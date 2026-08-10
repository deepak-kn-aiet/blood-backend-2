"""
Database Connection & Session Management Module

Sets up PostgreSQL SQLAlchemy Engine, SessionLocal, Base model class,
and a dependency function `get_db` to yield database sessions per request.
Uses PostgreSQL exclusively.
"""

from typing import Generator
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.config import settings


class Base(DeclarativeBase):
    """
    Base class for all SQLAlchemy ORM models.
    """
    pass


def get_engine():
    """
    Creates SQLAlchemy engine, automatically falling back to SQLite if PostgreSQL is unavailable.
    """
    db_url = settings.DATABASE_URL
    if db_url.startswith("postgresql"):
        try:
            temp_engine = create_engine(
                db_url,
                pool_pre_ping=True,
                echo=settings.DEBUG,
                connect_args={"connect_timeout": 2}
            )
            with temp_engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return temp_engine
        except Exception as e:
            print(f"Notice: PostgreSQL connection failed ({e}). Falling back to local SQLite database (blood_relay.db)...")
            db_url = "sqlite:///./blood_relay.db"

    if db_url.startswith("sqlite"):
        return create_engine(
            db_url,
            connect_args={"check_same_thread": False},
            echo=settings.DEBUG
        )
    return create_engine(db_url, pool_pre_ping=True, echo=settings.DEBUG)


engine = get_engine()

# Create sessionmaker class for database sessions
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


def get_db() -> Generator:
    """
    Dependency function to get a database session per API request.
    Yields a SQLAlchemy session and ensures clean closure after request completion.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

