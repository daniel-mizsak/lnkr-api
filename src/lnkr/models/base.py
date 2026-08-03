"""
SQLAlchemy base database model.

Copyright (C) 2026 "Daniel Mizsak" <daniel@mizsak.com>
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all database models."""
