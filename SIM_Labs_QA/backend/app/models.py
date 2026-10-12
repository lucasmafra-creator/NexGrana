from __future__ import annotations
from datetime import datetime, timezone
import uuid
from sqlalchemy import String, DateTime, Boolean, ForeignKey, Text, UniqueConstraint, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .db import Base


def uid() -> str:
    return str(uuid.uuid4())


def now() -> datetime:
    return datetime.now(timezone.utc)


class Product(Base):
    __tablename__ = "products"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(160))
    status: Mapped[str] = mapped_column(String(30), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Sector(Base):
    __tablename__ = "sectors"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(160))
    description: Mapped[str] = mapped_column(Text)


class TeamMember(Base):
    __tablename__ = "team_members"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    canonical_name: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    canonical_role: Mapped[str] = mapped_column(String(160))
    responsibility: Mapped[str] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    identities: Mapped[list[UserIdentity]] = relationship(back_populates="member", cascade="all, delete-orphan")


class UserIdentity(Base):
    __tablename__ = "user_identities"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    member_id: Mapped[str] = mapped_column(ForeignKey("team_members.id", ondelete="CASCADE"), index=True)
    provider: Mapped[str] = mapped_column(String(40), default="supabase")
    external_uid: Mapped[str] = mapped_column(String(180), unique=True, index=True)
    member: Mapped[TeamMember] = relationship(back_populates="identities")


class Membership(Base):
    __tablename__ = "memberships"
    __table_args__ = (UniqueConstraint("member_id", "product_id", "role", "environment", name="uq_membership_scope"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    member_id: Mapped[str] = mapped_column(ForeignKey("team_members.id", ondelete="CASCADE"), index=True)
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(50), index=True)
    environment: Mapped[str] = mapped_column(String(20), default="all")
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class AuditEvent(Base):
    __tablename__ = "audit_events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    actor_member_id: Mapped[str | None] = mapped_column(ForeignKey("team_members.id"), nullable=True, index=True)
    actor_type: Mapped[str] = mapped_column(String(30), default="human")
    action: Mapped[str] = mapped_column(String(120), index=True)
    object_type: Mapped[str] = mapped_column(String(80), index=True)
    object_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    product_id: Mapped[str | None] = mapped_column(ForeignKey("products.id"), nullable=True, index=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    correlation_id: Mapped[str] = mapped_column(String(80), default=uid, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, index=True)


class SequenceCounter(Base):
    __tablename__ = "sequence_counters"
    name: Mapped[str] = mapped_column(String(50), primary_key=True)
    value: Mapped[int] = mapped_column(Integer, default=0)


class Feedback(Base):
    __tablename__ = "feedbacks"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    human_id: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), index=True)
    created_by_member_id: Mapped[str | None] = mapped_column(ForeignKey("team_members.id"), nullable=True, index=True)
    category: Mapped[str] = mapped_column(String(40), default="suggestion", index=True)
    title: Mapped[str] = mapped_column(String(180))
    description: Mapped[str] = mapped_column(Text)
    expected: Mapped[str | None] = mapped_column(Text, nullable=True)
    observed: Mapped[str | None] = mapped_column(Text, nullable=True)
    severity: Mapped[str] = mapped_column(String(10), default="S3", index=True)
    priority: Mapped[str] = mapped_column(String(10), default="P3", index=True)
    status: Mapped[str] = mapped_column(String(30), default="new", index=True)
    source: Mapped[str] = mapped_column(String(40), default="control-center")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


class Task(Base):
    __tablename__ = "tasks"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    human_id: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), index=True)
    source_feedback_id: Mapped[str | None] = mapped_column(ForeignKey("feedbacks.id", ondelete="SET NULL"), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(180))
    description: Mapped[str] = mapped_column(Text)
    owner_sector: Mapped[str] = mapped_column(String(50), default="product", index=True)
    priority: Mapped[str] = mapped_column(String(10), default="P3", index=True)
    status: Mapped[str] = mapped_column(String(30), default="open", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


class RepoMonitor(Base):
    __tablename__ = "repo_monitors"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(160))
    local_path: Mapped[str] = mapped_column(Text)
    test_command: Mapped[str] = mapped_column(Text)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    interval_seconds: Mapped[int] = mapped_column(Integer, default=900)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class AutomationRun(Base):
    __tablename__ = "automation_runs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    monitor_id: Mapped[str | None] = mapped_column(ForeignKey("repo_monitors.id", ondelete="SET NULL"), nullable=True, index=True)
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), index=True)
    run_type: Mapped[str] = mapped_column(String(40), default="code-check", index=True)
    status: Mapped[str] = mapped_column(String(30), default="running", index=True)
    commit_sha: Mapped[str | None] = mapped_column(String(80), nullable=True)
    command: Mapped[str] = mapped_column(Text)
    stdout: Mapped[str | None] = mapped_column(Text, nullable=True)
    stderr: Mapped[str | None] = mapped_column(Text, nullable=True)
    exit_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, index=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class WorkerState(Base):
    __tablename__ = "worker_states"
    key: Mapped[str] = mapped_column(String(50), primary_key=True, default="main")
    status: Mapped[str] = mapped_column(String(30), default="starting")
    heartbeat_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, index=True)
    pid: Mapped[int | None] = mapped_column(Integer, nullable=True)
    version: Mapped[str] = mapped_column(String(50), default="0.4.1-qa.2-engine")
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
