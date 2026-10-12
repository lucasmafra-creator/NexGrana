from sqlalchemy import select
from app.db import SessionLocal
from app.models import Feedback, Task, RepoMonitor, WorkerState
from app.liveops import triage_feedbacks, heartbeat


def h(name="Mafra"):
    return {"X-Dev-Actor": name}


def test_feedback_enters_live_queue(client):
    r = client.post("/api/v1/feedbacks", headers=h(), json={
        "product_slug":"nexgrana",
        "category":"bug",
        "title":"Saldo não atualiza",
        "description":"Ao registrar uma despesa, o saldo não atualiza na tela.",
        "expected":"Saldo recalculado",
        "observed":"Valor antigo permanece"
    })
    assert r.status_code == 201
    data = r.json()
    assert data["human_id"].startswith("SIM-")
    assert data["status"] == "new"


def test_worker_triages_feedback_and_creates_task(client):
    client.post("/api/v1/feedbacks", headers=h(), json={
        "product_slug":"nexgrana", "category":"bug", "title":"Crash no cadastro",
        "description":"Aplicativo travou ao salvar o cadastro"
    })
    with SessionLocal() as db:
        assert triage_feedbacks(db) == 1
        feedback = db.scalar(select(Feedback))
        task = db.scalar(select(Task))
        assert feedback.status == "triaged"
        assert feedback.priority in {"P1","P2"}
        assert task is not None
        assert task.source_feedback_id == feedback.id
        assert task.human_id.startswith("TASK-")


def test_security_feedback_is_p0(client):
    client.post("/api/v1/feedbacks", headers=h(), json={
        "product_slug":"nexgrana", "category":"security", "title":"Token exposto",
        "description":"Uma credencial apareceu em um log"
    })
    with SessionLocal() as db:
        triage_feedbacks(db)
        feedback = db.scalar(select(Feedback))
        assert feedback.severity == "S0"
        assert feedback.priority == "P0"
        task = db.scalar(select(Task))
        assert task.owner_sector == "security"


def test_worker_heartbeat_visible(client):
    with SessionLocal() as db:
        heartbeat(db, "running", "test heartbeat")
    r = client.get("/api/v1/live/status", headers=h())
    assert r.status_code == 200
    assert r.json()["worker_online"] is True


def test_self_monitor_seeded(client):
    r = client.get("/api/v1/automation/monitors", headers=h())
    assert r.status_code == 200
    assert any(x["name"] == "SIM Labs self-check" for x in r.json())


def test_ux_cannot_queue_monitor_run(client):
    monitor = client.get("/api/v1/automation/monitors", headers=h("Karol")).json()[0]
    r = client.post(f"/api/v1/automation/monitors/{monitor['id']}/run-now", headers=h("Karol"))
    assert r.status_code == 403
