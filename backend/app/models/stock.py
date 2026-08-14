"""SQLAlchemy ORM model: stock"""
import uuid
from datetime import datetime
from decimal import Decimal
from sqlalchemy import text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import TIMESTAMP, Numeric
from app.db.session import Base


class Stock(Base):
    __tablename__ = "stock"

    item_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True),
                                                ForeignKey("item.id", ondelete="CASCADE"),
                                                primary_key=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True),
                                                  ForeignKey("tenant.id", ondelete="CASCADE"),
                                                  nullable=False)
    quantity_available: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False,
                                                         server_default="0")
    last_updated: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True),
                                                    server_default=text("now()"))
