from __future__ import annotations
from datetime import datetime, timedelta, timezone
from pathlib import Path
import os
import subprocess
import sys
import time
from sqlalchemy import select
from sqlalchemy.orm import Session
from .models import SequenceCounter, Feedback, Task, RepoMonitor, AutomationRun, WorkerState, AuditEvent


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def next_human_id(db: Session, prefix: str) -> str:
    from sqlalchemy import update
    from sqlalchemy.dialects.sqlite import insert as sqlite_insert
    from sqlalchemy.dialects.postgresql import insert as pg_insert
    name = prefix.lower()
    dialect=db.get_bind().dialect.name
    insert=sqlite_insert if dialect=="sqlite" else pg_insert
    db.execute(insert(SequenceCounter).values(name=name,value=0).on_conflict_do_nothing(index_elements=["name"]))
    value=db.scalar(update(SequenceCounter).where(SequenceCounter.name==name).values(value=SequenceCounter.value+1).returning(SequenceCounter.value))
    return f"{prefix.upper()}-{value:04d}"


def classify_feedback(feedback: Feedback) -> tuple[str, str, str]:
    text = f"{feedback.title} {feedback.description} {feedback.observed or ''}".lower()
    if feedback.category in {"security", "privacy"} or any(k in text for k in ["vazamento", "senha", "token", "credencial", "exposto", "dados de outro"]):
        return "S0", "P0", "security"
    if any(k in text for k in ["perda de dados", "saldo errado", "cobrança errada", "não abre", "crash", "travou", "indisponível"]):
        return "S1", "P1", "qa"
    if feedback.category in {"bug", "error", "performance"}:
        return "S2", "P2", "qa"
    if feedback.category == "ux":
        return "S3", "P2", "ux"
    return "S3", "P3", "product"


def triage_feedbacks(db: Session) -> int:
    rows = list(db.scalars(select(Feedback).where(Feedback.status == "new").order_by(Feedback.created_at).limit(100)))
    processed = 0
    for feedback in rows:
        severity, priority, owner = classify_feedback(feedback)
        feedback.severity = severity
        priority = min(priority, feedback.priority or "P3")
        feedback.priority = priority
        feedback.status = "triaged"
        db.add(AuditEvent(
            actor_member_id=None, actor_type="service", action="feedback.triaged",
            object_type="feedback", object_id=feedback.id, product_id=feedback.product_id,
            reason=f"Rule-based initial triage: {severity}/{priority} -> {owner}",
        ))
        existing = db.scalar(select(Task).where(Task.source_feedback_id == feedback.id))
        if not existing:
            task = Task(
                human_id=next_human_id(db, "TASK"),
                product_id=feedback.product_id,
                source_feedback_id=feedback.id,
                title=f"Revisar {feedback.human_id}: {feedback.title}",
                description=feedback.description,
                owner_sector=owner,
                priority=priority,
                status="open",
            )
            db.add(task)
            db.flush()
            db.add(AuditEvent(
                actor_member_id=None, actor_type="service", action="task.auto_created",
                object_type="task", object_id=task.id, product_id=feedback.product_id,
                reason=f"Created from {feedback.human_id}; owner_sector={owner}",
            ))
        processed += 1
    if processed:
        db.commit()
    return processed


def _git_sha(path: str) -> str | None:
    try:
        p = subprocess.run(["git", "rev-parse", "HEAD"], cwd=path, capture_output=True, text=True, timeout=15)
        return p.stdout.strip() if p.returncode == 0 else None
    except Exception:
        return None


def run_monitor(db: Session, monitor: RepoMonitor):
    raise RuntimeError("Monitor de comandos desabilitado. Use inspeção estática ou runner isolado.")


def due_monitor_ids(db: Session) -> list[str]:
    now = utcnow()
    ids: list[str] = []
    monitors = list(db.scalars(select(RepoMonitor).where(RepoMonitor.enabled.is_(True))))
    for monitor in monitors:
        due = monitor.next_run_at is None
        if monitor.next_run_at is not None:
            nr = monitor.next_run_at
            if nr.tzinfo is None:
                nr = nr.replace(tzinfo=timezone.utc)
            due = nr <= now
        if due:
            ids.append(monitor.id)
    return ids


def run_monitor_by_id(monitor_id: str):
    from .db import SessionLocal
    with SessionLocal() as db:
        monitor = db.get(RepoMonitor, monitor_id)
        if monitor and monitor.enabled:
            return run_monitor(db, monitor)
    return None


def run_due_monitors(db: Session) -> int:
    count = 0
    for monitor_id in due_monitor_ids(db):
        run_monitor_by_id(monitor_id)
        count += 1
    return count


def heartbeat(db: Session, status: str = "running", message: str | None = None) -> None:
    state = db.get(WorkerState, "main")
    if state is None:
        state = WorkerState(key="main")
        db.add(state)
    state.status = status
    state.heartbeat_at = utcnow()
    state.pid = os.getpid()
    state.version = "0.4.1-qa.2-engine"
    state.message = message
    db.commit()
