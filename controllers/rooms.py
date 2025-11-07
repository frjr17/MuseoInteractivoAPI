from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from db.room import Room, Hint, UsuarioRoom, UsuarioHint
from db.usuario import Usuario
from db.init import db as _db

bp = Blueprint("rooms", __name__, url_prefix="/rooms")


@bp.route("", methods=["GET"])
@login_required
def list_rooms():
    """Return all rooms with per-user completed/is_unlocked flags."""
    rooms = Room.query.order_by(Room.id).all()

    # Build a quick lookup for the current user's UsuarioRoom entries by querying the DB
    # This avoids issues with relationship loading states returning scalars or proxies.
    usuario_rooms = (
        UsuarioRoom.query.filter_by(usuario_id=getattr(current_user, "id", None)).all()
        if getattr(current_user, "id", None) is not None
        else []
    )
    usuario_rooms_lookup = {ur.room_id: ur for ur in usuario_rooms}

    result = []
    for r in rooms:
        ur = usuario_rooms_lookup.get(r.id)
        result.append(
            {
                "id": r.id,
                "name": r.name,
                "finalCode": r.final_code,
                "imageUrl": getattr(r, "image_url", None),
                "completed": bool(ur.completed) if ur is not None else False,
                "isUnlocked": bool(ur.is_unlocked) if ur is not None else False,
            }
        )

    return jsonify(result), 200


@bp.route("/<int:room_id>", methods=["GET"])
@login_required
def get_room_hints(room_id: int):
    """Return hints for a room including per-user completed flag."""
    room = Room.query.get(room_id)
    if room is None:
        return jsonify({"error": "room not found"}), 404

    # get UsuarioRoom for current user and this room
    ur = UsuarioRoom.query.filter_by(room_id=room.id, usuario_id=getattr(current_user, "id", None)).first()
    hints = Hint.query.filter_by(room_id=room_id).order_by(Hint.id).all()

    # Build lookup for user's hint completion
    uh_items = getattr(current_user, "usuario_hints", [])
    if isinstance(uh_items, UsuarioHint):
        uh_items = [uh_items]
    usuario_hints_lookup = {uh.hint_id: uh for uh in (uh_items or [])}

    hints_out = []
    for h in hints:
        uh = usuario_hints_lookup.get(h.id)
        hints_out.append(
            {
                "id": h.id,
                "title": h.title,
                "limeSurveyUrl": getattr(h, "lime_survey_url", None),
                "imageUrl": h.image_url,
                "accessCode": getattr(h, "access_code", None),
                "completed": bool(uh.completed) if uh is not None else False,
            }
        )

    return jsonify({"id": room.id, "completed": bool(ur.completed) if ur is not None else False, "name": room.name,"final_code":room.final_code, "hints": hints_out}), 200


@bp.route("/<int:room_id>/verify_final_code", methods=["POST"])
@login_required
def verify_final_code(room_id: int):
    """Verify a submitted final code for a room.

    Request JSON: { "final_code": "..." }
    Response: { "room_id": <int>, "correct": true|false }
    """
    # Only allow verifying the final code for the first room (id == 1)
    if int(room_id) != 1:
        return jsonify({"error": "final code verification only allowed for room 1"}), 403

    room = Room.query.get(room_id)
    if room is None:
        return jsonify({"error": "room not found"}), 404

    data = request.get_json() or {}
    submitted = data.get("final_code") or data.get("code")
    if submitted is None:
        return jsonify({"error": "final_code required in request body"}), 400
    # Check if user already completed this room; if so, don't allow re-verification
    uid = getattr(current_user, "id", None)
    if uid is not None:
        existing_ur = UsuarioRoom.query.filter_by(usuario_id=uid, room_id=room.id).first()
        if existing_ur and existing_ur.completed:
            return jsonify({"error": "room already completed"}), 400

    # simple equality check (case-sensitive). If you want case-insensitive, change accordingly.
    correct = (room.final_code == submitted)

    if correct:
        # mark this room completed for the current user and unlock the next room
        try:
            if uid is not None:
                ur = UsuarioRoom.query.filter_by(usuario_id=uid, room_id=room.id).first()
                room_was_completed_before = bool(ur and ur.completed)

                if not ur:
                    ur = UsuarioRoom(usuario_id=uid, room_id=room.id, completed=True, is_unlocked=True)
                    _db.session.add(ur)
                else:
                    if not ur.completed:
                        ur.completed = True
                        _db.session.add(ur)

                # Award 100 points to the user only if the room wasn't previously completed
                if not room_was_completed_before:
                    try:
                        user = Usuario.query.filter_by(id=uid).first()
                        if user:
                            user.total_points = (user.total_points or 0) + 100
                            _db.session.add(user)
                    except Exception:
                        # don't block the flow if scoring fails
                        pass

                # unlock next room (first room with id > current)
                next_room = Room.query.filter(Room.id > room.id).order_by(Room.id).first()
                if next_room:
                    next_ur = UsuarioRoom.query.filter_by(usuario_id=uid, room_id=next_room.id).first()
                    if not next_ur:
                        next_ur = UsuarioRoom(usuario_id=uid, room_id=next_room.id, completed=False, is_unlocked=True)
                        _db.session.add(next_ur)
                    elif not next_ur.is_unlocked:
                        next_ur.is_unlocked = True
                        _db.session.add(next_ur)

                try:
                    _db.session.commit()
                except Exception:
                    try:
                        _db.session.rollback()
                    except Exception:
                        pass
        except Exception:
            # don't raise to the client; just log in server logs if needed
            pass

    return jsonify({"room_id": room.id, "correct": bool(correct)}), 200


@bp.route("/complete", methods=["POST"])
@login_required
def complete_hint_for_user():
    """Mark a hint as completed for a user.

    Expects JSON body: { "room_id": int, "hint_id": int, "email": "user@example.com" }
    Only the user themselves or an ADMIN may mark hints for a user.
    """
    data = request.get_json() or {}
    try:
        room_id = int(data.get("room_id"))
        hint_id = int(data.get("hint_id"))
    except Exception:
        return jsonify({"error": "room_id and hint_id must be integers"}), 400
    email = data.get("email")
    if not email:
        return jsonify({"error": "email required in request body"}), 400

    # permission check: allow if current_user is admin or owner
    is_admin = getattr(current_user, "role", None) == "ADMIN"
    if not is_admin and getattr(current_user, "email", None) != email:
        return jsonify({"error": "forbidden"}), 403

    user = Usuario.query.filter_by(email=email).first()
    if not user:
        return jsonify({"error": "user not found"}), 404

    # verify hint exists and belongs to room
    hint = Hint.query.get(hint_id)
    if not hint or hint.room_id != room_id:
        return jsonify({"error": "hint not found for room"}), 404

    # ensure user has UsuarioRoom record
    ur = UsuarioRoom.query.filter_by(usuario_id=user.id, room_id=room_id).first()
    if not ur:
        ur = UsuarioRoom(
            usuario_id=user.id, room_id=room_id, completed=False, is_unlocked=True
        )
        _db.session.add(ur)

    # set or create UsuarioHint
    uh = UsuarioHint.query.filter_by(usuario_id=user.id, hint_id=hint_id).first()
    newly_completed = False
    if not uh:
        uh = UsuarioHint(usuario_id=user.id, hint_id=hint_id, completed=True)
        _db.session.add(uh)
        newly_completed = True
    else:
        # only add points / mark as newly completed if it wasn't already completed
        if not uh.completed:
            uh.completed = True
            newly_completed = True

    # If the hint was newly completed, add points to the user
    if newly_completed:
        try:
            # add 30 points for completing a hint
            user.total_points = (user.total_points or 0) + 30
            _db.session.add(user)
        except Exception:
            # ignore scoring errors and continue to commit rest
            pass

    # After marking the hint, check if all hints in the room are completed for this user
    try:
        total_hints = Hint.query.filter_by(room_id=room_id).count()
        completed_hints = (
            _db.session.query(UsuarioHint)
            .join(Hint, UsuarioHint.hint_id == Hint.id)
            .filter(UsuarioHint.usuario_id == user.id, Hint.room_id == room_id, UsuarioHint.completed == True)
            .count()
        )
        if total_hints > 0 and completed_hints >= total_hints:
            # mark the UsuarioRoom as completed
            ur = UsuarioRoom.query.filter_by(usuario_id=user.id, room_id=room_id).first()
            room_completed_now = False
            if ur and not ur.completed:
                ur.completed = True
                room_completed_now = True
                _db.session.add(ur)
            # If this room was just completed, unlock the next room (if any)
            if room_completed_now:
                try:
                    next_room = (
                        Room.query.filter(Room.id > room_id).order_by(Room.id).first()
                    )
                    if next_room:
                        next_ur = UsuarioRoom.query.filter_by(usuario_id=user.id, room_id=next_room.id).first()
                        if not next_ur:
                            next_ur = UsuarioRoom(usuario_id=user.id, room_id=next_room.id, completed=False, is_unlocked=True)
                            _db.session.add(next_ur)
                        elif not next_ur.is_unlocked:
                            next_ur.is_unlocked = True
                            _db.session.add(next_ur)
                except Exception:
                    # don't block on unlocking
                    pass
    except Exception:
        # don't block on this check; proceed to commit
        pass

    # commit
    try:
        _db.session.commit()
    except Exception as e:
        try:
            _db.session.rollback()
        except Exception:
            pass
        return jsonify({"error": "db error", "detail": str(e)}), 500

    return jsonify({
        "status": "ok",
        "hint": {"id": hint_id, "completed": True, "accessCode": getattr(hint, "access_code", None)},
    }), 200
