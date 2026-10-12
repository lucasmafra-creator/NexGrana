"""Add operational sectors for build, offers, performance and QA-only chaos.

Revision ID: 0007_qa_operations
Revises: 0006_promotions
"""
from __future__ import annotations

import uuid
import sqlalchemy as sa
from alembic import op

revision = "0007_qa_operations"
down_revision = "0006_promotions"
branch_labels = None
depends_on = None

SECTORS = (
    ("build", "Build & Release", "Pré-flight e artefatos nativos; geração depende do host e de ferramentas disponíveis"),
    ("performance", "Performance", "Baselines, latência, memória e desempenho em aparelhos autorizados"),
    ("offers", "Ofertas & Parcerias", "Fontes autorizadas, catálogo, links e revisão comercial"),
    ("chaos_test", "Chaos Test", "Planejamento de resiliência em QA; injeção de falhas ainda desativada"),
)


def upgrade():
    bind = op.get_bind()
    sectors = sa.table(
        "sectors",
        sa.column("id", sa.String()),
        sa.column("slug", sa.String()),
        sa.column("name", sa.String()),
        sa.column("description", sa.Text()),
    )
    existing = set(bind.execute(sa.select(sectors.c.slug)).scalars())
    for slug, name, description in SECTORS:
        if slug not in existing:
            bind.execute(sa.insert(sectors).values(id=str(uuid.uuid4()), slug=slug, name=name, description=description))


def downgrade():
    # Preserve sector rows and any future work referring to them.
    pass
