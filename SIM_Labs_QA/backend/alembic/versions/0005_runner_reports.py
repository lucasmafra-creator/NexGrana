"""Additive receipt enforcing runner report deduplication."""
from alembic import op
from app.integration_models import RunnerReportReceipt
revision='0005_runner_reports'
down_revision='0004_engine'
branch_labels=None
depends_on=None

def upgrade():
    RunnerReportReceipt.__table__.create(op.get_bind())

def downgrade():
    raise RuntimeError('Downgrade requer restauração de backup revisado.')
