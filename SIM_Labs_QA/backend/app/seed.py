from sqlalchemy import select
from pathlib import Path
import os
import shutil
from .db import SessionLocal, Base, engine
from .models import Product, Sector, TeamMember, Membership, RepoMonitor, WorkerState

CANONICAL_TEAM = [
    ("Mafra", "CEO / Fundador", "Estratégia, orçamento, decisão final de promoção de release após gates", "executive"),
    ("Vânio", "Diretor de Operações", "Coordenação operacional, prioridades de execução, incidentes e escalonamentos", "operations"),
    ("Karol", "UX & Feedback", "Pesquisa, triagem de experiência e validação de fluxo", "ux"),
    ("Niel", "Testes & QA", "Plano de testes, evidência, reteste e aceite técnico de QA", "qa"),
    ("Bárbara", "Análise & Produto", "Requisitos, métricas de produto e critérios de aceite", "product"),
    ("Fernanda", "Operations & Business", "Processos, custos e operação de negócio", "business"),
    ("Carlinha", "UX & Feedback", "Feedback, linguagem e validação de usabilidade", "ux"),
]

SECTORS = [
    ("executive", "Executive / Control Center", "Saúde agregada, prioridades, orçamento e bloqueios"),
    ("product", "Product", "Discovery, requisitos, roadmap e critérios"),
    ("engineering", "Engineering", "Bugs, tarefas, PRs, arquitetura e dependências"),
    ("qa", "Quality / QA", "Cenários, execuções, dispositivos e regressões"),
    ("security", "Cybersecurity", "Ativos, riscos, vulnerabilidades e incidentes"),
    ("ux", "UX / Experience", "Jornadas, acessibilidade e pesquisa"),
    ("marketing", "Marketing / Growth", "Campanhas, funil, ativação e retenção agregada"),
    ("operations", "Operations", "Serviços, jobs, capacidade e runbooks"),
    ("business", "Business", "Custos, contratos, parceiros e projeções empresariais"),
    ("sac", "SAC / Customer Success", "Atendimento, respostas e acompanhamento"),
    ("analytics", "Data / Analytics", "Taxonomia, qualidade e agregação de eventos"),
    ("red_team", "Red Team", "Contestação independente e testes autorizados"),
    ("release_manager", "Release Management", "Gates, tag, artefatos, rollout e rollback"),
    ("build", "Build & Release", "Pré-flight e artefatos nativos; geração depende do host e de ferramentas disponíveis"),
    ("performance", "Performance", "Baselines, latência, memória e desempenho em aparelhos autorizados"),
    ("offers", "Ofertas & Parcerias", "Fontes autorizadas, catálogo, links e revisão comercial"),
    ("chaos_test", "Chaos Test", "Planejamento de resiliência em QA; injeção de falhas ainda desativada"),
]


def seed(db):
    product = db.scalar(select(Product).where(Product.slug == "nexgrana"))
    if not product:
        product = Product(slug="nexgrana", name="NexGrana — Produto #001")
        db.add(product)
        db.flush()

    internal_product = db.scalar(select(Product).where(Product.slug == "sim-labs-control-center"))
    if not internal_product:
        internal_product = Product(slug="sim-labs-control-center", name="SIM Labs Control Center — Interno", status="internal")
        db.add(internal_product)
        db.flush()

    for slug, name, description in SECTORS:
        if not db.scalar(select(Sector).where(Sector.slug == slug)):
            db.add(Sector(slug=slug, name=name, description=description))

    for name, role_name, responsibility, role in CANONICAL_TEAM:
        member = db.scalar(select(TeamMember).where(TeamMember.canonical_name == name))
        if not member:
            member = TeamMember(canonical_name=name, canonical_role=role_name, responsibility=responsibility)
            db.add(member)
            db.flush()
        membership = db.scalar(select(Membership).where(Membership.member_id == member.id, Membership.product_id == product.id, Membership.role == role))
        if not membership:
            db.add(Membership(member_id=member.id, product_id=product.id, role=role, environment="all"))
        internal_membership = db.scalar(select(Membership).where(Membership.member_id == member.id, Membership.product_id == internal_product.id, Membership.role == role))
        if not internal_membership:
            db.add(Membership(member_id=member.id, product_id=internal_product.id, role=role, environment="all"))

    root = Path(__file__).resolve().parents[2]
    self_monitor = db.scalar(select(RepoMonitor).where(RepoMonitor.name == "SIM Labs self-check"))
    if not self_monitor:
        check_parts = []
        if (root / ".git").exists() and shutil.which("git"):
            check_parts.append("git diff --check")
        if (root / "backend" / "app").exists():
            check_parts.append("{python} -m compileall -q backend/app")
            check_parts.append("{python} -m pytest -q backend/tests")
        else:
            check_parts.append("{python} -m compileall -q app")
            check_parts.append("{python} -m pytest -q tests")
        if (root / "frontend" / "package.json").exists() and shutil.which("npm"):
            check_parts.append("npm run build --prefix frontend")
        db.add(RepoMonitor(
            product_id=internal_product.id,
            name="SIM Labs self-check",
            local_path=str(root),
            test_command=" && ".join(check_parts),
            enabled=False,
            interval_seconds=900,
        ))

    nex_path = os.getenv("NEXGRANA_REPO_PATH", "").strip()
    if nex_path and Path(nex_path).exists():
        nex_monitor = db.scalar(select(RepoMonitor).where(RepoMonitor.name == "NexGrana local checks"))
        if not nex_monitor:
            db.add(RepoMonitor(
                product_id=product.id,
                name="NexGrana local checks",
                local_path=nex_path,
                test_command=os.getenv("NEXGRANA_TEST_COMMAND", "{python} -m pytest -q"),
                enabled=False,
                interval_seconds=int(os.getenv("NEXGRANA_CHECK_INTERVAL", "900")),
            ))

    if db.get(WorkerState, "main") is None:
        db.add(WorkerState(key="main", status="not_started", message="Start app.worker to activate LiveOps"))
    for monitor in db.scalars(select(RepoMonitor)):
        monitor.enabled = False
    db.commit()


def main():
    # Apply Alembic migrations before running the seed.
    with SessionLocal() as db:
        seed(db)


if __name__ == "__main__":
    main()
