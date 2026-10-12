"""Phase A foundation schema
Revision ID: 0001_phase_a
Revises: 
"""
from alembic import op
import sqlalchemy as sa

revision = "0001_phase_a"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("products", sa.Column("id", sa.String(36), primary_key=True), sa.Column("slug", sa.String(80), nullable=False), sa.Column("name", sa.String(160), nullable=False), sa.Column("status", sa.String(30), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.UniqueConstraint("slug"))
    op.create_index("ix_products_slug", "products", ["slug"], unique=False)
    op.create_table("sectors", sa.Column("id", sa.String(36), primary_key=True), sa.Column("slug", sa.String(80), nullable=False), sa.Column("name", sa.String(160), nullable=False), sa.Column("description", sa.Text(), nullable=False), sa.UniqueConstraint("slug"))
    op.create_index("ix_sectors_slug", "sectors", ["slug"], unique=False)
    op.create_table("team_members", sa.Column("id", sa.String(36), primary_key=True), sa.Column("canonical_name", sa.String(120), nullable=False), sa.Column("canonical_role", sa.String(160), nullable=False), sa.Column("responsibility", sa.Text(), nullable=False), sa.Column("active", sa.Boolean(), nullable=False), sa.UniqueConstraint("canonical_name"))
    op.create_index("ix_team_members_canonical_name", "team_members", ["canonical_name"], unique=False)
    op.create_table("user_identities", sa.Column("id", sa.String(36), primary_key=True), sa.Column("member_id", sa.String(36), sa.ForeignKey("team_members.id", ondelete="CASCADE"), nullable=False), sa.Column("provider", sa.String(40), nullable=False), sa.Column("external_uid", sa.String(180), nullable=False), sa.UniqueConstraint("external_uid"))
    op.create_index("ix_user_identities_member_id", "user_identities", ["member_id"], unique=False)
    op.create_index("ix_user_identities_external_uid", "user_identities", ["external_uid"], unique=False)
    op.create_table("memberships", sa.Column("id", sa.String(36), primary_key=True), sa.Column("member_id", sa.String(36), sa.ForeignKey("team_members.id", ondelete="CASCADE"), nullable=False), sa.Column("product_id", sa.String(36), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False), sa.Column("role", sa.String(50), nullable=False), sa.Column("environment", sa.String(20), nullable=False), sa.Column("active", sa.Boolean(), nullable=False), sa.UniqueConstraint("member_id", "product_id", "role", "environment", name="uq_membership_scope"))
    op.create_index("ix_memberships_member_id", "memberships", ["member_id"], unique=False)
    op.create_index("ix_memberships_product_id", "memberships", ["product_id"], unique=False)
    op.create_index("ix_memberships_role", "memberships", ["role"], unique=False)
    op.create_table("audit_events", sa.Column("id", sa.String(36), primary_key=True), sa.Column("actor_member_id", sa.String(36), sa.ForeignKey("team_members.id"), nullable=True), sa.Column("actor_type", sa.String(30), nullable=False), sa.Column("action", sa.String(120), nullable=False), sa.Column("object_type", sa.String(80), nullable=False), sa.Column("object_id", sa.String(120), nullable=True), sa.Column("product_id", sa.String(36), sa.ForeignKey("products.id"), nullable=True), sa.Column("reason", sa.Text(), nullable=True), sa.Column("correlation_id", sa.String(80), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    for col in ["actor_member_id", "action", "object_type", "product_id", "correlation_id", "created_at"]:
        op.create_index(f"ix_audit_events_{col}", "audit_events", [col], unique=False)


def downgrade():
    op.drop_table("audit_events")
    op.drop_table("memberships")
    op.drop_table("user_identities")
    op.drop_table("team_members")
    op.drop_table("sectors")
    op.drop_table("products")
