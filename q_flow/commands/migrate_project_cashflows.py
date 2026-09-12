"""One-time legacy Project to Unit/Cashflow migration."""

from datetime import datetime, timezone
from pathlib import Path
from shutil import copy2

import click
from flask import current_app
from flask.cli import with_appcontext
from sqlalchemy import inspect, text

from q_flow.extensions import db, u_api
from q_flow.models.cashflow import Cashflow
from q_flow.services.units import create_unit_for_owner


def _database_path() -> Path:
    database = db.engine.url.database
    if not database:
        raise click.ClickException("Migration requires a file-backed SQLite database")
    return Path(database)


def _project_columns() -> set[str]:
    return {column["name"] for column in inspect(db.engine).get_columns("project")}


def _legacy_count(has_unit_id: bool) -> int:
    statement = (
        "SELECT COUNT(*) FROM project WHERE unit_id IS NULL"
        if has_unit_id else
        "SELECT COUNT(*) FROM project"
    )
    return int(db.session.execute(text(statement)).scalar() or 0)


def _add_unit_id_column() -> None:
    if "unit_id" not in _project_columns():
        db.session.execute(text("ALTER TABLE project ADD COLUMN unit_id VARCHAR(64)"))
        db.session.commit()


def _backup_database() -> Path:
    source = _database_path()
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
    destination = source.with_name(f"{source.name}.backup-{timestamp}")
    db.session.remove()
    db.engine.dispose()
    copy2(source, destination)
    return destination


def _verify_app_configuration() -> None:
    missing = [
        key for key in ("APP_ID", "APP_SECRET", "APP_ALGO")
        if not current_app.config.get(key)
    ]
    if missing:
        raise click.ClickException(
            f"Missing QAuth app configuration: {', '.join(missing)}")
    # Generate and validate the locally signed app token before any mutation.
    u_api._app_token()


@click.command("migrate-projects-to-cashflows")
@click.option(
    "--execute",
    is_flag=True,
    help="Create QAuth Units and convert legacy rows. Default is dry run.",
)
@with_appcontext
def migrate_projects_to_cashflows(execute: bool) -> None:
    """Convert each legacy local Project into a Unit plus Base Cashflow."""
    has_unit_id = "unit_id" in _project_columns()
    legacy_count = _legacy_count(has_unit_id)
    skipped = int(db.session.execute(text("SELECT COUNT(*) FROM project")).scalar() or 0) - legacy_count

    if not execute:
        click.echo(
            f"DRY RUN: legacy={legacy_count} skipped={skipped}; "
            "rerun with --execute to migrate")
        return

    _verify_app_configuration()
    backup = _backup_database()
    click.echo(f"Backup: {backup}")
    _add_unit_id_column()

    migrated = 0
    already_created = 0
    failed = 0
    legacy_rows = Cashflow.query.filter(Cashflow.unit_id.is_(None)).all()
    for cashflow in legacy_rows:
        original_name = cashflow.name or "Untitled Project"
        original_description = cashflow.description or ""
        project_was_deleted = cashflow.is_deleted
        try:
            _, existed = create_unit_for_owner(
                u_api,
                owner_user_id=cashflow.created_by,
                unit_id=cashflow.id,
                name=original_name,
                description=original_description,
                color=cashflow.color or "",
            )
            if project_was_deleted:
                response = u_api.post(
                    "unit/admin/deactivate",
                    data={"unit_id": cashflow.id},
                )
                if response.error:
                    raise RuntimeError(response.message)
            cashflow.unit_id = cashflow.id
            cashflow.name = "Base Cashflow"
            cashflow.description = ""
            # Deletion now belongs to the parent Unit. The financial scenario
            # itself must remain active so restoring that Unit reveals it.
            cashflow.is_deleted = False
            cashflow.updated_by = cashflow.created_by
            db.session.commit()
            migrated += 1
            already_created += int(existed)
            click.echo(f"Migrated {cashflow.id}: {original_name}")
        except Exception as error:
            db.session.rollback()
            failed += 1
            click.echo(f"FAILED {cashflow.id}: {original_name}: {error}", err=True)

    click.echo(
        f"Summary: migrated={migrated} already_created={already_created} "
        f"failed={failed} skipped={skipped}")
    if failed:
        raise click.ClickException(f"{failed} project migration(s) failed")
