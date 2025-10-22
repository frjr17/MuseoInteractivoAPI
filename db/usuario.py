from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from sqlalchemy import String, types, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from db.init import db
import uuid


class Usuario(db.Model):
    __tablename__ = "usuarios"

    id: Mapped[uuid.UUID] = mapped_column(
        types.Uuid, primary_key=True, default=uuid.uuid4)
    nombre: Mapped[str] = mapped_column(String(50), nullable=False)
    apellido: Mapped[str] = mapped_column(String(50), nullable=False)
    email: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False)
    password: Mapped[str] = mapped_column(String(100), nullable=False)

    # Un Usuario tiene un solo Rol
    role_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        # FK hacia roles.id; SET NULL para no borrar usuarios si se borra el rol
        types.Uuid,
        ForeignKey("roles.id", ondelete="SET NULL"),
        nullable=True,
    )

    role: Mapped[Optional["Rol"]] = relationship(
        "Rol",
        back_populates="usuarios",
        lazy="selectin",
    )


if TYPE_CHECKING:
    # Import only for type checking to satisfy annotations without circular import at runtime
    from db.rol import Rol  # noqa: F401

