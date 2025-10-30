from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, logout_user, current_user, login_required
from db.usuario import Usuario
from db.init import db
from db.password_reset import PasswordReset
import uuid
from datetime import datetime, timedelta
import secrets
import os
import smtplib
from email.message import EmailMessage


def send_reset_email(to_email: str, code: str) -> None:
    """Send reset code to email. If SMTP is not configured, print the code to stdout.

    Required env vars to actually send email:
      SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, EMAIL_FROM
    """
    host = os.getenv('SMTP_HOST')
    port = os.getenv('SMTP_PORT')
    user = os.getenv('SMTP_USER')
    password = os.getenv('SMTP_PASSWORD')
    sender = os.getenv('EMAIL_FROM', user)

    subject = 'Código de restablecimiento de contraseña'
    body = f'Su código de restablecimiento de contraseña es: {code}\nEste código es válido por 15 minutos.'

    # If host/port missing, just print the code for dev.
    if not host or not port:
        print(f"[DEV EMAIL] To: {to_email} Code: {code}")
        return

    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = to_email
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
                    # Ignore EHLO errors; some dev/test SMTP servers may not support it.
                    pass
                s.send_message(msg)
    except Exception as e:
        # Don't raise — log for dev and fallback to printing the code
        print('Failed to send reset email:', e)
        print(f"[DEV EMAIL] To: {to_email} Code: {code}")

bp = Blueprint('auth', __name__, url_prefix='/auth')


@bp.route('/register', methods=['POST'])
def register():
    data = request.get_json() or {}
    required = ('nombre', 'apellido', 'email', 'password')
    if not all(k in data for k in required):
        return jsonify({'error': 'missing fields'}), 400

    # check existing
    if Usuario.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'email already registered'}), 400

    hashed = generate_password_hash(data['password'])
    user = Usuario(
        id=uuid.uuid4(),
        nombre=data['nombre'],
        apellido=data['apellido'],
        email=data['email'],
        password=hashed,
    )
    db.session.add(user)
    db.session.commit()
    return jsonify({'id': str(user.id), 'email': user.email}), 201


@bp.route('/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    if 'email' not in data or 'password' not in data:
        return jsonify({'error': 'missing credentials'}), 400

    user = Usuario.query.filter_by(email=data['email']).first()
    if not user or not check_password_hash(user.password, data['password']):
        return jsonify({'error': 'invalid credentials'}), 401

    login_user(user)
    return jsonify({'id': str(user.id), 'email': user.email, 'role': user.role}), 200


@bp.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    return jsonify({'status': 'logged out'})


@bp.route('/forgot', methods=['POST'])
def forgot_password():
    data = request.get_json() or {}
    email = data.get('email')
    if not email:
        return jsonify({'error': 'email required'}), 400

    user = Usuario.query.filter_by(email=email).first()
    if not user:
        return jsonify({'error': 'email not found'}), 404

    code = ''.join(secrets.choice('0123456789') for _ in range(6))
    expires = datetime.utcnow() + timedelta(minutes=15)
    pr = PasswordReset(id=uuid.uuid4(), user_id=user.id, code=code, expires_at=expires, used=False)
    db.session.add(pr)
    db.session.commit()

    send_reset_email(user.email, code)
    return jsonify({'status': 'code_sent'}), 200


@bp.route('/verify-reset', methods=['POST'])
def verify_reset():
    data = request.get_json() or {}
    email = data.get('email')
    code = data.get('code')
    if not email or not code:
        return jsonify({'error': 'email and code required'}), 400

    user = Usuario.query.filter_by(email=email).first()
    if not user:
        return jsonify({'error': 'email not found'}), 404

    pr = PasswordReset.query.filter_by(user_id=user.id, code=code, used=False).order_by(PasswordReset.expires_at.desc()).first()
    if not pr or not pr.is_valid():
        return jsonify({'error': 'invalid or expired code'}), 400

    return jsonify({'status': 'code_valid'}), 200


@bp.route('/reset', methods=['POST'])
def reset_password():
    data = request.get_json() or {}
    email = data.get('email')
    code = data.get('code')
    new_password = data.get('new_password')
    if not email or not code or not new_password:
        return jsonify({'error': 'email, code and new_password required'}), 400

    user = Usuario.query.filter_by(email=email).first()
    if not user:
        return jsonify({'error': 'email not found'}), 404

    pr = PasswordReset.query.filter_by(user_id=user.id, code=code, used=False).order_by(PasswordReset.expires_at.desc()).first()
    if not pr or not pr.is_valid():
        return jsonify({'error': 'invalid or expired code'}), 400

    # set new password
    user.password = generate_password_hash(new_password)
    pr.used = True
    db.session.add(user)
    db.session.add(pr)
    db.session.commit()

    return jsonify({'status': 'password_changed'}), 200
