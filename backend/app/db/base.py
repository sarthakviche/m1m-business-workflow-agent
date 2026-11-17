"""
SQLAlchemy declarative base shared by all ORM models.

All model classes inherit from Base, which means Base.metadata contains
the full schema that Alembic uses for autogenerate migrations.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """
    Declarative base for all M1M ORM models.
    Import this in every model file and inherit from it.
    """
    pass
