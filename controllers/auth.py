from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, logout_user, current_user, login_required
from db.usuario import Usuario
from db.room import Room, Hint, UsuarioRoom, UsuarioHint
from db.init import db
from db.password_reset import PasswordReset
import uuid
from datetime import datetime, timedelta, timezone
import secrets
import os
import smtplib
from email.message import EmailMessage


def send_reset_email(to_email: str, code: str) -> None:
    """Send reset code to email. If SMTP is not configured, print the code to stdout.

    Required env vars to actually send email:
      SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, EMAIL_FROM
    """
    host = os.getenv("SMTP_HOST")
    port = os.getenv("SMTP_PORT")
    user = os.getenv("SMTP_USER")
    password = os.getenv("SMTP_PASSWORD")
    sender = os.getenv("EMAIL_FROM")

    subject = "Código de restablecimiento de contraseña"
    body = f"Su código de restablecimiento de contraseña es: {code}\nEste código es válido por 15 minutos."

    # If host/port missing, just print the code for dev.
    if not host or not port:
        print(f"[DEV EMAIL] To: {to_email} Code: {code}")
        return

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = to_email
    msg.set_content(body)

    try:
        port_i = int(port)
        # MailHog and many dev SMTP servers accept plain SMTP without TLS/auth on port 1025
        if user and password:
            # Authenticated SMTP
            if port_i == 465:
                with smtplib.SMTP_SSL(host, port_i) as s:
                    s.login(user, password)
                    s.send_message(msg)
            else:
                with smtplib.SMTP(host, port_i) as s:
                    s.starttls()
                    s.login(user, password)
                    s.send_message(msg)
        else:
            # No auth: connect and send (suitable for MailHog)
            with smtplib.SMTP(host, port_i) as s:
                try:
                    # try EHLO/NOOP to ensure connection
                    s.ehlo()
                except Exception:
                    pass
                s.send_message(msg)
    except Exception as e:
        # Don't raise — log for dev and fallback to printing the code
        print("Failed to send reset email:", e)
        print(f"[DEV EMAIL] To: {to_email} Code: {code}")


bp = Blueprint("auth", __name__, url_prefix="/auth")


def _to_bool(value):
    """Normalize various truthy/falsy values to boolean."""
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    if isinstance(value, (int, float)):
        return bool(value)
    s = str(value).strip().lower()
    return s in ("1", "true", "t", "yes", "y", "on")


@bp.route("/register", methods=["POST"])
def register():
    data = request.get_json() or {}
    required = ("nombre", "apellido", "email", "password")
    if not all(k in data for k in required):
        return jsonify({"error": "missing fields"}), 400

    if Usuario.query.filter_by(email=data["email"]).first():
        return jsonify({"error": "email already registered"}), 400

    hashed = generate_password_hash(data["password"])
    user = Usuario(
        id=uuid.uuid4(),
        nombre=data["nombre"],
        apellido=data["apellido"],
        email=data["email"],
        password=hashed,
    )
    db.session.add(user)
    db.session.commit()
    login_user(user, remember=True)

    # Create per-user room and hint records so the frontend can show progress
    try:
        rooms = Room.query.all()
        for room in rooms:
            is_first_room = room.id == 1
            # create UsuarioRoom if not exists
            ur = UsuarioRoom.query.filter_by(
                usuario_id=user.id, room_id=room.id
            ).first()
            if not ur:
                ur = UsuarioRoom(
                    usuario_id=user.id,
                    room_id=room.id,
                    completed=is_first_room,
                    is_unlocked=(is_first_room or room.id == 2),
                )
                db.session.add(ur)

            # ensure UsuarioHint entries exist for each hint in the room
            hints = Hint.query.filter_by(room_id=room.id).all()
            for h in hints:
                uh = UsuarioHint.query.filter_by(
                    usuario_id=user.id, hint_id=h.id
                ).first()
                if not uh:
                    uh = UsuarioHint(
                        usuario_id=user.id, hint_id=h.id, completed=is_first_room
                    )
                    db.session.add(uh)
        db.session.commit()
    except Exception:
        db.session.rollback()

    return jsonify({"id": str(user.id), "email": user.email}), 201


@bp.route("/login", methods=["POST"])
def login():
    data = request.get_json() or {}
    if "email" not in data or "password" not in data:
        return jsonify({"error": "missing credentials"}), 400

    user = Usuario.query.filter_by(email=data["email"]).first()
    if not user or not check_password_hash(user.password, data["password"]):
        return jsonify({"error": "invalid credentials"}), 401

    # Consider rememberMe field from frontend; default to False if not provided
    remember = _to_bool(data.get("rememberMe", False))
    login_user(user, remember=remember)
    return jsonify({"id": str(user.id), "email": user.email, "role": user.role}), 200


@bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    return jsonify({"status": "logged out"})


@bp.route("/forgot", methods=["POST"])
def forgot_password():
    data = request.get_json() or {}
    email = data.get("email")
    if not email:
        return jsonify({"error": "email required"}), 400

    user = Usuario.query.filter_by(email=email).first()
    if not user:
        return jsonify({"error": "email not found"}), 404

    code = str(secrets.randbelow(900000) + 100000)
    expires = datetime.now(timezone.utc) + timedelta(minutes=15)
    pr = PasswordReset(
        id=uuid.uuid4(), user_id=user.id, code=code, expires_at=expires, used=False
    )
    db.session.add(pr)
    db.session.commit()

    send_reset_email(user.email, code)
    return jsonify({"status": "code_sent"}), 200


@bp.route("/verify-reset", methods=["POST"])
def verify_reset():
    data = request.get_json() or {}
    email = data.get("email")
    code = data.get("code")
    if not email or not code:
        return jsonify({"error": "email and code required"}), 400

    user = Usuario.query.filter_by(email=email).first()
    if not user:
        return jsonify({"error": "email not found"}), 404

    pr = (
        PasswordReset.query.filter_by(user_id=user.id, code=code, used=False)
        .order_by(PasswordReset.expires_at.desc())
        .first()
    )
    if not pr or not pr.is_valid():
        return jsonify({"error": "invalid or expired code"}), 400

    return jsonify({"status": "code_valid"}), 200


@bp.route("/reset", methods=["POST"])
def reset_password():
    data = request.get_json() or {}
    email = data.get("email")
    code = data.get("code")
    new_password = data.get("new_password")
    if not email or not code or not new_password:
        return jsonify({"error": "email, code and new_password required"}), 400

    user = Usuario.query.filter_by(email=email).first()
    if not user:
        return jsonify({"error": "email not found"}), 404

    pr = (
        PasswordReset.query.filter_by(user_id=user.id, code=code, used=False)
        .order_by(PasswordReset.expires_at.desc())
        .first()
    )
    if not pr or not pr.is_valid():
        return jsonify({"error": "invalid or expired code"}), 400

    user.password = generate_password_hash(new_password)
    pr.used = True
    db.session.add(user)
    db.session.add(pr)
    db.session.commit()

    return jsonify({"status": "password_changed"}), 200


@bp.route("/me", methods=["GET"])
@login_required
def me():
    """Return the current logged-in user's basic info. Use this to verify the session cookie."""
    user = current_user
    try:
        uid = str(user.id)
    except Exception:
        uid = None

    return (
        jsonify(
            {
                "id": uid,
                "email": getattr(user, "email", None),
                "nombre": getattr(user, "nombre", None),
                "apellido": getattr(user, "apellido", None),
                "role": getattr(user, "role", None),
                "totalPoints": getattr(user, "total_points", None),
                "isAuthenticated": bool(user.is_authenticated),
            }
        ),
        200,
    )
