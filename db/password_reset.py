from __future__ import annotations

from typing import Optional

from sqlalchemy import String, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from db.init import db
import uuid
from datetime import datetime, timezone


class PasswordReset(db.Model):
    __tablename__ = "password_resets"

    id: Mapped[uuid.UUID] = mapped_column(db.types.Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuarios.id"), nullable=False)
    code: Mapped[str] = mapped_column(String(6), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    def is_valid(self) -> bool:
        return (not self.used) and (self.expires_at > datetime.now(timezone.utc))
