"""INSERT ... ON CONFLICT for the databases we run on. Both dialects build the same statement."""

from sqlalchemy.dialects.postgresql import insert as postgres_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession


def upsert_insert(session: AsyncSession, model):
    return (sqlite_insert if session.get_bind().dialect.name == "sqlite" else postgres_insert)(model)
