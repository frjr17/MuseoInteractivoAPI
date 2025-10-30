import os
from flask import Flask
from db.init import db
from dotenv import load_dotenv
from db.usuario import Usuario
from db.password_reset import PasswordReset
from flask_login import LoginManager
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('SQLALCHEMY_DATABASE_URI')

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


from controllers.auth import bp as auth_bp
app.register_blueprint(auth_bp)

with app.app_context():
    # ensure models are imported so SQLAlchemy registers them before creating tables
    db.create_all()
    print("Database tables created.")


@app.route('/healthz', methods=['GET'])
def health_check():
    return {"status": "healthy"}, 200