"""
SQLAlchemy base database model.

@author "Daniel Mizsak" <daniel@mizsak.com>
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all database models."""
