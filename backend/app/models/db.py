from sqlalchemy import JSON, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.security import utc_now
from app.db import Base


class UserSession(Base):
    __tablename__ = "user_sessions"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    spotify_user_id: Mapped[str | None] = mapped_column(String(128), index=True, nullable=True)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    csrf_token: Mapped[str] = mapped_column(String(128), nullable=False)
    token_info: Mapped[dict] = mapped_column(JSON, nullable=False)
    last_action: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
