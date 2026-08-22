"""SQLite metadata database: users and sites tables."""

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel, create_engine, Session as SQLSession

from app.core.config import settings


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True, max_length=255)
    password_hash: str
    full_name: Optional[str] = Field(default=None, max_length=255)
    company_name: Optional[str] = Field(default=None, max_length=255)
    is_verified: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Subscription & Billing
    plan: str = Field(default="free", max_length=32)
    stripe_customer_id: Optional[str] = Field(default=None, max_length=255)
    stripe_subscription_id: Optional[str] = Field(default=None, max_length=255)
    subscription_status: Optional[str] = Field(default="active", max_length=32)
    monthly_pageview_limit: int = Field(default=10000)


class Site(SQLModel, table=True):
    __tablename__ = "sites"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    name: str = Field(max_length=128)
    domain: str = Field(max_length=255)
    public_token: str = Field(unique=True, index=True, max_length=64)
    site_id: str = Field(unique=True, index=True, max_length=64)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class EventRecord(SQLModel, table=True):
    __tablename__ = "event_records"

    id: Optional[int] = Field(default=None, primary_key=True)
    event_id: str = Field(index=True, max_length=64)
    site_id: str = Field(index=True, max_length=64)
    event_type: str = Field(default="pageview", max_length=32)
    timestamp: int = Field(index=True)
    url: str = Field(default="")
    path: str = Field(index=True, max_length=255)
    referrer: str = Field(default="", max_length=255)
    session_id: str = Field(index=True, max_length=64)
    visitor_id: str = Field(index=True, max_length=64)
    screen: str = Field(default="", max_length=32)
    device_type: str = Field(default="desktop", max_length=32)
    browser: str = Field(default="Chrome", max_length=32)
    country: str = Field(default="Unknown", max_length=64)
    created_at: datetime = Field(default_factory=datetime.utcnow)

class BotTrafficLog(SQLModel, table=True):
    __tablename__ = "bot_traffic_logs"

    id: Optional[int] = Field(default=None, primary_key=True)
    site_id: str = Field(index=True, max_length=64)
    bot_name: str = Field(max_length=64)
    target_url: str = Field(max_length=512)
    timestamp: int = Field(index=True)


class SessionReplay(SQLModel, table=True):
    __tablename__ = "session_replays"

    id: Optional[int] = Field(default=None, primary_key=True)
    site_id: str = Field(index=True, max_length=64)
    session_id: str = Field(index=True, max_length=64)
    path: str = Field(max_length=255)
    coordinates: str = Field(default="[]")  # stored as JSON string
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# Engine & session helpers
# ---------------------------------------------------------------------------

import os

_db_dir = os.path.dirname(settings.sqlite_path)
if _db_dir:
    os.makedirs(_db_dir, exist_ok=True)

if settings.database_url:
    # SQLModel works out of the box with PostgreSQL
    db_url = settings.database_url
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    engine = create_engine(db_url, echo=False)
else:
    engine = create_engine(f"sqlite:///{settings.sqlite_path}", echo=False)



def create_tables():
    SQLModel.metadata.create_all(engine)
    
    # Self-healing migrations for SQLite / PostgreSQL
    with SQLSession(engine) as session:
        from sqlalchemy import text
        
        try:
            session.execute(text("ALTER TABLE users ADD COLUMN is_verified BOOLEAN DEFAULT FALSE"))
            session.commit()
        except Exception:
            session.rollback()

        try:
            session.execute(text("ALTER TABLE users ADD COLUMN full_name VARCHAR(255) DEFAULT NULL"))
            session.commit()
        except Exception:
            session.rollback()

        try:
            session.execute(text("ALTER TABLE users ADD COLUMN company_name VARCHAR(255) DEFAULT NULL"))
            session.commit()
        except Exception:
            session.rollback()

        try:
            session.execute(text("ALTER TABLE users ADD COLUMN plan VARCHAR(32) DEFAULT 'free'"))
            session.commit()
        except Exception:
            session.rollback()

        try:
            session.execute(text("ALTER TABLE users ADD COLUMN stripe_customer_id VARCHAR(255) DEFAULT NULL"))
            session.commit()
        except Exception:
            session.rollback()

        try:
            session.execute(text("ALTER TABLE users ADD COLUMN stripe_subscription_id VARCHAR(255) DEFAULT NULL"))
            session.commit()
        except Exception:
            session.rollback()

        try:
            session.execute(text("ALTER TABLE users ADD COLUMN subscription_status VARCHAR(32) DEFAULT 'active'"))
            session.commit()
        except Exception:
            session.rollback()

        try:
            session.execute(text("ALTER TABLE users ADD COLUMN monthly_pageview_limit INTEGER DEFAULT 10000"))
            session.commit()
        except Exception:
            session.rollback()


def get_session():
    """FastAPI dependency that yields a SQLModel session."""
    with SQLSession(engine) as session:
        yield session
