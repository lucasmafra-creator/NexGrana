"""Additive 24/7 operations; downgrade intentionally requires manual backup review."""
from alembic import op
from app.db import Base
from app import models, integration_models, engine_models
revision='0004_engine'
down_revision='0003_integrated'
branch_labels=None
depends_on=None
TABLES={'engine_config','engine_workers','engine_schedules','engine_jobs','engine_incidents','learning_notes'}
def upgrade():
    for t in Base.metadata.sorted_tables:
        if t.name in TABLES: t.create(op.get_bind())
def downgrade():
    raise RuntimeError('Downgrade bloqueado: restaure um backup revisado para preservar evidencias.')
