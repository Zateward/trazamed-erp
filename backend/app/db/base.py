"""
SQLAlchemy declarative base.
Kept separate from session.py so Alembic can import Base (and thus all
model metadata) without triggering the async engine creation.
"""
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
