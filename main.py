import os
from flask import Flask
try:
    from flask_cors import CORS
except Exception:
    # In environments where flask-cors is not installed (CI/dev), fall back to a no-op
    # so imports don't fail. Install Flask-Cors in production/dev environments.
    CORS = lambda *a, **k: None
from db.init import db
from dotenv import load_dotenv
from db.usuario import Usuario
from db.password_reset import PasswordReset
from flask_login import LoginManager
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('SQLALCHEMY_DATABASE_URI')

# CORS and session cookie settings for browser SPA frontends.
# FRONTEND_ORIGIN should be the exact origin (scheme + host + port) of your frontend.
FRONTEND_ORIGIN = os.getenv('FRONTEND_ORIGIN')
CORS(app, supports_credentials=True, resources={r"/*": {"origins": FRONTEND_ORIGIN}})

# Cookie security settings — configurable via env vars.
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SECURE'] = os.getenv('SESSION_COOKIE_SECURE', 'false').lower() == 'true'
app.config['SESSION_COOKIE_SAMESITE'] = os.getenv('SESSION_COOKIE_SAMESITE', 'Lax')

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
from controllers.users import bp as users_bp
app.register_blueprint(users_bp)

with app.app_context():
    # ensure models are imported so SQLAlchemy registers them before creating tables
    db.create_all()
    print("Database tables created.")


@app.route('/healthz', methods=['GET'])
def health_check():
    return {"status": "healthy"}, 200