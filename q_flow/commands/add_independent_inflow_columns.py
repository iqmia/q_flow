"""Schema-only upgrade for independent inflow curve settings."""

import click
from flask.cli import with_appcontext
from sqlalchemy import inspect, text

from q_flow.extensions import db


_COLUMNS = (
    ("use_independent_inflow_curve", "BOOLEAN"),
    ("inflow_curve_type", "VARCHAR(16)"),
    ("inflow_curve_skew", "FLOAT"),
)


def _project_columns() -> set[str]:
    return {column["name"] for column in inspect(db.engine).get_columns("project")}


@click.command("add-independent-inflow-columns")
@with_appcontext
def add_independent_inflow_columns() -> None:
    """Add nullable independent-inflow columns without backfilling rows."""
    existing = _project_columns()
    added = []

    for name, sql_type in _COLUMNS:
        if name in existing:
            continue
        db.session.execute(text(
            f"ALTER TABLE project ADD COLUMN {name} {sql_type}"
        ))
        added.append(name)

    if added:
        db.session.commit()
        click.echo(f"Added columns: {', '.join(added)}")
    else:
        click.echo("Independent inflow columns already exist")
