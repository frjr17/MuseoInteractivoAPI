# scripts/create_admin.py
import os
import sys

# Ensure project root is on sys.path so `from main import app` works even when
# this script is executed as `python scripts/create_admin.py` (sys.path[0]
# would otherwise be the scripts directory).
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from main import app
from db.init import db
from db.usuario import Usuario
from werkzeug.security import generate_password_hash
import uuid

with app.app_context():
    if not Usuario.query.filter_by(email='admin@example.com').first():
        u = Usuario(
            id=uuid.uuid4(),
            nombre='Admin',
            apellido='User',
            email='admin@example.com',
            password=generate_password_hash('AdminPass123'),
            role='ADMIN',
            is_active=True
        )
        db.session.add(u)
        db.session.commit()
        print('Admin created:', u.id)
    else:
        print('Admin already exists')
