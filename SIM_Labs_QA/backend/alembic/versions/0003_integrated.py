"""Additive SIM Labs integration, no NexGrana financial migrations.
Revision: 0003_integrated
"""
from alembic import op
from app.db import Base
from app import integration_models
revision='0003_integrated'
down_revision='0002_liveops'
branch_labels=None
depends_on=None
TABLES=['project_configs','releases','artifacts','integration_receipts','evidence','test_runs','decisions','messages','regression_cases','daily_reports','jobs','leases']
def upgrade():
    # New tables only; existing foundation tables are deliberately preserved.
    bind=op.get_bind()
    for table in Base.metadata.sorted_tables:
        if table.name in TABLES:
            table.create(bind, checkfirst=False)
def downgrade():
    for table in reversed(Base.metadata.sorted_tables):
        if table.name in TABLES:
            table.drop(op.get_bind())
