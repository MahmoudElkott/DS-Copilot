# backend/app/models/database.py
"""
Database initialization utilities.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import settings
from app.infrastructure.memory import Base


def get_engine():
    """Get SQLAlchemy engine."""
    return create_engine(settings.DATABASE_URL)


def init_db():
    """Initialize database tables."""
    engine = get_engine()
    Base.metadata.create_all(engine)
    return engine


def get_session():
    """Get a new database session."""
    engine = get_engine()
    Session = sessionmaker(bind=engine)
    return Session()
