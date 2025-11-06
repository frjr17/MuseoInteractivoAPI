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
import json

# Load environment variables from .env file if present
dotenv.load_dotenv()

# Environment-configurable hosts (defaults keep previous hardcoded hosts)
# Load optional data file (scripts/data.json) so values can come from JSON or env
DATA_FILE = os.path.join(os.path.dirname(__file__), "data.json")
try:
    with open(DATA_FILE, "r") as _f:
        _DATA = json.load(_f)
except Exception:
    _DATA = {}

LIME_SURVEY_HOST = os.getenv("LIME_SURVEY_HOST") or _DATA.get("LIME_SURVEY_HOST")
FILES_HOST = os.getenv("FILES_HOST") or _DATA.get("FILES_HOST")


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


# All required data (test_user, rooms) must come from scripts/data.json
TEST_USER = _DATA.get("test_user")
if not isinstance(TEST_USER, dict):
    raise RuntimeError("scripts/data.json must contain a top-level 'test_user' object with keys: email,nombre,apellido,password")


def seed():
    with app.app_context():
        # Create tables (if not present)
        db.create_all()

        # Source rooms data from data.json (required)
        rooms_info = _DATA.get("rooms")
        if not isinstance(rooms_info, list) or len(rooms_info) == 0:
            raise RuntimeError("scripts/data.json must contain a top-level 'rooms' array with room definitions")

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
        for idx, room_info in enumerate(rooms_info):
            is_first_room = idx == 0

            base_name = room_info.get("base_name") or room_info.get("name")
            if not base_name:
                raise RuntimeError(f"room at index {idx} in scripts/data.json is missing 'base_name'")
            full_room_name = f"Sala {idx+1}: {base_name}"

            room = Room.query.filter_by(name=full_room_name).first()
            if not room:
                # determine final_code only from data.json (None if not provided)
                final_code = room_info.get("final_code") if isinstance(room_info, dict) else None
                room = Room(name=full_room_name, final_code=final_code)
                db.session.add(room)
                db.session.commit()
                print(
                    f"Created room: {room.name} (id={room.id}) final_code={final_code}"
                )
            else:
                print(f"Room already exists: {room.name} (id={room.id})")

            # Build hint titles from data.json if present, otherwise default to Pista 1..5
            hints_list = []
            if isinstance(room_info, dict) and isinstance(room_info.get("hints"), list):
                hints_list = room_info.get("hints")
            else:
                hints_list = [f"Pista {n}" for n in range(1, 6)]

            for hint_idx, hint_item in enumerate(hints_list, start=1):
                # hint_item may be a string (legacy) or an object with name/access_code
                if isinstance(hint_item, dict):
                    title = hint_item.get("name") or f"Pista {hint_idx}"
                    access_code = hint_item.get("access_code")
                else:
                    title = str(hint_item)
                    access_code = None

                # avoid duplicate hint titles for same room
                existing = Hint.query.filter_by(room_id=room.id, title=title).first()
                if existing:
                    print(f"  Hint exists: {existing.title} (id={existing.id})")
                    # ensure access_code is set if missing
                    if access_code and existing.access_code != access_code:
                        existing.access_code = access_code
                        db.session.add(existing)
                        db.session.commit()
                    continue

                lime_path = f"index.php/S{room.id}P{hint_idx}"
                lime_url = _join_host_path(LIME_SURVEY_HOST, lime_path)

                image_path = f"S{room.id}P{hint_idx}.png"
                image_url = _join_host_path(FILES_HOST, image_path)
                hint = Hint(
                    room_id=room.id,
                    title=title,
                    image_url=image_url,
                    lime_survey_url=lime_url,
                    access_code=access_code,
                )
                db.session.add(hint)
                db.session.commit()
                print(f"  Created hint: {hint.title} (id={hint.id}) survey={lime_url} access_code={access_code}")

            # Ensure test user has access to the room via UsuarioRoom if not exists
            ur = UsuarioRoom.query.filter_by(
                usuario_id=user.id, room_id=room.id
            ).first()
            if not ur:
                # only first room unlocked by default
                ur = UsuarioRoom(
                    usuario_id=user.id,
                    room_id=room.id,
                    completed=False,
                    is_unlocked=is_first_room,
                )
                db.session.add(ur)
                db.session.commit()
                state = "unlocked" 
                print(
                    f"  Granted access for user {user.email} to room {room.name} ({state})"
                )

            # Ensure UsuarioHint entries exist for each hint (mark all as not completed)
            hints = Hint.query.filter_by(room_id=room.id).order_by(Hint.id).all()
            for _, h in enumerate(hints):
                uh = UsuarioHint.query.filter_by(
                    usuario_id=user.id, hint_id=h.id
                ).first()
                if not uh:
                    uh = UsuarioHint(
                        usuario_id=user.id, hint_id=h.id, completed=is_first_room
                    )
                   
                    db.session.add(uh)
        db.session.commit()

        print("Seeding complete.")


if __name__ == "__main__":
    seed()
