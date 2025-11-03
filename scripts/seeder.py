"""Seed script for MuseoInteractivoAPI.

Creates sample rooms, hints, a test user, and per-user access records.

Run with:
    python seeder.py

This script is idempotent for basic runs (it will not duplicate rooms/hints by name).
"""

from datetime import datetime
import uuid

from werkzeug.security import generate_password_hash
import os
import dotenv

# Load environment variables from .env file if present
dotenv.load_dotenv()

# Environment-configurable hosts (defaults keep previous hardcoded hosts)
LIME_SURVEY_HOST = os.getenv("LIME_SURVEY_HOST")
FILES_HOST = os.getenv("FILES_HOST")


def _join_host_path(host: str, path: str) -> str:
    """Join host and path ensuring there is exactly one slash between them."""
    if not host:
        return path
    host = host.rstrip("/")
    path = path.lstrip("/")
    return f"{host}/{path}"


from main import app
from db.init import db
from db.usuario import Usuario
from db.room import Room, Hint, UsuarioRoom, UsuarioHint


ROOM_NAMES = [
    "El Secreto del Canal",
    "Leyendas Panameñas",
    "El tesoro verde de Panamá",
    "Sabores y Colores de Panamá",
    "Las llaves de la ciudad",
]

# We'll generate 5 hints per room named "Pista 1" .. "Pista 5" and set
# the lime_survey_url and image_url based on the created room.id and hint index.


TEST_USER = {
    "email": "test@example.com",
    "nombre": "Test",
    "apellido": "User",
    "password": "secret",
}


def seed():
    with app.app_context():
        # Create tables (if not present)
        db.create_all()

        # Use ROOM_NAMES and generate 5 hints per room
        rooms_data = ROOM_NAMES

        # Create or get test user
        user = Usuario.query.filter_by(email=TEST_USER["email"]).first()
        if not user:
            print("Creating test user", TEST_USER["email"])
            user = Usuario(
                id=uuid.uuid4(),
                nombre=TEST_USER["nombre"],
                apellido=TEST_USER["apellido"],
                email=TEST_USER["email"],
                password=generate_password_hash(TEST_USER["password"]),
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
        for idx, room_name in enumerate(rooms_data):
            is_first_room = idx == 0

            full_room_name = f"Sala {idx+1}: {room_name}"

            room = Room.query.filter_by(name=full_room_name).first()
            if not room:
                # set final_code from the images (best-effort values)
                final_codes = [
                    "1881-1904-1914-1999",
                    "Ru-ben-Bla-des-Patria",
                    "F-A-U-N-A",
                    "9-7-5-3-1",
                    "1-3-5-7-9",
                ]
                final_code = final_codes[idx] if idx < len(final_codes) else None
                room = Room(name=full_room_name, final_code=final_code)
                db.session.add(room)
                db.session.commit()
                print(
                    f"Created room: {room.name} (id={room.id}) final_code={final_code}"
                )
            else:
                print(f"Room already exists: {room.name} (id={room.id})")

            # Create 5 hints for room (Pista 1..5)
            for hint_num in range(1, 6):
                title = f"Pista {hint_num}"
                # avoid duplicate hint titles for same room
                existing = Hint.query.filter_by(room_id=room.id, title=title).first()
                if existing:
                    print(f"  Hint exists: {existing.title} (id={existing.id})")
                    continue
                lime_path = f"index.php/S{room.id}P{hint_num}"
                lime_url = _join_host_path(LIME_SURVEY_HOST, lime_path)

                image_path = f"S{room.id}P{hint_num}.png"
                image_url = _join_host_path(FILES_HOST, image_path)
                hint = Hint(
                    room_id=room.id,
                    title=title,
                    image_url=image_url,
                    lime_survey_url=lime_url,
                )
                db.session.add(hint)
                db.session.commit()
                print(f"  Created hint: {hint.title} (id={hint.id}) survey={lime_url}")

            # Ensure test user has access to the room via UsuarioRoom if not exists
            ur = UsuarioRoom.query.filter_by(
                usuario_id=user.id, room_id=room.id
            ).first()
            if not ur:
                # only first room unlocked by default
                ur = UsuarioRoom(
                    usuario_id=user.id,
                    room_id=room.id,
                    completed=is_first_room,
                    is_unlocked=(is_first_room or room.id == 2),
                )
                db.session.add(ur)
                db.session.commit()
                state = "unlocked" if is_first_room else "locked"
                print(
                    f"  Granted access for user {user.email} to room {room.name} ({state})"
                )

            # Ensure UsuarioHint entries exist for each hint (mark all as not completed)
            hints = Hint.query.filter_by(room_id=room.id).order_by(Hint.id).all()
            for h_idx, h in enumerate(hints):
                uh = UsuarioHint.query.filter_by(
                    usuario_id=user.id, hint_id=h.id
                ).first()
                if not uh:
                    uh = UsuarioHint(
                        usuario_id=user.id, hint_id=h.id, completed=is_first_room
                    )
                    # only unlock the first hint of the first room
                    if is_first_room and h_idx == 0 and "is_unlocked" in uh_columns:
                        uh.is_unlocked = True
                    db.session.add(uh)
        db.session.commit()

        print("Seeding complete.")


if __name__ == "__main__":
    seed()
