from __future__ import annotations

from typing import Optional, TYPE_CHECKING, List

from sqlalchemy import Integer, String, types, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from db.init import db
import uuid


class Rol(db.Model):
    __tablename__ = "roles"

    id: Mapped[uuid.UUID] = mapped_column(
        types.Uuid, primary_key=True, default=uuid.uuid4)
    nombre: Mapped[str] = mapped_column(
        types.Enum('ADMIN', 'SOPOERTE', 'USER', 'HOST', name='nombre'),
        nullable=False,
        default='USER'
    )
    descripcion: Mapped[str] = mapped_column(String(200), nullable=True)

    # Foreign key to Usuario
    # Lista de usuarios que tienen este rol
    usuarios: Mapped[List["Usuario"]] = relationship(
        "Usuario",
        back_populates="role",
        lazy="selectin",
    )


if TYPE_CHECKING:
    # Import only for type checking to satisfy annotations without circular import at runtime
    from db.usuario import Usuario  # noqa: F401