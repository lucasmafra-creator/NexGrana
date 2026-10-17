import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import os
os.environ["APP_ENV"] = "test"
os.environ["SIM_AI_PROVIDER"] = "none"
os.environ["ALLOW_DEV_ACTORS"] = "1"
os.environ["STORAGE_DIR"] = str(Path(__file__).resolve().parent / "temporary_evidence")
os.environ["SESSION_SIGNING_KEY"] = "TEST_DATA_SESSION_KEY_64_chars_abcdefghijklmnopqrstuvwxyz0123456789"
os.environ["LOCAL_ADMIN_PASSWORD_HASH"] = ""
os.environ["FEEDBACK_INGEST_TOKEN"] = "TEST_DATA_INGEST"
TEST_DB = Path(__file__).resolve().parents[1] / "test_sim_labs.db"
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB.as_posix()}"
os.environ["AUTO_INIT_DB"] = "1"

import pytest
from fastapi.testclient import TestClient
from app.db import Base, engine, SessionLocal
from app.seed import seed
from app.main import app

@pytest.fixture(autouse=True)
def reset_db():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        seed(db)
    yield
    import shutil
    shutil.rmtree(os.environ["STORAGE_DIR"], ignore_errors=True)

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c
