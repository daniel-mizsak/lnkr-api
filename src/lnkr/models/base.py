"""
SQLAlchemy base database model.

@author "Daniel Mizsak" <info@pythonvilag.hu>
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all database models."""
