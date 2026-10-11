import importlib
import os
import sys
from types import SimpleNamespace

import pytest

from q_flow.services import utils as utils_module
from q_flow.services.file_sys import FileSys


@pytest.fixture(autouse=True)
def _clear_config_module():
    sys.modules.pop("q_flow.config", None)
    yield
    sys.modules.pop("q_flow.config", None)


def _import_config(monkeypatch, env_data, local_data=None):
    def fake_get_env(file_path):
        file_path = str(file_path)
        if file_path.endswith("env_local.json"):
            if local_data is None:
                raise AssertionError("env_local.json should not be loaded when it does not exist")
            return local_data
        return env_data

    real_exists = os.path.exists

    def fake_exists(file_path):
        if str(file_path).endswith("env_local.json"):
            return local_data is not None
        return real_exists(file_path)

    monkeypatch.setattr(utils_module, "get_env", fake_get_env)
    monkeypatch.setattr(os.path, "exists", fake_exists)
    return importlib.import_module("q_flow.config")


def test_production_config_uses_database_url_and_storage_override(monkeypatch):
    database_url = "postgresql+psycopg://cashflowpot:secret@localhost/cashflowpot"
    module = _import_config(
        monkeypatch,
        {
            "DATABASE_URL": database_url,
            "STORAGE_PATH": "/srv/cashflowpot/storage",
        },
    )

    assert module.Config.SQLALCHEMY_DATABASE_URI == database_url
    assert module.Config.STORAGE_PATH == "/srv/cashflowpot/storage"


def test_local_config_does_not_require_env_local(monkeypatch):
    module = _import_config(monkeypatch, {"SECRET_KEY": "production-secret"})

    assert module.LocalConfig.DEBUG is True
    assert module.LocalConfig.SQLALCHEMY_DATABASE_URI.startswith("sqlite:///")


def test_test_config_always_uses_sqlite(monkeypatch):
    module = _import_config(
        monkeypatch,
        {"DATABASE_URL": "postgresql+psycopg://prod@localhost/prod"},
    )

    assert module.TestConfig.SQLALCHEMY_DATABASE_URI.startswith("sqlite:///")
    assert module.TestConfig.DATABASE_URL == ""


def test_file_sys_does_not_replace_configured_database_uri(tmp_path):
    database_url = "postgresql+psycopg://cashflowpot:secret@localhost/cashflowpot"
    app = SimpleNamespace(
        config={
            "STORAGE_PATH": str(tmp_path),
            "PROJECT_PHOTOS": "project_photos",
            "SQLALCHEMY_DATABASE_URI": database_url,
        }
    )

    FileSys().init_app(app)

    assert app.config["SQLALCHEMY_DATABASE_URI"] == database_url
