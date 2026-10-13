"""Schema-only upgrade for Activity mode and manual schedule settings."""

import click
from flask.cli import with_appcontext
from sqlalchemy import inspect, text

from q_flow.extensions import db


_COLUMNS = (
    ("activity_mode", "VARCHAR(32)"),
    ("distribution_type", "VARCHAR(32)"),
    ("cost_schedule_json", "JSON"),
)


def _activity_columns() -> set[str]:
    return {column["name"] for column in inspect(db.engine).get_columns("activity")}


@click.command("add-activity-mode-columns")
@with_appcontext
def add_activity_mode_columns() -> None:
    """Add nullable Activity mode columns without backfilling legacy rows."""
    existing = _activity_columns()
    added = []

    for name, sql_type in _COLUMNS:
        if name in existing:
            continue
        db.session.execute(text(
            f"ALTER TABLE activity ADD COLUMN {name} {sql_type}"
        ))
        added.append(name)

    if added:
        db.session.commit()
        click.echo(f"Added columns: {', '.join(added)}")
    else:
        click.echo("Activity mode columns already exist")
