from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from db.usuario import Usuario
from db.init import db
from werkzeug.security import generate_password_hash
import uuid
import re
import secrets

bp = Blueprint('users', __name__, url_prefix='/users')

ADMIN_ROLE = 'ADMIN'
USER_ROLE = 'USER'


def user_to_dict(u: Usuario) -> dict:
    return {
        'id': str(u.id),
        'nombre': u.nombre,
        'apellido': u.apellido,
        'email': u.email,
        'global_position': u.global_position,
        'total_points': u.total_points,
        'role': u.role,
        'is_active': bool(u.is_active),
    }


def is_admin():
    return current_user.is_authenticated and getattr(current_user, 'role', None) == ADMIN_ROLE


def validate_email(email: str) -> bool:
    # simple RFC-5322-ish-ish regex for basic validation
    return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email or ""))


@bp.route('', methods=['GET'])
@login_required
def list_users():
    if not is_admin():
        return jsonify({'error': 'forbidden'}), 403

    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 10))
    except ValueError:
        return jsonify({'error': 'invalid pagination parameters'}), 400

    q = request.args.get('q')
    role = request.args.get('role')
    is_active = request.args.get('is_active')

    query = Usuario.query

    if q:
        like = f"%{q}%"
        query = query.filter(
            db.or_(
                Usuario.nombre.ilike(like),
                Usuario.apellido.ilike(like),
                Usuario.email.ilike(like),
            )
        )

    if role:
        query = query.filter_by(role=role)

    if is_active is not None:
        if is_active.lower() in ('true', '1', 'yes'):
            query = query.filter_by(is_active=True)
        elif is_active.lower() in ('false', '0', 'no'):
            query = query.filter_by(is_active=False)

    pag = query.order_by(Usuario.nombre.asc()).paginate(page=page, per_page=per_page, error_out=False)

    items = [user_to_dict(u) for u in pag.items]
    return jsonify({
        'items': items,
        'page': pag.page,
        'per_page': pag.per_page,
        'total': pag.total,
        'total_pages': pag.pages,
    }), 200


@bp.route('/<user_id>', methods=['GET'])
@login_required
def get_user(user_id):
    try:
        uid = uuid.UUID(user_id)
    except Exception:
        return jsonify({'error': 'invalid id'}), 400

    user = Usuario.query.get(uid)
    if not user:
        return jsonify({'error': 'not found'}), 404

    if not is_admin() and str(current_user.get_id()) != str(user.id):
        return jsonify({'error': 'forbidden'}), 403

    return jsonify(user_to_dict(user)), 200


@bp.route('', methods=['POST'])
@login_required
def create_user():
    if not is_admin():
        return jsonify({'error': 'forbidden'}), 403

    data = request.get_json() or {}
    nombre = data.get('nombre')
    apellido = data.get('apellido')
    email = data.get('email')
    password = data.get('password')
    role = data.get('role', USER_ROLE)

    if not nombre or not apellido or not email:
        return jsonify({'error': 'missing fields'}), 400

    if not validate_email(email):
        return jsonify({'error': 'invalid email'}), 400

    if Usuario.query.filter_by(email=email).first():
        return jsonify({'error': 'email duplicate'}), 409

    if password:
        if len(password) < 8:
            return jsonify({'error': 'password too short'}), 400
        hashed = generate_password_hash(password)
    else:
        # generate random password (admin could send activation email in future)
        random_pw = secrets.token_urlsafe(12)
        hashed = generate_password_hash(random_pw)

    u = Usuario(id=uuid.uuid4(), nombre=nombre, apellido=apellido, email=email, password=hashed, role=role)
    db.session.add(u)
    db.session.commit()

    return jsonify(user_to_dict(u)), 201


def apply_user_updates(user: Usuario, data: dict, allow_role_change: bool = False) -> (bool, str): # type: ignore
    # returns (changed, error_message)
    # Allowed updates: nombre, apellido, email (admin), password (admin), role (admin), is_active (admin)
    changed = False

    if 'nombre' in data:
        user.nombre = data['nombre']
        changed = True

    if 'apellido' in data:
        user.apellido = data['apellido']
        changed = True

    if 'email' in data:
        if not validate_email(data['email']):
            return False, 'invalid email'
        existing = Usuario.query.filter(Usuario.email == data['email'], Usuario.id != user.id).first()
        if existing:
            return False, 'email duplicate'
        user.email = data['email']
        changed = True

    if 'password' in data:
        pw = data['password']
        if pw and len(pw) < 8:
            return False, 'password too short'
        user.password = generate_password_hash(pw)
        changed = True

    if allow_role_change and 'role' in data:
        user.role = data['role']
        changed = True

    if allow_role_change and 'is_active' in data:
        user.is_active = bool(data['is_active'])
        changed = True

    return changed, ''


@bp.route('/<user_id>', methods=['PUT', 'PATCH'])
@login_required
def update_user(user_id):
    try:
        uid = uuid.UUID(user_id)
    except Exception:
        return jsonify({'error': 'invalid id'}), 400

    user = Usuario.query.get(uid)
    if not user:
        return jsonify({'error': 'not found'}), 404

    data = request.get_json() or {}

    if is_admin():
        allow_role_change = True
    elif str(current_user.get_id()) == str(user.id):
        allow_role_change = False
        # ensure user only updates allowed fields
        allowed = {'nombre', 'apellido'}
        # if request tries to change other fields, reject
        forbidden = set(data.keys()) - allowed
        if forbidden:
            return jsonify({'error': 'forbidden fields for user update', 'fields': list(forbidden)}), 403
    else:
        return jsonify({'error': 'forbidden'}), 403

    changed, err = apply_user_updates(user, data, allow_role_change=allow_role_change)
    if err:
        if err == 'email duplicate':
            return jsonify({'error': err}), 409
        return jsonify({'error': err}), 400

    if changed:
        db.session.add(user)
        db.session.commit()

    return jsonify(user_to_dict(user)), 200


@bp.route('/<user_id>', methods=['DELETE'])
@login_required
def delete_user(user_id):
    if not is_admin():
        return jsonify({'error': 'forbidden'}), 403

    try:
        uid = uuid.UUID(user_id)
    except Exception:
        return jsonify({'error': 'invalid id'}), 400

    user = Usuario.query.get(uid)
    if not user:
        return jsonify({'error': 'not found'}), 404

    # soft delete
    user.is_active = False
    db.session.add(user)
    db.session.commit()
    return '', 204
