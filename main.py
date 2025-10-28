import os
from flask import Flask
from db.init import db
from dotenv import load_dotenv
from db.rol import Rol
from db.usuario import Usuario
load_dotenv()

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('SQLALCHEMY_DATABASE_URI')
#No se que estoy haciendo
db.init_app(app)

with app.app_context():
    # ensure models are imported so SQLAlchemy registers them before creating tables
    db.create_all()
    print("Database tables created.")

@app.route('/healthz', methods=['GET'])
def health_check():
    return {"status": "healthy"}, 200