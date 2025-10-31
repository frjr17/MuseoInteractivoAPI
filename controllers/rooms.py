from flask import Blueprint, jsonify
from flask_login import login_required, current_user
from db.room import Room, Hint, UsuarioRoom, UsuarioHint

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
