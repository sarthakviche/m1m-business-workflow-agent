"""Initial schema: all tables, indexes, constraints, RLS policies — M1M MVP

Implements the complete DDL from TRD Section 4.
Row-Level Security is applied to every tenant-scoped table with the pattern:
    tenant_id = current_setting('app.current_tenant_id')::uuid
The backend's set_tenant_context() in db/session.py sets this before every query.

Revision ID: 0001
Revises: (none — first migration)
Create Date: 2026-08-07
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    # ------------------------------------------------------------------ #
    # Extensions                                                           #
    # ------------------------------------------------------------------ #
    conn.execute(sa.text("CREATE EXTENSION IF NOT EXISTS pgcrypto;"))
    # pg_trgm: fuzzy matching for customer/item name lookup
    conn.execute(sa.text("CREATE EXTENSION IF NOT EXISTS pg_trgm;"))

    # ------------------------------------------------------------------ #
    # tenant — no RLS (it's the root entity, not scoped to itself)         #
    # ------------------------------------------------------------------ #
    op.create_table(
        "tenant",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("business_name", sa.Text(), nullable=False),
        sa.Column("gstin", sa.Text(), nullable=True),
        sa.Column("state", sa.Text(), nullable=False),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("logo_url", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
    )

    # ------------------------------------------------------------------ #
    # app_user                                                             #
    # ------------------------------------------------------------------ #
    op.create_table(
        "app_user",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False),
        sa.Column("phone", sa.Text(), nullable=False, unique=True),
        sa.Column("name", sa.Text(), nullable=True),
        sa.Column("role", sa.Text(), nullable=False, server_default="owner"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
    )
    conn.execute(sa.text(
        "ALTER TABLE app_user ADD CONSTRAINT app_user_role_check "
        "CHECK (role IN ('owner','staff','accountant'))"
    ))
    op.create_index("idx_app_user_tenant", "app_user", ["tenant_id"])

    # ------------------------------------------------------------------ #
    # customer                                                             #
    # ------------------------------------------------------------------ #
    op.create_table(
        "customer",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("phone", sa.Text(), nullable=True),
        sa.Column("gstin", sa.Text(), nullable=True),
        sa.Column("state", sa.Text(), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("idx_customer_tenant", "customer", ["tenant_id"])
    # GIN trigram index for fuzzy name matching (pg_trgm)
    conn.execute(sa.text(
        "CREATE INDEX idx_customer_name_trgm ON customer "
        "USING gin (name gin_trgm_ops);"
    ))

    # ------------------------------------------------------------------ #
    # item                                                                 #
    # ------------------------------------------------------------------ #
    op.create_table(
        "item",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("hsn_code", sa.Text(), nullable=True),
        sa.Column("gst_rate_percent", sa.Numeric(5, 2), nullable=False),
        sa.Column("unit_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("unit", sa.Text(), server_default="pcs", nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("idx_item_tenant", "item", ["tenant_id"])
    conn.execute(sa.text(
        "CREATE INDEX idx_item_name_trgm ON item "
        "USING gin (name gin_trgm_ops);"
    ))

    # ------------------------------------------------------------------ #
    # stock                                                                #
    # ------------------------------------------------------------------ #
    op.create_table(
        "stock",
        sa.Column("item_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("item.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False),
        sa.Column("quantity_available", sa.Numeric(12, 2), nullable=False,
                  server_default="0"),
        sa.Column("last_updated", sa.TIMESTAMP(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
    )

    # ------------------------------------------------------------------ #
    # quotation                                                            #
    # ------------------------------------------------------------------ #
    op.create_table(
        "quotation",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("customer.id"), nullable=False),
        sa.Column("quotation_number", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="draft"),
        sa.Column("subtotal", sa.Numeric(14, 2), nullable=True),
        sa.Column("pdf_url", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("tenant_id", "quotation_number",
                            name="uq_quotation_tenant_number"),
    )
    conn.execute(sa.text(
        "ALTER TABLE quotation ADD CONSTRAINT quotation_status_check "
        "CHECK (status IN ('draft','sent','converted'))"
    ))

    # ------------------------------------------------------------------ #
    # quotation_line                                                       #
    # ------------------------------------------------------------------ #
    op.create_table(
        "quotation_line",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        # Denormalize tenant_id for simpler RLS (TRD Section 4 recommendation)
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False),
        sa.Column("quotation_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("quotation.id", ondelete="CASCADE"), nullable=False),
        sa.Column("item_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("item.id"), nullable=False),
        sa.Column("quantity", sa.Numeric(12, 2), nullable=False),
        sa.Column("unit_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("line_total", sa.Numeric(14, 2), nullable=False),
    )

    # ------------------------------------------------------------------ #
    # invoice                                                              #
    # ------------------------------------------------------------------ #
    op.create_table(
        "invoice",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("customer.id"), nullable=False),
        sa.Column("quotation_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("quotation.id"), nullable=True),
        sa.Column("invoice_number", sa.Text(), nullable=False),
        sa.Column("subtotal", sa.Numeric(14, 2), nullable=True),
        sa.Column("cgst_amount", sa.Numeric(14, 2), server_default="0", nullable=False),
        sa.Column("sgst_amount", sa.Numeric(14, 2), server_default="0", nullable=False),
        sa.Column("igst_amount", sa.Numeric(14, 2), server_default="0", nullable=False),
        sa.Column("total_amount", sa.Numeric(14, 2), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default="unpaid"),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("pdf_url", sa.Text(), nullable=True),
        sa.Column("tally_push_status", sa.Text(),
                  server_default="not_applicable", nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("tenant_id", "invoice_number",
                            name="uq_invoice_tenant_number"),
    )
    conn.execute(sa.text(
        "ALTER TABLE invoice ADD CONSTRAINT invoice_status_check "
        "CHECK (status IN ('unpaid','partially_paid','paid'))"
    ))
    conn.execute(sa.text(
        "ALTER TABLE invoice ADD CONSTRAINT invoice_tally_status_check "
        "CHECK (tally_push_status IN ('not_applicable','pending','pushed'))"
    ))
    op.create_index("idx_invoice_tenant_status", "invoice", ["tenant_id", "status"])
    # Partial index: only for unpaid/partially-paid — used by dues queries
    conn.execute(sa.text(
        "CREATE INDEX idx_invoice_due_date ON invoice(due_date) "
        "WHERE status != 'paid';"
    ))

    # ------------------------------------------------------------------ #
    # invoice_line                                                         #
    # ------------------------------------------------------------------ #
    op.create_table(
        "invoice_line",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        # Denormalized tenant_id for RLS
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False),
        sa.Column("invoice_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("invoice.id", ondelete="CASCADE"), nullable=False),
        sa.Column("item_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("item.id"), nullable=False),
        sa.Column("quantity", sa.Numeric(12, 2), nullable=False),
        sa.Column("unit_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("gst_rate_percent", sa.Numeric(5, 2), nullable=False),
        sa.Column("line_total", sa.Numeric(14, 2), nullable=False),
    )

    # ------------------------------------------------------------------ #
    # payment                                                              #
    # ------------------------------------------------------------------ #
    op.create_table(
        "payment",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        # Denormalized tenant_id for RLS
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False),
        sa.Column("invoice_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("invoice.id", ondelete="CASCADE"), nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("method", sa.Text(), nullable=True),
        sa.Column("paid_at", sa.TIMESTAMP(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
    )
    conn.execute(sa.text(
        "ALTER TABLE payment ADD CONSTRAINT payment_method_check "
        "CHECK (method IS NULL OR method IN ('upi','cash','bank_transfer'))"
    ))

    # ------------------------------------------------------------------ #
    # conversation_log                                                     #
    # ------------------------------------------------------------------ #
    op.create_table(
        "conversation_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False),
        sa.Column("channel", sa.Text(), nullable=False),
        sa.Column("direction", sa.Text(), nullable=False),
        sa.Column("raw_message", sa.Text(), nullable=True),
        sa.Column("detected_intent", sa.Text(), nullable=True),
        sa.Column("agent_invoked", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
    )
    conn.execute(sa.text(
        "ALTER TABLE conversation_log ADD CONSTRAINT convlog_channel_check "
        "CHECK (channel IN ('whatsapp','web'))"
    ))
    conn.execute(sa.text(
        "ALTER TABLE conversation_log ADD CONSTRAINT convlog_direction_check "
        "CHECK (direction IN ('inbound','outbound'))"
    ))
    op.create_index("idx_convlog_tenant_time", "conversation_log",
                    ["tenant_id", sa.text("created_at DESC")])

    # ------------------------------------------------------------------ #
    # tally_connection                                                     #
    # ------------------------------------------------------------------ #
    op.create_table(
        "tally_connection",
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("tenant.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("status", sa.Text(), server_default="not_connected", nullable=False),
        sa.Column("mode", sa.Text(), server_default="read_only", nullable=False),
        sa.Column("last_synced_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    conn.execute(sa.text(
        "ALTER TABLE tally_connection ADD CONSTRAINT tally_status_check "
        "CHECK (status IN ('not_connected','connected'))"
    ))

    # ------------------------------------------------------------------ #
    # external_id_map                                                      #
    # ------------------------------------------------------------------ #
    op.create_table(
        "external_id_map",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False),
        sa.Column("internal_entity_type", sa.Text(), nullable=False),
        sa.Column("internal_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("external_system", sa.Text(), nullable=False),
        sa.Column("external_id", sa.Text(), nullable=False),
    )

    # ================================================================== #
    # ROW-LEVEL SECURITY                                                  #
    # Applied to every tenant-scoped table.                               #
    # Policy: tenant_id must equal current_setting('app.current_tenant_id')
    # The backend sets this via SET LOCAL before every query.             #
    # ================================================================== #
    _rls_tables = [
        "app_user",
        "customer",
        "item",
        "stock",
        "quotation",
        "quotation_line",
        "invoice",
        "invoice_line",
        "payment",
        "conversation_log",
        "tally_connection",
        "external_id_map",
    ]

    for table in _rls_tables:
        conn.execute(sa.text(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;"))
        conn.execute(sa.text(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY;"))
        conn.execute(sa.text(
            f"CREATE POLICY tenant_isolation_{table} ON {table} "
            f"USING (tenant_id = current_setting('app.current_tenant_id')::uuid);"
        ))

    # RLS bypass for the service-role connection (Supabase service_role key bypasses RLS by default)
    # The above policies apply to the authenticated/app role connections.
    # No additional configuration needed — Supabase's service_role already bypasses RLS,
    # which is correct: the migration itself runs as service_role.


def downgrade() -> None:
    # Drop in reverse FK dependency order
    tables_in_order = [
        "external_id_map",
        "tally_connection",
        "conversation_log",
        "payment",
        "invoice_line",
        "invoice",
        "quotation_line",
        "quotation",
        "stock",
        "item",
        "customer",
        "app_user",
        "tenant",
    ]
    for table in tables_in_order:
        op.drop_table(table)
