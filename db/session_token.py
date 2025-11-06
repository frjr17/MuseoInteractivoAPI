from __future__ import annotations

from datetime import datetime
from sqlalchemy import String, Boolean, DateTime
from sqlalchemy import types as sa_types
from sqlalchemy.orm import Mapped, mapped_column, relationship
from db.init import db


class SessionToken(db.Model):
    __tablename__ = "session_tokens"

    # store only the sha256 hex of the token
    token_hash: Mapped[str] = mapped_column(String(128), primary_key=True)
    usuario_id: Mapped[sa_types.Uuid] = mapped_column(
        sa_types.Uuid, db.ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    revoked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    last_used: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    usuario = relationship("Usuario", backref="session_tokens")
