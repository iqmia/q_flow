from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from q_flow import create_app
from q_flow.config import TestConfig
from q_flow.extensions import db
from q_flow.models.activity import Activity
from q_flow.models.cashflow import Cashflow


@pytest.fixture
def app(tmp_path):
    class MigrationTestConfig(TestConfig):
        STORAGE_PATH = str(tmp_path)

    return create_app(MigrationTestConfig)


@pytest.fixture
def runner(app):
    return app.test_cli_runner()


@pytest.fixture
def legacy_project(app):
    with app.app_context():
        item = Cashflow(
            id="legacy-project-1",
            name="Legacy Tower",
            description="Original project description",
            color="#123456",
            unit_id=None,
            created_by="owner-1",
            contract_value=1_000_000,
        ).commit()
        Activity(
            name="Concrete",
            cashflow_id=item.id,
            created_by="owner-1",
            cost=400_000,
        ).commit()
        return item.id


def test_migration_dry_run_does_not_change_data(app, runner, legacy_project):
    result = runner.invoke(args=["migrate-projects-to-cashflows"])

    assert result.exit_code == 0
    assert "DRY RUN" in result.output
    with app.app_context():
        assert db.session.get(Cashflow, legacy_project).unit_id is None


def test_migration_creates_unit_and_converts_row(app, runner, legacy_project):
    with patch(
        "q_flow.commands.migrate_project_cashflows.create_unit_for_owner",
        return_value=({"id": legacy_project}, False),
    ) as create:
        result = runner.invoke(
            args=["migrate-projects-to-cashflows", "--execute"])

    assert result.exit_code == 0, result.output
    assert "migrated=1" in result.output
    create.assert_called_once()
    assert create.call_args.kwargs["owner_user_id"] == "owner-1"
    assert create.call_args.kwargs["name"] == "Legacy Tower"
    with app.app_context():
        cashflow = db.session.get(Cashflow, legacy_project)
        assert cashflow.unit_id == legacy_project
        assert cashflow.name == "Base Cashflow"
        assert cashflow.contract_value == 1_000_000
        assert [activity.name for activity in cashflow.activities] == ["Concrete"]


def test_migration_is_idempotent(app, runner, legacy_project):
    with patch(
        "q_flow.commands.migrate_project_cashflows.create_unit_for_owner",
        return_value=({"id": legacy_project}, False),
    ) as create:
        first = runner.invoke(
            args=["migrate-projects-to-cashflows", "--execute"])
        second = runner.invoke(
            args=["migrate-projects-to-cashflows", "--execute"])

    assert first.exit_code == 0
    assert second.exit_code == 0
    assert "skipped=1" in second.output
    assert create.call_count == 1


def test_migration_creates_database_backup(app, runner, legacy_project):
    with patch(
        "q_flow.commands.migrate_project_cashflows.create_unit_for_owner",
        return_value=({"id": legacy_project}, False),
    ):
        result = runner.invoke(
            args=["migrate-projects-to-cashflows", "--execute"])

    assert result.exit_code == 0
    backups = list(Path(app.config["STORAGE_PATH"]).glob("q_flow.db.backup-*"))
    assert len(backups) == 1
    assert backups[0].stat().st_size > 0


def test_deleted_legacy_project_becomes_inactive_unit_with_active_cashflow(
        app, runner, legacy_project):
    with app.app_context():
        cashflow = db.session.get(Cashflow, legacy_project)
        cashflow.is_deleted = True
        db.session.commit()

    with patch(
        "q_flow.commands.migrate_project_cashflows.create_unit_for_owner",
        return_value=({"id": legacy_project}, False),
    ), patch(
        "q_flow.commands.migrate_project_cashflows.u_api.post",
        return_value=Mock(error=False),
    ) as deactivate:
        result = runner.invoke(
            args=["migrate-projects-to-cashflows", "--execute"])

    assert result.exit_code == 0, result.output
    deactivate.assert_called_once_with(
        "unit/admin/deactivate", data={"unit_id": legacy_project})
    with app.app_context():
        assert db.session.get(Cashflow, legacy_project).is_deleted is False


def test_migration_reports_failure_and_continues(app, runner, legacy_project):
    with app.app_context():
        Cashflow(
            id="legacy-project-2",
            name="Second Legacy Project",
            unit_id=None,
            created_by="owner-2",
        ).commit()

    def migrate_one(*_args, **kwargs):
        if kwargs["unit_id"] == legacy_project:
            raise RuntimeError("QAuth rejected the first project")
        return {"id": kwargs["unit_id"]}, False

    with patch(
        "q_flow.commands.migrate_project_cashflows.create_unit_for_owner",
        side_effect=migrate_one,
    ):
        result = runner.invoke(
            args=["migrate-projects-to-cashflows", "--execute"])

    assert result.exit_code != 0
    assert "failed=1" in result.output
    assert "migrated=1" in result.output
    with app.app_context():
        assert db.session.get(Cashflow, legacy_project).unit_id is None
        assert db.session.get(Cashflow, "legacy-project-2").unit_id == "legacy-project-2"
