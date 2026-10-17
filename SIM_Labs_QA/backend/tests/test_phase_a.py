from sqlalchemy import select
from app.db import SessionLocal
from app.models import Product, TeamMember, Membership


def h(name):
    return {"X-Dev-Actor": name}


def test_health_is_public(client):
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json()["phase"] == "Engine 0.4.1-qa.2"


def test_private_endpoint_requires_auth(client):
    assert client.get("/api/v1/dashboard").status_code == 401


def test_canonical_team_seeded(client):
    r = client.get("/api/v1/team", headers=h("Mafra"))
    assert r.status_code == 200
    names = {x["canonical_name"] for x in r.json()}
    assert names == {"Mafra", "Vânio", "Karol", "Niel", "Bárbara", "Fernanda", "Carlinha"}


def test_non_executive_cannot_read_audit(client):
    assert client.get("/api/v1/audit-events", headers=h("Karol")).status_code == 403


def test_non_manager_cannot_create_product(client):
    r = client.post("/api/v1/products", headers=h("Karol"), json={"slug":"produto-dois","name":"Produto #002"})
    assert r.status_code == 403


def test_executive_can_create_product_and_event_is_audited(client):
    r = client.post("/api/v1/products", headers=h("Mafra"), json={"slug":"produto-dois","name":"Produto #002"})
    assert r.status_code == 201
    audit = client.get("/api/v1/audit-events", headers=h("Mafra")).json()
    assert any(x["action"] == "product.created" for x in audit)


def test_product_scope_isolation(client):
    with SessionLocal() as db:
        p2 = Product(slug="private-two", name="Private Product")
        db.add(p2); db.commit(); db.refresh(p2)
        # Karol intentionally receives no membership for p2.
    visible = client.get("/api/v1/products", headers=h("Karol")).json()
    assert {p["slug"] for p in visible} == {"nexgrana", "sim-labs-control-center"}
    exec_visible = client.get("/api/v1/products", headers=h("Mafra")).json()
    assert {p["slug"] for p in exec_visible} == {"nexgrana", "sim-labs-control-center", "private-two"}
