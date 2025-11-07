import os
from flask import Flask
try:
    from flask_cors import CORS
except Exception:
    # In environments where flask-cors is not installed (CI/dev), fall back to a no-op
    # so imports don't fail. Install Flask-Cors in production/dev environments.
    CORS = lambda *a, **k: None
from dotenv import load_dotenv
from db.init import db
from db.usuario import Usuario
from db.password_reset import PasswordReset
from db.room import Room, Hint, UsuarioRoom, UsuarioHint
from flask_login import LoginManager
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('SQLALCHEMY_DATABASE_URI')


CORS(app) 

# Init extensions
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)


@login_manager.request_loader
def load_user_from_request(request):
    """Allow API clients to authenticate using Authorization: Bearer <sessionToken>.

    The session token is an opaque random string issued at login. We store only
    the sha256 hash in `session_tokens` and validate by hashing the presented
    token and looking it up (also checking expiry and revoked flag).
    """
    auth = request.headers.get("Authorization")
    if not auth or not auth.startswith("Bearer "):
        return None
    raw = auth.split(" ", 1)[1].strip()
    try:
        import hashlib
        from db.session_token import SessionToken
        from datetime import datetime

        h = hashlib.sha256(raw.encode()).hexdigest()
        st = SessionToken.query.filter_by(token_hash=h, revoked=False).first()
        if not st:
            return None
        if st.expires_at < datetime.utcnow():
            return None
        # update last_used (best-effort)
        try:
            st.last_used = datetime.utcnow()
            db.session.add(st)
            db.session.commit()
        except Exception:
            try:
                db.session.rollback()
            except Exception:
                pass
        return Usuario.query.get(st.usuario_id)
    except Exception:
        return None

@login_manager.user_loader
def load_user(user_id):
    try:
        import uuid as _uuid
        # convert string id back to UUID if possible
        uid = _uuid.UUID(user_id)
        return Usuario.query.get(uid)
    except Exception:
        # fallback: try direct get (some DBs accept string)
        return Usuario.query.get(user_id)


# For API clients, return JSON 401 instead of redirecting to a login page
@login_manager.unauthorized_handler
def unauthorized_callback():
    from flask import jsonify
    return jsonify({'error': 'unauthorized'}), 401


from controllers.auth import bp as auth_bp
app.register_blueprint(auth_bp)
from controllers.rooms import bp as rooms_bp
app.register_blueprint(rooms_bp)
from controllers.users import bp as users_bp
app.register_blueprint(users_bp)

with app.app_context():
    # ensure models are imported so SQLAlchemy registers them before creating tables
    db.create_all()
    print("Database tables created.")


@app.route('/healthz', methods=['GET'])
def health_check():
    return {"status": "healthy"}, 200