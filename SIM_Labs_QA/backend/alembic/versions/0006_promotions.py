"""Private commercial catalog; additive, preserves all existing operations."""
from alembic import op
from app.promotion_models import PromotionSource,PromotionOffer,PromotionRun,PromotionControl
revision='0006_promotions'
down_revision='0005_runner_reports'
branch_labels=None
depends_on=None

def upgrade():
 for model in (PromotionSource,PromotionOffer,PromotionRun,PromotionControl):model.__table__.create(op.get_bind())

def downgrade():raise RuntimeError('Downgrade exige backup revisado; não remover histórico comercial automaticamente.')
