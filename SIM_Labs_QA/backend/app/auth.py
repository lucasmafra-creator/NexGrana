from dataclasses import dataclass
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session
import jwt
from .config import settings
from .db import get_db
from .models import TeamMember, UserIdentity, Membership, Product


@dataclass
class Principal:
    member_id: str
    name: str
    canonical_role: str
    roles: set[str]
    product_ids: set[str]
    product_slugs: set[str]
    auth_mode: str


def _principal_for_member(db: Session, member: TeamMember, auth_mode: str) -> Principal:
    rows = db.execute(
        select(Membership, Product)
        .join(Product, Product.id == Membership.product_id)
        .where(Membership.member_id == member.id, Membership.active.is_(True))
    ).all()
    return Principal(
        member_id=member.id,
        name=member.canonical_name,
        canonical_role=member.canonical_role,
        roles={m.role for m, _ in rows},
        product_ids={p.id for _, p in rows},
        product_slugs={p.slug for _, p in rows},
        auth_mode=auth_mode,
    )


def get_current_principal(
    authorization: str | None = Header(default=None),
    x_dev_actor: str | None = Header(default=None, alias="X-Dev-Actor"),
    db: Session = Depends(get_db),
) -> Principal:
    if settings.is_dev and settings.allow_dev_actors and x_dev_actor:
        member = db.scalar(select(TeamMember).where(TeamMember.canonical_name == x_dev_actor, TeamMember.active.is_(True)))
        if not member:
            raise HTTPException(status_code=401, detail="Unknown dev actor")
        return _principal_for_member(db, member, "dev-simulated")

    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    token = authorization.split(" ", 1)[1]
    if settings.is_dev and settings.session_signing_key:
        try:
            payload = jwt.decode(token, settings.session_signing_key, algorithms=["HS256"], audience="sim-labs", issuer="sim-labs-local", options={"require": ["exp", "sub", "iss", "aud"]})
            if payload["sub"] != "local-mafra":
                raise jwt.InvalidTokenError()
            member=db.scalar(select(TeamMember).where(TeamMember.canonical_name=="Mafra", TeamMember.active.is_(True)))
            if not member:
                raise HTTPException(403, "CEO local não cadastrado")
            return _principal_for_member(db, member, "local-private")
        except jwt.PyJWTError:
            pass
    if not settings.supabase_jwt_secret:
        raise HTTPException(status_code=503, detail="Supabase JWT verification is not configured")

    token = authorization.split(" ", 1)[1]
    try:
        payload = jwt.decode(token, settings.supabase_jwt_secret, algorithms=["HS256"], options={"require": ["sub", "exp"]})
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid token") from exc

    identity = db.scalar(select(UserIdentity).where(UserIdentity.external_uid == payload["sub"]))
    if not identity:
        raise HTTPException(status_code=403, detail="Identity is not onboarded")
    member = db.get(TeamMember, identity.member_id)
    if not member or not member.active:
        raise HTTPException(status_code=403, detail="Member is inactive")
    return _principal_for_member(db, member, "supabase-jwt")
