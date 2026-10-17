"""Operational additions only; no financial database connection."""
from sqlalchemy import String, Text, Integer, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from .db import Base
from .models import now, uid

class EngineConfig(Base):
    __tablename__='engine_config'
    key: Mapped[str]=mapped_column(String(80),primary_key=True)
    paused: Mapped[bool]=mapped_column(Boolean,default=False)
    heartbeat_at: Mapped[object|None]=mapped_column(DateTime(timezone=True),nullable=True)

class EngineWorker(Base):
    __tablename__='engine_workers'
    key: Mapped[str]=mapped_column(String(80),primary_key=True)
    specialty: Mapped[str]=mapped_column(String(100))
    paused: Mapped[bool]=mapped_column(Boolean,default=False)
    status: Mapped[str]=mapped_column(String(30),default='idle')
    last_run_at: Mapped[object|None]=mapped_column(DateTime(timezone=True),nullable=True)
    last_error: Mapped[str]=mapped_column(String(200),default='')
    completed: Mapped[int]=mapped_column(Integer,default=0)

class EngineSchedule(Base):
    __tablename__='engine_schedules'
    key: Mapped[str]=mapped_column(String(80),primary_key=True)
    interval_seconds: Mapped[int]=mapped_column(Integer)
    enabled: Mapped[bool]=mapped_column(Boolean,default=True)
    next_run_at: Mapped[object]=mapped_column(DateTime(timezone=True),default=now)

class EngineJob(Base):
    __tablename__='engine_jobs'
    id: Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    product_id: Mapped[str]=mapped_column(ForeignKey('products.id'),index=True)
    worker_key: Mapped[str]=mapped_column(ForeignKey('engine_workers.key'),index=True)
    kind: Mapped[str]=mapped_column(String(60))
    dedup_key: Mapped[str]=mapped_column(String(200),unique=True)
    artifact_id: Mapped[str|None]=mapped_column(ForeignKey('artifacts.id'),nullable=True)
    status: Mapped[str]=mapped_column(String(30),default='queued',index=True)
    attempts: Mapped[int]=mapped_column(Integer,default=0)
    available_at: Mapped[object]=mapped_column(DateTime(timezone=True),default=now)
    lease_until: Mapped[object|None]=mapped_column(DateTime(timezone=True),nullable=True)
    started_at: Mapped[object|None]=mapped_column(DateTime(timezone=True),nullable=True)
    finished_at: Mapped[object|None]=mapped_column(DateTime(timezone=True),nullable=True)
    created_at: Mapped[object]=mapped_column(DateTime(timezone=True),default=now)
    duration_ms: Mapped[int]=mapped_column(Integer,default=0)
    error: Mapped[str]=mapped_column(String(200),default='')
    result_json: Mapped[str]=mapped_column(Text,default='{}')
    evidence_id: Mapped[str|None]=mapped_column(ForeignKey('evidence.id'),nullable=True)

class EngineIncident(Base):
    __tablename__='engine_incidents'
    id: Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    key: Mapped[str]=mapped_column(String(200),unique=True)
    severity: Mapped[str]=mapped_column(String(10),default='P2')
    status: Mapped[str]=mapped_column(String(30),default='open')
    detail: Mapped[str]=mapped_column(String(400))
    created_at: Mapped[object]=mapped_column(DateTime(timezone=True),default=now)

class LearningNote(Base):
    __tablename__='learning_notes'
    id: Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    product_id: Mapped[str]=mapped_column(ForeignKey('products.id'))
    source: Mapped[str]=mapped_column(String(200))
    concept: Mapped[str]=mapped_column(String(200))
    application: Mapped[str]=mapped_column(Text)
    evidence_id: Mapped[str|None]=mapped_column(ForeignKey('evidence.id'),nullable=True)
    created_at: Mapped[object]=mapped_column(DateTime(timezone=True),default=now)
