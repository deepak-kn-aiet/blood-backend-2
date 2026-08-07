"""
Database Connection & Session Management Module

Sets up PostgreSQL SQLAlchemy Engine, SessionLocal, Base model class,
and a dependency function `get_db` to yield database sessions per request.
Uses PostgreSQL exclusively.
"""

from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.config import settings


class Base(DeclarativeBase):
    """
    Base class for all SQLAlchemy ORM models.
    """
    pass


# PostgreSQL SQLAlchemy Engine (Fails loudly if PostgreSQL is unreachable)
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    echo=settings.DEBUG,
)

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
