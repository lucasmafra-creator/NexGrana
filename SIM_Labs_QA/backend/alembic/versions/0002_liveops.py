"""LiveOps feedback, task and continuous automation
Revision ID: 0002_liveops
Revises: 0001_phase_a
"""
from alembic import op
import sqlalchemy as sa

revision = "0002_liveops"
down_revision = "0001_phase_a"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("sequence_counters",
        sa.Column("name", sa.String(50), primary_key=True),
        sa.Column("value", sa.Integer(), nullable=False),
    )
    op.create_table("feedbacks",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("human_id", sa.String(30), nullable=False),
        sa.Column("product_id", sa.String(36), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_by_member_id", sa.String(36), sa.ForeignKey("team_members.id"), nullable=True),
        sa.Column("category", sa.String(40), nullable=False),
        sa.Column("title", sa.String(180), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("expected", sa.Text(), nullable=True),
        sa.Column("observed", sa.Text(), nullable=True),
        sa.Column("severity", sa.String(10), nullable=False),
        sa.Column("priority", sa.String(10), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("source", sa.String(40), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("human_id"),
    )
    for col in ["human_id","product_id","created_by_member_id","category","severity","priority","status","created_at"]:
        op.create_index(f"ix_feedbacks_{col}", "feedbacks", [col], unique=False)
    op.create_table("tasks",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("human_id", sa.String(30), nullable=False),
        sa.Column("product_id", sa.String(36), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_feedback_id", sa.String(36), sa.ForeignKey("feedbacks.id", ondelete="SET NULL"), nullable=True),
        sa.Column("title", sa.String(180), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("owner_sector", sa.String(50), nullable=False),
        sa.Column("priority", sa.String(10), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("human_id"),
    )
    for col in ["human_id","product_id","source_feedback_id","owner_sector","priority","status","created_at"]:
        op.create_index(f"ix_tasks_{col}", "tasks", [col], unique=False)
    op.create_table("repo_monitors",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("product_id", sa.String(36), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("local_path", sa.Text(), nullable=False),
        sa.Column("test_command", sa.Text(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("interval_seconds", sa.Integer(), nullable=False),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    for col in ["product_id","enabled","next_run_at"]:
        op.create_index(f"ix_repo_monitors_{col}", "repo_monitors", [col], unique=False)
    op.create_table("automation_runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("monitor_id", sa.String(36), sa.ForeignKey("repo_monitors.id", ondelete="SET NULL"), nullable=True),
        sa.Column("product_id", sa.String(36), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("run_type", sa.String(40), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("commit_sha", sa.String(80), nullable=True),
        sa.Column("command", sa.Text(), nullable=False),
        sa.Column("stdout", sa.Text(), nullable=True),
        sa.Column("stderr", sa.Text(), nullable=True),
        sa.Column("exit_code", sa.Integer(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
    )
    for col in ["monitor_id","product_id","run_type","status","started_at"]:
        op.create_index(f"ix_automation_runs_{col}", "automation_runs", [col], unique=False)
    op.create_table("worker_states",
        sa.Column("key", sa.String(50), primary_key=True),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("heartbeat_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("pid", sa.Integer(), nullable=True),
        sa.Column("version", sa.String(50), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
    )
    op.create_index("ix_worker_states_heartbeat_at", "worker_states", ["heartbeat_at"], unique=False)


def downgrade():
    op.drop_table("worker_states")
    op.drop_table("automation_runs")
    op.drop_table("repo_monitors")
    op.drop_table("tasks")
    op.drop_table("feedbacks")
    op.drop_table("sequence_counters")
