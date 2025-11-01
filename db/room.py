from __future__ import annotations

from typing import Optional

from sqlalchemy import Integer, String, Boolean
from sqlalchemy import types as sa_types
from sqlalchemy.orm import Mapped, mapped_column, relationship
from db.init import db


# Association object for usuarios <-> rooms with per-user metadata
class UsuarioRoom(db.Model):
    __tablename__ = "usuarios_rooms"

    usuario_id: Mapped[sa_types.Uuid] = mapped_column(
        sa_types.Uuid, db.ForeignKey("usuarios.id", ondelete="CASCADE"), primary_key=True
    )
    room_id: Mapped[int] = mapped_column(Integer, db.ForeignKey("rooms.id", ondelete="CASCADE"), primary_key=True)
    # per-user flags
    completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_unlocked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # relationships to parent objects
    usuario = relationship("Usuario", back_populates="usuario_rooms")
    room = relationship("Room", back_populates="room_users")


class Room(db.Model):
    __tablename__ = "rooms"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    final_code: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    # convenience many-to-many to usuarios (via usuarios_rooms table)
    usuarios: Mapped[list] = relationship(
        "Usuario",
        secondary="usuarios_rooms",
        back_populates="rooms",
        lazy="selectin",
    )

    # access to the association objects for per-user metadata
    room_users: Mapped[list[UsuarioRoom]] = relationship("UsuarioRoom", back_populates="room", lazy="selectin")


class Hint(db.Model):
    __tablename__ = "hints"

    # use integer autoincrement id for easier management
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    room_id: Mapped[int] = mapped_column(Integer, db.ForeignKey("rooms.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    image_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    lime_survey_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    room: Mapped[Optional[Room]] = relationship("Room", backref="hints", lazy="selectin")


# Association table for per-user hint completion
class UsuarioHint(db.Model):
    __tablename__ = "usuarios_hints"

    usuario_id: Mapped[sa_types.Uuid] = mapped_column(
        sa_types.Uuid, db.ForeignKey("usuarios.id", ondelete="CASCADE"), primary_key=True
    )
    hint_id: Mapped[int] = mapped_column(Integer, db.ForeignKey("hints.id", ondelete="CASCADE"), primary_key=True)
    completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    usuario = relationship("Usuario", backref="usuario_hints")
    hint = relationship("Hint", backref="hint_users")
