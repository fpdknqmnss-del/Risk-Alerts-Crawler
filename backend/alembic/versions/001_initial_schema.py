"""Initial schema — all tables for travel risk alert platform

Revision ID: 001_initial
Revises:
Create Date: 2026-02-10

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import geoalchemy2
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# ---------- Enum types (created explicitly so we can drop them in downgrade) ----------
userrole_enum = postgresql.ENUM("admin", "viewer", name="userrole", create_type=False)
alertcategory_enum = postgresql.ENUM(
    "natural_disaster",
    "political",
    "crime",
    "health",
    "terrorism",
    "civil_unrest",
    name="alertcategory",
    create_type=False,
)
reportstatus_enum = postgresql.ENUM(
    "draft",
    "pending_approval",
    "approved",
    "sent",
    name="reportstatus",
    create_type=False,
)


def upgrade() -> None:
    # Enable PostGIS extension
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")

    # --- Create enum types first ---
    userrole_enum.create(op.get_bind(), checkfirst=True)
    alertcategory_enum.create(op.get_bind(), checkfirst=True)
    reportstatus_enum.create(op.get_bind(), checkfirst=True)

    # --- 1. users (no FK dependencies) ---
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("role", userrole_enum, nullable=False, server_default="viewer"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    # --- 2. alerts (no FK dependencies) ---
    op.create_table(
        "alerts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("full_content", sa.Text(), nullable=True),
        sa.Column("category", alertcategory_enum, nullable=False),
        sa.Column("severity", sa.Integer(), nullable=False),
        sa.Column("country", sa.String(length=100), nullable=False),
        sa.Column("region", sa.String(length=255), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column(
            "location",
            geoalchemy2.types.Geometry(geometry_type="POINT", srid=4326),
            nullable=True,
        ),
        sa.Column("sources", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("verified", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("verification_score", sa.Float(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_alerts_category"), "alerts", ["category"])
    op.create_index(op.f("ix_alerts_severity"), "alerts", ["severity"])
    op.create_index(op.f("ix_alerts_country"), "alerts", ["country"])

    # --- 3. reports (FK → users) ---
    op.create_table(
        "reports",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("content_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("pdf_path", sa.String(length=500), nullable=True),
        sa.Column("status", reportstatus_enum, nullable=False, server_default="draft"),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column("approved_by", sa.Integer(), nullable=True),
        sa.Column("geographic_scope", sa.String(length=500), nullable=True),
        sa.Column("date_range_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("date_range_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], name="fk_reports_created_by"),
        sa.ForeignKeyConstraint(["approved_by"], ["users.id"], name="fk_reports_approved_by"),
    )
    op.create_index(op.f("ix_reports_status"), "reports", ["status"])

    # --- 4. mailing_lists (FK → users) ---
    op.create_table(
        "mailing_lists",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("geographic_regions", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_mailing_lists_name"),
        sa.ForeignKeyConstraint(
            ["created_by"], ["users.id"], name="fk_mailing_lists_created_by"
        ),
    )

    # --- 5. subscribers (FK → mailing_lists) ---
    op.create_table(
        "subscribers",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("organization", sa.String(length=255), nullable=True),
        sa.Column("mailing_list_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["mailing_list_id"],
            ["mailing_lists.id"],
            name="fk_subscribers_mailing_list_id",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("email", "mailing_list_id", name="uq_subscriber_email_list"),
    )
    op.create_index(op.f("ix_subscribers_email"), "subscribers", ["email"])

    # --- 6. raw_news_items (no FK dependencies) ---
    op.create_table(
        "raw_news_items",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("source", sa.String(length=100), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("url", sa.String(length=1024), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("country", sa.String(length=100), nullable=True),
        sa.Column("region", sa.String(length=255), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "fetched_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source", "url", name="uq_raw_news_source_url"),
    )
    op.create_index(op.f("ix_raw_news_items_source"), "raw_news_items", ["source"])
    op.create_index(op.f("ix_raw_news_items_published_at"), "raw_news_items", ["published_at"])
    op.create_index(op.f("ix_raw_news_items_country"), "raw_news_items", ["country"])
    op.create_index(op.f("ix_raw_news_items_fetched_at"), "raw_news_items", ["fetched_at"])


def downgrade() -> None:
    # Drop tables in reverse order (FK-dependent tables first)
    op.drop_index(op.f("ix_raw_news_items_fetched_at"), table_name="raw_news_items")
    op.drop_index(op.f("ix_raw_news_items_country"), table_name="raw_news_items")
    op.drop_index(op.f("ix_raw_news_items_published_at"), table_name="raw_news_items")
    op.drop_index(op.f("ix_raw_news_items_source"), table_name="raw_news_items")
    op.drop_table("raw_news_items")

    op.drop_index(op.f("ix_subscribers_email"), table_name="subscribers")
    op.drop_table("subscribers")

    op.drop_table("mailing_lists")

    op.drop_index(op.f("ix_reports_status"), table_name="reports")
    op.drop_table("reports")

    op.drop_index(op.f("ix_alerts_country"), table_name="alerts")
    op.drop_index(op.f("ix_alerts_severity"), table_name="alerts")
    op.drop_index(op.f("ix_alerts_category"), table_name="alerts")
    op.drop_table("alerts")

    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")

    # Drop enum types last (after tables that reference them are gone)
    reportstatus_enum.drop(op.get_bind(), checkfirst=True)
    alertcategory_enum.drop(op.get_bind(), checkfirst=True)
    userrole_enum.drop(op.get_bind(), checkfirst=True)

    op.execute("DROP EXTENSION IF EXISTS postgis")
