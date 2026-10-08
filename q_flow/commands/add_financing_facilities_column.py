"""Schema upgrade for storing financing facility definitions on cashflows."""

import click
from flask.cli import with_appcontext
from sqlalchemy import inspect, text

from q_flow.extensions import db


@click.command("add-financing-facilities-column")
@with_appcontext
def add_financing_facilities_column() -> None:
    """Add the nullable JSON facility-definition column if it is missing."""
    columns = {
        column["name"] for column in inspect(db.engine).get_columns("project")
    }
    if "financing_facilities" in columns:
        click.echo("Financing facilities column already exists")
        return

    db.session.execute(text(
        "ALTER TABLE project ADD COLUMN financing_facilities JSON"
    ))
    db.session.commit()
    click.echo("Added column: financing_facilities")
