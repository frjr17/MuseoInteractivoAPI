"""Seed script for MuseoInteractivoAPI.

Creates sample rooms, hints, a test user, and per-user access records.

Run with:
    python seeder.py

This script is idempotent for basic runs (it will not duplicate rooms/hints by name).
"""
from datetime import datetime
import uuid

from werkzeug.security import generate_password_hash

from main import app
from db.init import db
from db.usuario import Usuario
from db.room import Room, Hint, UsuarioRoom, UsuarioHint


SAMPLE_ROOMS = [
        {
                "name": "Sala de Historia",
                "description": "Explora objetos antiguos y descubre sus secretos.",
                "image_url": None,
                "hints": [
                        {"title": "Pista 1 - Busca la placa", "description": "Revisa la placa dentro del estuche.", "image_url": None},
                        {"title": "Pista 2 - Cuenta los símbolos", "description": "Anota los símbolos alrededor del borde.", "image_url": None},
                        {"title": "Pista 3 - Fecha oculta", "description": "Inspecciona el reverso para una fecha grabada.", "image_url": None},
                        {"title": "Pista 4 - Material", "description": "Toca la superficie para identificar el material.", "image_url": None},
                        {"title": "Pista 5 - Relación", "description": "Relaciona el objeto con el mapa histórico en la pared.", "image_url": None},
                ],
        },
        {
                "name": "Sala de Ciencia",
                "description": "Experimentos interactivos que explican principios científicos.",
                "image_url": None,
                "hints": [
                        {"title": "Pista 1 - Observa la reacción", "description": "Fíjate en la reacción en el primer cilindro.", "image_url": None},
                        {"title": "Pista 2 - Medición", "description": "Mide la proporción entre los dos líquidos.", "image_url": None},
                        {"title": "Pista 3 - Temperatura", "description": "Siente la variación de temperatura cerca del experimento.", "image_url": None},
                        {"title": "Pista 4 - Voltaje", "description": "Revisa las conexiones eléctricas de la maqueta.", "image_url": None},
                        {"title": "Pista 5 - Resultado esperado", "description": "Compara tu observación con la tabla de resultados.", "image_url": None},
                ],
        },
        {
                "name": "Sala de Arte",
                "description": "Obras que desafían la percepción.",
                "image_url": None,
                "hints": [
                        {"title": "Pista 1 - Colores ocultos", "description": "Ilumina la obra para ver los colores escondidos.", "image_url": None},
                        {"title": "Pista 2 - Firma del autor", "description": "Busca una firma en la esquina inferior derecha.", "image_url": None},
                        {"title": "Pista 3 - Técnica", "description": "Observa la textura para identificar la técnica usada.", "image_url": None},
                        {"title": "Pista 4 - Perspectiva", "description": "Cambia de ángulo para descubrir un detalle oculto.", "image_url": None},
                        {"title": "Pista 5 - Inspiración", "description": "Lee la placa para conocer la inspiración detrás de la obra.", "image_url": None},
                ],
        },
        {
                "name": "Sala de Tecnología",
                "description": "Innovaciones tecnológicas y su evolución.",
                "image_url": None,
                "hints": [
                        {"title": "Pista 1 - Componentes", "description": "Identifica los componentes principales del prototipo.", "image_url": None},
                        {"title": "Pista 2 - Línea de tiempo", "description": "Consulta la línea temporal para ubicar el invento.", "image_url": None},
                        {"title": "Pista 3 - Software", "description": "Observa la interfaz en la pantalla interactiva.", "image_url": None},
                        {"title": "Pista 4 - Fuente de energía", "description": "Localiza la fuente de alimentación del dispositivo.", "image_url": None},
                        {"title": "Pista 5 - Aplicación", "description": "Piensa en un uso práctico para esta tecnología.", "image_url": None},
                ],
        },
        {
                "name": "Sala de Naturaleza",
                "description": "Ecosistemas, flora y fauna en exhibición.",
                "image_url": None,
                "hints": [
                        {"title": "Pista 1 - Hábitat", "description": "Identifica el hábitat natural del ejemplar.", "image_url": None},
                        {"title": "Pista 2 - Alimentación", "description": "Observa las adaptaciones relacionadas con la alimentación.", "image_url": None},
                        {"title": "Pista 3 - Ciclo de vida", "description": "Revisa el diagrama del ciclo de vida en el panel.", "image_url": None},
                        {"title": "Pista 4 - Adaptación", "description": "Busca rasgos que ayuden a la supervivencia.", "image_url": None},
                        {"title": "Pista 5 - Conservación", "description": "Lee sobre las medidas de conservación para esta especie.", "image_url": None},
                ],
        },
]


TEST_USER = {
        "email": "test@example.com",
        "nombre": "Test",
        "apellido": "User",
        "password": "password123",
}


def seed():
        with app.app_context():
                # Create tables (if not present)
                db.create_all()

                # Use built-in SAMPLE_ROOMS
                rooms_data = SAMPLE_ROOMS

                # Create or get test user
                user = Usuario.query.filter_by(email=TEST_USER['email']).first()
                if not user:
                        print("Creating test user", TEST_USER['email'])
                        user = Usuario(
                                id=uuid.uuid4(),
                                nombre=TEST_USER['nombre'],
                                apellido=TEST_USER['apellido'],
                                email=TEST_USER['email'],
                                password=generate_password_hash(TEST_USER['password']),
                        )
                        db.session.add(user)
                        db.session.commit()
                else:
                        print("Found existing test user", user.email)

                # Determine if UsuarioHint has an is_unlocked column
                try:
                        uh_columns = set(UsuarioHint.__table__.columns.keys())
                except Exception:
                        uh_columns = set()

                # Create rooms and hints (skip duplicates by name)
                for idx, rdata in enumerate(rooms_data):
                        is_first_room = (idx == 0)

                        room = Room.query.filter_by(name=rdata['name']).first()
                        if not room:
                                room = Room(name=rdata['name'], description=rdata['description'], image_url=rdata.get('image_url'))
                                db.session.add(room)
                                db.session.commit()
                                print(f"Created room: {room.name} (id={room.id})")
                        else:
                                print(f"Room already exists: {room.name} (id={room.id})")

                        # Create hints for room
                        for hdata in rdata.get('hints', []):
                                # avoid duplicate hint titles for same room
                                existing = Hint.query.filter_by(room_id=room.id, title=hdata['title']).first()
                                if existing:
                                        print(f"  Hint exists: {existing.title} (id={existing.id})")
                                        continue
                                hint = Hint(room_id=room.id, title=hdata['title'], description=hdata['description'], image_url=hdata.get('image_url'))
                                db.session.add(hint)
                                db.session.commit()
                                print(f"  Created hint: {hint.title} (id={hint.id})")

                        # Ensure test user has access to the room via UsuarioRoom if not exists
                        ur = UsuarioRoom.query.filter_by(usuario_id=user.id, room_id=room.id).first()
                        if not ur:
                                # only first room unlocked by default
                                ur = UsuarioRoom(usuario_id=user.id, room_id=room.id, completed=False, is_unlocked=is_first_room)
                                db.session.add(ur)
                                db.session.commit()
                                state = "unlocked" if is_first_room else "locked"
                                print(f"  Granted access for user {user.email} to room {room.name} ({state})")

                        # Ensure UsuarioHint entries exist for each hint (mark all as not completed)
                        hints = Hint.query.filter_by(room_id=room.id).order_by(Hint.id).all()
                        for h_idx, h in enumerate(hints):
                                uh = UsuarioHint.query.filter_by(usuario_id=user.id, hint_id=h.id).first()
                                if not uh:
                                        uh = UsuarioHint(usuario_id=user.id, hint_id=h.id, completed=False)
                                        # only unlock the first hint of the first room
                                        if is_first_room and h_idx == 0 and 'is_unlocked' in uh_columns:
                                                uh.is_unlocked = True
                                        db.session.add(uh)
                db.session.commit()

                print("Seeding complete.")


if __name__ == '__main__':
        seed()
