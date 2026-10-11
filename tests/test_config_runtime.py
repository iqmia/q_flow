import importlib
import os
import sys
from types import SimpleNamespace

import pytest

from q_flow import create_app
from q_flow.config import TestConfig
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

    assert module.Config.DATABASE_URL == database_url
    assert module.Config.STORAGE_PATH == "/srv/cashflowpot/storage"


def test_local_config_does_not_require_env_local(monkeypatch):
    module = _import_config(monkeypatch, {"SECRET_KEY": "production-secret"})

    assert module.LocalConfig.DEBUG is True
    assert module.LocalConfig.DATABASE_URL == ""


def test_test_config_always_selects_sqlite_fallback(monkeypatch):
    module = _import_config(
        monkeypatch,
        {"DATABASE_URL": "postgresql+psycopg://prod@localhost/prod"},
    )

    assert module.TestConfig.DATABASE_URL == ""


def test_app_uses_database_url_when_configured(tmp_path):
    database_url = "sqlite:///:memory:"

    class RuntimeConfig(TestConfig):
        STORAGE_PATH = str(tmp_path)
        DATABASE_URL = database_url

    app = create_app(RuntimeConfig)

    assert app.config["SQLALCHEMY_DATABASE_URI"] == database_url


def test_app_builds_sqlite_uri_from_final_storage_path(tmp_path):
    class RuntimeConfig(TestConfig):
        STORAGE_PATH = str(tmp_path)
        DATABASE_URL = ""

    app = create_app(RuntimeConfig)

    assert app.config["SQLALCHEMY_DATABASE_URI"] == (
        f"sqlite:///{os.path.join(str(tmp_path), 'q_flow.db')}"
    )


def test_subclass_storage_override_gets_its_own_sqlite_database(tmp_path, monkeypatch):
    module = _import_config(monkeypatch, {"SECRET_KEY": "production-secret"})

    class IsolatedTestConfig(module.TestConfig):
        STORAGE_PATH = str(tmp_path)

    app = create_app(IsolatedTestConfig)

    assert app.config["SQLALCHEMY_DATABASE_URI"] == (
        f"sqlite:///{os.path.join(str(tmp_path), 'q_flow.db')}"
    )


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
