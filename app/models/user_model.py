from builtins import bool, int, str
from datetime import datetime, timezone, timedelta
from enum import Enum
import uuid

from sqlalchemy import (
    Column, String, Integer, DateTime, Boolean, func, Enum as SQLAlchemyEnum
)
from sqlalchemy.dialects.postgresql import UUID, ENUM
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import TypeDecorator, DateTime as SADateTime

from app.database import Base


class UTCDateTime(TypeDecorator):
    """
    Ensures timezone-aware UTC datetimes across dialects (incl. SQLite which drops tzinfo).
    - On bind: coerce to UTC, ensure tzinfo.
    - On result: attach UTC tzinfo if missing.
    """
    impl = SADateTime
    cache_ok = True

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("timezone", True)
        super().__init__(*args, **kwargs)

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value


class UserRole(Enum):
    """Enumeration of user roles within the application, stored as ENUM in the database."""
    ANONYMOUS = "ANONYMOUS"
    AUTHENTICATED = "AUTHENTICATED"
    MANAGER = "MANAGER"
    ADMIN = "ADMIN"


class User(Base):
    """
    Represents a user within the application, corresponding to the 'users' table in the database.
    """
    __tablename__ = "users"
    __mapper_args__ = {"eager_defaults": True}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nickname: Mapped[str] = Column(String(50), unique=True, nullable=False, index=True)
    email: Mapped[str] = Column(String(255), unique=True, nullable=False, index=True)
    first_name: Mapped[str] = Column(String(100), nullable=True)
    last_name: Mapped[str] = Column(String(100), nullable=True)
    bio: Mapped[str] = Column(String(500), nullable=True)
    profile_picture_url: Mapped[str] = Column(String(255), nullable=True)
    linkedin_profile_url: Mapped[str] = Column(String(255), nullable=True)
    github_profile_url: Mapped[str] = Column(String(255), nullable=True)
    role: Mapped[UserRole] = Column(SQLAlchemyEnum(UserRole, name='UserRole', create_constraint=True), nullable=False)
    is_professional: Mapped[bool] = Column(Boolean, default=False)
    professional_status_updated_at: Mapped[datetime] = Column(UTCDateTime(), nullable=True)
    last_login_at: Mapped[datetime] = Column(UTCDateTime(), nullable=True)
    failed_login_attempts: Mapped[int] = Column(Integer, default=0)
    is_locked: Mapped[bool] = Column(Boolean, default=False)
    created_at: Mapped[datetime] = Column(UTCDateTime(), server_default=func.now())
    updated_at: Mapped[datetime] = Column(UTCDateTime(), server_default=func.now(), onupdate=func.now())
    verification_token = Column(String, nullable=True)
    email_verified: Mapped[bool] = Column(Boolean, default=False, nullable=False)
    hashed_password: Mapped[str] = Column(String(255), nullable=False)

    def __repr__(self) -> str:
        return f"<User {self.nickname}, Role: {self.role.name}>"

    # Domain helpers
    def lock_account(self):
        self.is_locked = True

    def unlock_account(self):
        self.is_locked = False

    def verify_email(self):
        self.email_verified = True

    def has_role(self, role_name: UserRole) -> bool:
        return self.role == role_name

    def update_professional_status(self, status: bool):
        self.is_professional = status
        self.professional_status_updated_at = func.now()

    def touch_last_login(self):
        """Set last_login_at to a strictly increasing, timezone-aware (UTC) timestamp."""
        now = datetime.now(timezone.utc)
        if self.last_login_at is None:
            self.last_login_at = now
        else:
            self.last_login_at = max(now, self.last_login_at + timedelta(microseconds=1))
