"""Additive operational schema. Financial NexGrana data is never stored here."""
from sqlalchemy import String, Text, Integer, ForeignKey, UniqueConstraint, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from .db import Base
from .models import uid, now

class ProjectConfig(Base):
    __tablename__ = 'project_configs'
    product_id: Mapped[str] = mapped_column(ForeignKey('products.id'), primary_key=True)
    description: Mapped[str] = mapped_column(Text, default='')
    platforms: Mapped[str] = mapped_column(Text, default='Windows,Android')
    repository: Mapped[str] = mapped_column(Text, default='')
    rules_json: Mapped[str] = mapped_column(Text, default='{}')

class Release(Base):
    __tablename__ = 'releases'
    __table_args__ = (UniqueConstraint('product_id', 'version', name='uq_release_version'),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    product_id: Mapped[str] = mapped_column(ForeignKey('products.id'), index=True)
    version: Mapped[str] = mapped_column(String(80))
    notes: Mapped[str] = mapped_column(Text, default='')
    status: Mapped[str] = mapped_column(String(30), default='candidate')
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), default=now)

class Artifact(Base):
    __tablename__ = 'artifacts'
    __table_args__ = (UniqueConstraint('release_id', 'sha256', name='uq_artifact_release_hash'),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    product_id: Mapped[str] = mapped_column(ForeignKey('products.id'), index=True)
    release_id: Mapped[str] = mapped_column(ForeignKey('releases.id'), index=True)
    filename: Mapped[str] = mapped_column(String(200))
    platform: Mapped[str] = mapped_column(String(40))
    path: Mapped[str] = mapped_column(Text)
    sha256: Mapped[str] = mapped_column(String(64))
    size_bytes: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(30), default='queued')
    report_json: Mapped[str] = mapped_column(Text, default='{}')
    manifest_json: Mapped[str] = mapped_column(Text, default='{}')
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), default=now)

class Receipt(Base):
    __tablename__ = 'integration_receipts'
    __table_args__ = (UniqueConstraint('product_id', 'source', 'external_id', name='uq_receipt_origin'),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    product_id: Mapped[str] = mapped_column(ForeignKey('products.id'), index=True)
    source: Mapped[str] = mapped_column(String(40), default='collector')
    external_id: Mapped[str] = mapped_column(String(150))
    feedback_id: Mapped[str] = mapped_column(ForeignKey('feedbacks.id'), index=True)
    release_version: Mapped[str] = mapped_column(String(80), default='')
    platform: Mapped[str] = mapped_column(String(40), default='Multiplataforma')
    screen: Mapped[str] = mapped_column(String(160), default='')
    content_hash: Mapped[str] = mapped_column(String(64))
    metadata_json: Mapped[str] = mapped_column(Text, default='{}')
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), default=now)

class Evidence(Base):
    __tablename__ = 'evidence'
    __table_args__ = (UniqueConstraint('feedback_id', 'sha256', name='uq_evidence_feedback_hash'),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    product_id: Mapped[str] = mapped_column(ForeignKey('products.id'), index=True)
    release_id: Mapped[str | None] = mapped_column(ForeignKey('releases.id'), nullable=True)
    feedback_id: Mapped[str | None] = mapped_column(ForeignKey('feedbacks.id'), nullable=True)
    filename: Mapped[str] = mapped_column(String(200))
    path: Mapped[str] = mapped_column(Text)
    sha256: Mapped[str] = mapped_column(String(64))
    size_bytes: Mapped[int] = mapped_column(Integer)
    kind: Mapped[str] = mapped_column(String(40), default='attachment')
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), default=now)

class TestRun(Base):
    __tablename__ = 'test_runs'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    product_id: Mapped[str] = mapped_column(ForeignKey('products.id'), index=True)
    release_id: Mapped[str] = mapped_column(ForeignKey('releases.id'), index=True)
    artifact_id: Mapped[str | None] = mapped_column(ForeignKey('artifacts.id'), nullable=True)
    kind: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(30))
    result_json: Mapped[str] = mapped_column(Text, default='{}')
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), default=now)

class RunnerReportReceipt(Base):
    __tablename__ = 'runner_report_receipts'
    release_id: Mapped[str] = mapped_column(ForeignKey('releases.id'), primary_key=True)
    report_sha256: Mapped[str] = mapped_column(String(64), primary_key=True)
    evidence_id: Mapped[str] = mapped_column(ForeignKey('evidence.id'))
    test_run_id: Mapped[str] = mapped_column(ForeignKey('test_runs.id'), unique=True)

class Decision(Base):
    __tablename__ = 'decisions'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    product_id: Mapped[str] = mapped_column(ForeignKey('products.id'), index=True)
    release_id: Mapped[str | None] = mapped_column(ForeignKey('releases.id'), nullable=True, unique=True)
    title: Mapped[str] = mapped_column(String(180))
    problem: Mapped[str] = mapped_column(Text)
    impact: Mapped[str] = mapped_column(Text)
    recommendation: Mapped[str] = mapped_column(Text)
    options_json: Mapped[str] = mapped_column(Text, default='["approve", "reject", "changes", "defer"]')
    status: Mapped[str] = mapped_column(String(30), default='pending')
    reason: Mapped[str] = mapped_column(Text, default='')
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[object] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)

class Message(Base):
    __tablename__ = 'messages'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    product_id: Mapped[str] = mapped_column(ForeignKey('products.id'), index=True)
    sender: Mapped[str] = mapped_column(String(80))
    kind: Mapped[str] = mapped_column(String(30), default='human')
    body: Mapped[str] = mapped_column(Text)
    task_id: Mapped[str | None] = mapped_column(ForeignKey('tasks.id'), nullable=True)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), default=now)

class RegressionCase(Base):
    __tablename__ = 'regression_cases'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    product_id: Mapped[str] = mapped_column(ForeignKey('products.id'), index=True)
    task_id: Mapped[str] = mapped_column(ForeignKey('tasks.id'), unique=True)
    title: Mapped[str] = mapped_column(String(180))
    steps: Mapped[str] = mapped_column(Text)
    expected: Mapped[str] = mapped_column(Text)
    evidence_id: Mapped[str] = mapped_column(ForeignKey('evidence.id'))
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), default=now)

class DailyReport(Base):
    __tablename__ = 'daily_reports'
    __table_args__ = (UniqueConstraint('product_id', 'day', name='uq_report_day'),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    product_id: Mapped[str] = mapped_column(ForeignKey('products.id'), index=True)
    day: Mapped[str] = mapped_column(String(10))
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), default=now)

class Job(Base):
    __tablename__ = 'jobs'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    product_id: Mapped[str] = mapped_column(ForeignKey('products.id'), index=True)
    artifact_id: Mapped[str] = mapped_column(ForeignKey('artifacts.id'), unique=True)
    status: Mapped[str] = mapped_column(String(30), default='queued', index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    lease_until: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error: Mapped[str] = mapped_column(Text, default='')
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), default=now)

class Lease(Base):
    __tablename__ = 'leases'
    key: Mapped[str] = mapped_column(String(80), primary_key=True)
    owner: Mapped[str] = mapped_column(String(80))
    expires_at: Mapped[object] = mapped_column(DateTime(timezone=True))
