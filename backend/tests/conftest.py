import os
import sys
import tempfile
from pathlib import Path

# Must be set BEFORE the app package is imported (config reads env at import time).
_tmp = tempfile.mkdtemp()
os.environ["WELLBEING_DB"] = str(Path(_tmp) / "test.db")
os.environ["ADMIN_TOKEN"] = "test-admin-token"
os.environ["SCREEN_MODEL_PATH"] = str(Path(_tmp) / "no_such_model.joblib")
os.environ.pop("TRANSFORMER_MODEL_DIR", None)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def auth(client):
    import uuid
    name = "u" + uuid.uuid4().hex[:10]
    r = client.post("/auth/register", json={"username": name, "password": "correct-horse", "consent": True,
                                            "age_group": "18-24", "gender": "female", "residence": "urban"})
    assert r.status_code == 200, r.text
    return {"Authorization": "Bearer " + r.json()["token"]}


ZERO = {c: 0.0 for c in ["social_media", "entertainment", "gaming", "productivity", "education", "other"]}
