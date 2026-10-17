from __future__ import annotations
import hmac
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from ..db import get_db
from ..auth import Principal, get_current_principal
from ..permissions import can_access_product, require_any
from ..models import Product, Feedback, Task, RepoMonitor, AutomationRun, WorkerState
from ..schemas import FeedbackCreate, FeedbackOut, TaskOut, MonitorOut, AutomationRunOut
from ..liveops import next_human_id
from ..audit import record_event
from ..config import settings

router = APIRouter()


def _product_for_slug(db: Session, principal: Principal, slug: str) -> Product:
    product = db.scalar(select(Product).where(Product.slug == slug))
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    if not can_access_product(principal, product.id):
        raise HTTPException(status_code=403, detail="Product access denied")
    return product


@router.get("/live/status")
def live_status(principal: Principal = Depends(get_current_principal), db: Session = Depends(get_db)):
    state = db.get(WorkerState, "main")
    now = datetime.now(timezone.utc)
    age = None
    online = False
    if state:
        hb = state.heartbeat_at
        if hb.tzinfo is None:
            hb = hb.replace(tzinfo=timezone.utc)
        age = max(0, int((now - hb).total_seconds()))
        online = state.status in {"running", "degraded"} and age <= 45
    product_ids = None if "executive" in principal.roles else principal.product_ids
    feedback_stmt = select(func.count(Feedback.id)).where(Feedback.status.in_(["new", "triaged"]))
    task_stmt = select(func.count(Task.id)).where(Task.status.in_(["open", "in_progress"]))
    failed_stmt = select(func.count(AutomationRun.id)).where(AutomationRun.status.in_(["failed", "timeout"]))
    if product_ids is not None:
        feedback_stmt = feedback_stmt.where(Feedback.product_id.in_(product_ids))
        task_stmt = task_stmt.where(Task.product_id.in_(product_ids))
        failed_stmt = failed_stmt.where(AutomationRun.product_id.in_(product_ids))
    last_stmt=select(AutomationRun).order_by(AutomationRun.started_at.desc()).limit(1)
    if product_ids is not None: last_stmt=last_stmt.where(AutomationRun.product_id.in_(product_ids))
    last_run = db.scalar(last_stmt)
    return {
        "worker_online": online,
        "worker_status": state.status if state else "not_started",
        "heartbeat_age_seconds": age,
        "worker_message": state.message if state else None,
        "open_feedbacks": db.scalar(feedback_stmt) or 0,
        "open_tasks": db.scalar(task_stmt) or 0,
        "failed_checks": db.scalar(failed_stmt) or 0,
        "last_check_status": last_run.status if last_run else None,
        "last_check_at": last_run.started_at if last_run else None,
    }


@router.post("/feedbacks", response_model=FeedbackOut, status_code=201)
def create_feedback(payload: FeedbackCreate, principal: Principal = Depends(get_current_principal), db: Session = Depends(get_db)):
    product = _product_for_slug(db, principal, payload.product_slug)
    row = Feedback(
        human_id=next_human_id(db, "SIM"),
        product_id=product.id,
        created_by_member_id=principal.member_id,
        category=payload.category,
        title=payload.title,
        description=payload.description,
        expected=payload.expected,
        observed=payload.observed,
        source="control-center",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    record_event(db, principal, "feedback.created", "feedback", row.id, product.id, f"{row.human_id} submitted")
    return row




@router.post("/ingest/feedback", response_model=FeedbackOut, status_code=201)
def ingest_feedback(payload: FeedbackCreate, x_sim_ingest_token: str | None = Header(default=None, alias="X-SIM-Ingest-Token"), db: Session = Depends(get_db)):
    if not settings.feedback_ingest_token:
        raise HTTPException(status_code=503, detail="Feedback ingest token is not configured")
    if not x_sim_ingest_token or not hmac.compare_digest(x_sim_ingest_token, settings.feedback_ingest_token):
        raise HTTPException(status_code=401, detail="Invalid ingest token")
    if payload.product_slug != settings.ingest_product_slug:
        raise HTTPException(status_code=403, detail="Integration token is limited to configured product")
    product = db.scalar(select(Product).where(Product.slug == payload.product_slug))
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    row = Feedback(
        human_id=next_human_id(db, "SIM"), product_id=product.id, created_by_member_id=None,
        category=payload.category, title=payload.title, description=payload.description,
        expected=payload.expected, observed=payload.observed, source="integration",
    )
    db.add(row); db.commit(); db.refresh(row)
    record_event(db, None, "feedback.ingested", "feedback", row.id, product.id, f"{row.human_id} received by integration")
    return row

@router.get("/feedbacks", response_model=list[FeedbackOut])
def list_feedbacks(principal: Principal = Depends(get_current_principal), db: Session = Depends(get_db), limit: int = 100):
    stmt = select(Feedback).order_by(Feedback.created_at.desc()).limit(max(1, min(limit, 200)))
    if "executive" not in principal.roles:
        stmt = stmt.where(Feedback.product_id.in_(principal.product_ids))
    return list(db.scalars(stmt))


@router.get("/tasks", response_model=list[TaskOut])
def list_tasks(principal: Principal = Depends(get_current_principal), db: Session = Depends(get_db), limit: int = 100):
    stmt = select(Task).order_by(Task.created_at.desc()).limit(max(1, min(limit, 200)))
    if "executive" not in principal.roles:
        stmt = stmt.where(Task.product_id.in_(principal.product_ids))
    return list(db.scalars(stmt))


@router.get("/automation/monitors", response_model=list[MonitorOut])
def monitors(principal: Principal = Depends(get_current_principal), db: Session = Depends(get_db)):
    stmt = select(RepoMonitor).order_by(RepoMonitor.name)
    if "executive" not in principal.roles:
        stmt = stmt.where(RepoMonitor.product_id.in_(principal.product_ids))
    return list(db.scalars(stmt))


@router.post("/automation/monitors/{monitor_id}/run-now")
def run_now(monitor_id: str, principal: Principal = Depends(get_current_principal), db: Session = Depends(get_db)):
    require_any(principal, {"executive", "operations", "qa", "engineering"})
    monitor = db.get(RepoMonitor, monitor_id)
    if not monitor:
        raise HTTPException(status_code=404, detail="Monitor not found")
    if not can_access_product(principal, monitor.product_id):
        raise HTTPException(status_code=403, detail="Product access denied")
    raise HTTPException(status_code=409, detail="Monitor de comandos desabilitado nesta versão. Importe o artefato para inspeção estática.")
    monitor.next_run_at = datetime.now(timezone.utc)
    db.commit()
    record_event(db, principal, "automation.run_requested", "repo_monitor", monitor.id, monitor.product_id, "Queued for background worker")
    return {"status": "queued", "monitor_id": monitor.id}


@router.get("/automation/runs", response_model=list[AutomationRunOut])
def runs(principal: Principal = Depends(get_current_principal), db: Session = Depends(get_db), limit: int = 30):
    stmt = select(AutomationRun).order_by(AutomationRun.started_at.desc()).limit(max(1, min(limit, 100)))
    if "executive" not in principal.roles:
        stmt = stmt.where(AutomationRun.product_id.in_(principal.product_ids))
    return list(db.scalars(stmt))
