import importlib
import os
import sys

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def app_module(tmp_path, monkeypatch):
    database_file = tmp_path / "mathquest_test.db"

    monkeypatch.setenv(
        "DATABASE_URL",
        f"sqlite:///{database_file}",
    )

    # Tests must not inherit Render's production environment flag.
    # Otherwise the profile cookie is marked Secure.
    monkeypatch.delenv("RENDER", raising=False)

    sys.modules.pop("app.main", None)

    module = importlib.import_module("app.main")

    module.Base.metadata.create_all(
        bind=module.engine,
    )

    yield module

    module.engine.dispose()

    sys.modules.pop("app.main", None)


@pytest.fixture
def client(app_module):
    with TestClient(
        app_module.app,
        base_url="https://testserver",
    ) as test_client:
        yield test_client


def build_client(tmp_path):
    database_file = tmp_path / "mathquest_test.db"

    os.environ["DATABASE_URL"] = (
        f"sqlite:///{database_file}"
    )

    # Prevent production cookie behavior during local tests.
    os.environ.pop("RENDER", None)

    sys.modules.pop("app.main", None)

    module = importlib.import_module("app.main")

    module.Base.metadata.create_all(
        bind=module.engine,
    )

    return TestClient(
        module.app,
        base_url="https://testserver",
    )
