from __future__ import annotations

from typing import Optional

from sqlalchemy import Integer, String, Boolean
from sqlalchemy import types as sa_types
from sqlalchemy.orm import Mapped, mapped_column, relationship
from db.init import db


# association table for many-to-many between usuarios and rooms
usuarios_rooms = db.Table(
    "usuarios_rooms",
    db.Column("usuario_id", sa_types.Uuid, db.ForeignKey("usuarios.id", ondelete="CASCADE"), primary_key=True),
    db.Column("room_id", Integer, db.ForeignKey("rooms.id", ondelete="CASCADE"), primary_key=True),
)


class Room(db.Model):
    __tablename__ = "rooms"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(2000), nullable=False)
    image_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_unlocked: Mapped[bool] = mapped_column(Boolean, nullable=True, default=False)

    # backref to users that have access
    usuarios: Mapped[list] = relationship(
        "Usuario",
        secondary=usuarios_rooms,
        back_populates="rooms",
        lazy="selectin",
    )


class Hint(db.Model):
    __tablename__ = "hints"

    # use integer autoincrement id for easier management
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    room_id: Mapped[int] = mapped_column(Integer, db.ForeignKey("rooms.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(2000), nullable=False)
    image_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    room: Mapped[Optional[Room]] = relationship("Room", backref="hints", lazy="selectin")
