from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from sqlalchemy import String, types, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from flask_login import UserMixin
from db.init import db
import uuid


class Usuario(db.Model, UserMixin):
    __tablename__ = "usuarios"

    def get_id(self) -> str:
        return str(self.id)
    id: Mapped[uuid.UUID] = mapped_column(
        types.Uuid, primary_key=True, default=uuid.uuid4)
    nombre: Mapped[str] = mapped_column(String(50), nullable=False)
    apellido: Mapped[str] = mapped_column(String(50), nullable=False)
    email: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False)
    password: Mapped[str] = mapped_column(String(255), nullable=False)
    global_position: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True)
    total_points: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, default=0)
    role: Mapped[str] = mapped_column(String(50), nullable=False, default='USER')
