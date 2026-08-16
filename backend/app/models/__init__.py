"""
M1M models package.

Importing this module registers ALL ORM models with Base.metadata,
which is required for:
  1. Alembic autogenerate to discover all tables.
  2. SQLAlchemy relationship resolution across models.

Any new model file must be imported here.
"""

from app.models.tenant import Tenant
from app.models.app_user import AppUser
from app.models.customer import Customer
from app.models.item import Item
from app.models.stock import Stock
from app.models.quotation import Quotation, QuotationLine
from app.models.invoice import Invoice, InvoiceLine
from app.models.payment import Payment
from app.models.conversation_log import ConversationLog
from app.models.tally import TallyConnection, ExternalIdMap

__all__ = [
    "Tenant",
    "AppUser",
    "Customer",
    "Item",
    "Stock",
    "Quotation",
    "QuotationLine",
    "Invoice",
    "InvoiceLine",
    "Payment",
    "ConversationLog",
    "TallyConnection",
    "ExternalIdMap",
]
