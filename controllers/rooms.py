from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from db.room import Room, Hint, UsuarioRoom, UsuarioHint
from db.usuario import Usuario
from db.init import db as _db

bp = Blueprint('rooms', __name__, url_prefix='/rooms')


@bp.route('', methods=['GET'])
@login_required
def list_rooms():
    """Return all rooms with per-user completed/is_unlocked flags."""
    rooms = Room.query.order_by(Room.id).all()

    # Build a quick lookup for the current user's UsuarioRoom entries if available
    ur_items = getattr(current_user, 'usuario_rooms', [])
    # relationship may be a single object or a collection depending on mapper state; normalize to list
    if isinstance(ur_items, UsuarioRoom):
        ur_items = [ur_items]
    usuario_rooms_lookup = {ur.room_id: ur for ur in (ur_items or [])}

    result = []
    for r in rooms:
        ur = usuario_rooms_lookup.get(r.id)
        result.append({
            'id': r.id,
            'name': r.name,
            'description': r.description,
            'imageUrl': r.image_url,
            'completed': bool(ur.completed) if ur is not None else False,
            'isUnlocked': bool(ur.is_unlocked) if ur is not None else False,
        })

    return jsonify(result), 200


@bp.route('/<int:room_id>', methods=['GET'])
@login_required
def get_room_hints(room_id: int):
    """Return hints for a room including per-user completed flag."""
    room = Room.query.get(room_id)
    if room is None:
        return jsonify({'error': 'room not found'}), 404

    hints = Hint.query.filter_by(room_id=room_id).order_by(Hint.id).all()

    # Build lookup for user's hint completion
    uh_items = getattr(current_user, 'usuario_hints', [])
    if isinstance(uh_items, UsuarioHint):
        uh_items = [uh_items]
    usuario_hints_lookup = {uh.hint_id: uh for uh in (uh_items or [])}

    hints_out = []
    for h in hints:
        uh = usuario_hints_lookup.get(h.id)
        hints_out.append({
            'id': h.id,
            'title': h.title,
            'description': h.description,
            'imageUrl': h.image_url,
            'completed': bool(uh.completed) if uh is not None else False,
        })

    return jsonify({'id': room.id, 'name': room.name, 'hints': hints_out}), 200


@bp.route('/complete', methods=['POST'])
@login_required
def complete_hint_for_user():
    """Mark a hint as completed for a user.

    Expects JSON body: { "room_id": int, "hint_id": int, "email": "user@example.com" }
    Only the user themselves or an ADMIN may mark hints for a user.
    """
    data = request.get_json() or {}
    try:
        room_id = int(data.get('room_id'))
        hint_id = int(data.get('hint_id'))
    except Exception:
        return jsonify({'error': 'room_id and hint_id must be integers'}), 400
    email = data.get('email')
    if not email:
        return jsonify({'error': 'email required in request body'}), 400

    # permission check: allow if current_user is admin or owner
    is_admin = getattr(current_user, 'role', None) == 'ADMIN'
    if not is_admin and getattr(current_user, 'email', None) != email:
        return jsonify({'error': 'forbidden'}), 403

    user = Usuario.query.filter_by(email=email).first()
    if not user:
        return jsonify({'error': 'user not found'}), 404

    # verify hint exists and belongs to room
    hint = Hint.query.get(hint_id)
    if not hint or hint.room_id != room_id:
        return jsonify({'error': 'hint not found for room'}), 404

    # ensure user has UsuarioRoom record
    ur = UsuarioRoom.query.filter_by(usuario_id=user.id, room_id=room_id).first()
    if not ur:
        ur = UsuarioRoom(usuario_id=user.id, room_id=room_id, completed=False, is_unlocked=True)
        _db.session.add(ur)

    # set or create UsuarioHint
    uh = UsuarioHint.query.filter_by(usuario_id=user.id, hint_id=hint_id).first()
    if not uh:
        uh = UsuarioHint(usuario_id=user.id, hint_id=hint_id, completed=True)
        _db.session.add(uh)
    else:
        uh.completed = True

    # commit
    try:
        _db.session.commit()
    except Exception as e:
        try:
            _db.session.rollback()
        except Exception:
            pass
        return jsonify({'error': 'db error', 'detail': str(e)}), 500

    return jsonify({'status': 'ok', 'hint': {'id': hint_id, 'completed': True}}), 200
