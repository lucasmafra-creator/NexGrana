"""Vincula um UID real do Supabase a um membro canônico, após onboarding administrativo.
Uso: python scripts/link_identity.py "Mafra" "uuid-do-supabase"
Não cria usuário, não envia convite e não inventa identidade.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
from sqlalchemy import select
from app.db import SessionLocal
from app.models import TeamMember, UserIdentity

if len(sys.argv) != 3:
    raise SystemExit('Uso: python scripts/link_identity.py "Nome canônico" "external_uid"')
name, external_uid = sys.argv[1], sys.argv[2]
with SessionLocal() as db:
    member = db.scalar(select(TeamMember).where(TeamMember.canonical_name == name))
    if not member:
        raise SystemExit(f'Membro canônico não encontrado: {name}')
    if db.scalar(select(UserIdentity).where(UserIdentity.external_uid == external_uid)):
        raise SystemExit('Esse external_uid já está vinculado')
    db.add(UserIdentity(member_id=member.id, provider='supabase', external_uid=external_uid))
    db.commit()
print(f'UID vinculado a {name}.')
