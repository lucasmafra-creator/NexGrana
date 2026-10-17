from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from ..db import get_db
from ..models import Product, Sector, TeamMember, AuditEvent
from ..schemas import ProductOut, ProductCreate, SectorOut, TeamMemberOut, AuditOut, MeOut
from ..auth import Principal, get_current_principal
from ..permissions import require_any, AUDIT_READ, TEAM_READ, PRODUCT_MANAGE
from ..audit import record_event

router = APIRouter()


@router.get("/health")
def health():
    import hashlib
    from pathlib import Path
    instance=hashlib.sha256(Path(__file__).resolve().parents[3].as_posix().lower().rstrip('/').encode()).hexdigest()[:16]
    return {"status": "ok", "service": "sim-labs-control-center-qa", "phase": "Engine 0.4.1-qa.2", "mode": "continuous-local-qa", "instance_id": instance}


@router.get("/me", response_model=MeOut)
def me(principal: Principal = Depends(get_current_principal)):
    return MeOut(member_id=principal.member_id, name=principal.name, canonical_role=principal.canonical_role, roles=sorted(principal.roles), product_slugs=sorted(principal.product_slugs), auth_mode=principal.auth_mode)


@router.get("/dashboard")
def dashboard(principal: Principal = Depends(get_current_principal), db: Session = Depends(get_db)):
    product_stmt = select(func.count(Product.id))
    if "executive" not in principal.roles:
        product_stmt = product_stmt.where(Product.id.in_(principal.product_ids))
    return {
        "phase": "SIM Labs QA 0.4.1-qa.2 — engine local",
        "actor": principal.name,
        "products_visible": db.scalar(product_stmt) or 0,
        "team_members": db.scalar(select(func.count(TeamMember.id)).where(TeamMember.active.is_(True))) or 0,
        "sectors": db.scalar(select(func.count(Sector.id))) or 0,
        "next_gate": "Conectar Supabase/Postgres e publicar em servidor para operação 24/7 independente do PC",
    }


@router.get("/products", response_model=list[ProductOut])
def products(principal: Principal = Depends(get_current_principal), db: Session = Depends(get_db)):
    stmt = select(Product).order_by(Product.created_at)
    if "executive" not in principal.roles:
        stmt = stmt.where(Product.id.in_(principal.product_ids))
    return list(db.scalars(stmt))


@router.post("/products", response_model=ProductOut, status_code=201)
def create_product(payload: ProductCreate, principal: Principal = Depends(get_current_principal), db: Session = Depends(get_db)):
    require_any(principal, PRODUCT_MANAGE)
    if db.scalar(select(Product).where(Product.slug == payload.slug)):
        raise HTTPException(status_code=409, detail="Product slug already exists")
    product = Product(slug=payload.slug, name=payload.name)
    db.add(product)
    db.commit()
    db.refresh(product)
    record_event(db, principal, "product.created", "product", product.id, product.id, "Created through Control Center API")
    return product


@router.get("/sectors", response_model=list[SectorOut])
def sectors(_: Principal = Depends(get_current_principal), db: Session = Depends(get_db)):
    return list(db.scalars(select(Sector).order_by(Sector.name)))


@router.get("/team", response_model=list[TeamMemberOut])
def team(principal: Principal = Depends(get_current_principal), db: Session = Depends(get_db)):
    require_any(principal, TEAM_READ)
    return list(db.scalars(select(TeamMember).order_by(TeamMember.canonical_name)))


@router.get("/audit-events", response_model=list[AuditOut])
def audit_events(principal: Principal = Depends(get_current_principal), db: Session = Depends(get_db), limit: int = 50):
    require_any(principal, AUDIT_READ)
    limit = max(1, min(limit, 200))
    stmt=select(AuditEvent).order_by(AuditEvent.created_at.desc()).limit(limit)
    if "executive" not in principal.roles:
        stmt=stmt.where(AuditEvent.product_id.in_(principal.product_ids))
    return list(db.scalars(stmt))
