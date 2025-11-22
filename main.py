import os
from flask import Flask, jsonify, request, session
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
from flask_login import LoginManager, current_user
import secrets
load_dotenv()

app = Flask(__name__)
# Secret key must be explicitly provided; falling back to a default is insecure.
secret_key = os.getenv('APP_SECRET_KEY') or os.getenv('SECRET_KEY')
if not secret_key:
    raise RuntimeError("APP_SECRET_KEY (or SECRET_KEY) is required")
app.config['SECRET_KEY'] = secret_key
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('SQLALCHEMY_DATABASE_URI')

# CORS and session cookie settings for browser SPA frontends.
# FRONTEND_ORIGIN should be the exact origin (scheme + host + port) of your frontend.
FRONTEND_ORIGIN = os.getenv('FRONTEND_ORIGIN')
if not FRONTEND_ORIGIN:
    raise RuntimeError("FRONTEND_ORIGIN is required for CORS")
CORS(app, supports_credentials=True, origins=[FRONTEND_ORIGIN])

# Cookie security settings — configurable via env vars.
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SECURE'] = os.getenv('SESSION_COOKIE_SECURE', 'true').lower() == 'true'
app.config['SESSION_COOKIE_SAMESITE'] = os.getenv('SESSION_COOKIE_SAMESITE', 'None')

# Init extensions
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    try:
        import uuid as _uuid
        # convert string id back to UUID if possible
        uid = _uuid.UUID(user_id)
        user = Usuario.query.get(uid)
    except Exception:
        # fallback: try direct get (some DBs accept string)
        user = Usuario.query.get(user_id)
    if user is not None and not getattr(user, "is_active", True):
        # Treat inactive users as not logged in
        return None
    return user


# For API clients, return JSON 401 instead of redirecting to a login page
@login_manager.unauthorized_handler
def unauthorized_callback():
    return jsonify({'error': 'unauthorized'}), 401


def _issue_csrf_token() -> str:
    """Create or reuse a per-session CSRF token stored server-side."""
    token = session.get("csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        session["csrf_token"] = token
    return token


@app.before_request
def csrf_protect():
    """Basic double-submit CSRF protection for session-authenticated users."""
    if request.method in ("POST", "PUT", "PATCH", "DELETE"):
        # Only enforce CSRF once a user is authenticated (login-required routes)
        if current_user.is_authenticated:
            session_token = session.get("csrf_token")
            header_token = request.headers.get("X-CSRF-Token")
            if not session_token or not header_token or header_token != session_token:
                return jsonify({"error": "csrf failed"}), 403


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
