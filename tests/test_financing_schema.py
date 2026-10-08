from sqlalchemy import inspect, text

from q_flow import create_app
from q_flow.config import TestConfig
from q_flow.extensions import db


def _app(tmp_path):
    class FinancingSchemaConfig(TestConfig):
        STORAGE_PATH = str(tmp_path)

    return create_app(FinancingSchemaConfig)


def test_schema_upgrade_adds_nullable_facility_json_column_idempotently(tmp_path):
    app = _app(tmp_path)
    with app.app_context():
        db.drop_all()
        db.session.execute(text(
            "CREATE TABLE project (id VARCHAR(64) PRIMARY KEY, name VARCHAR(64))"
        ))
        db.session.execute(text(
            "INSERT INTO project (id, name) VALUES ('legacy-1', 'Legacy')"
        ))
        db.session.commit()

    runner = app.test_cli_runner()
    first = runner.invoke(args=["add-financing-facilities-column"])
    second = runner.invoke(args=["add-financing-facilities-column"])

    assert first.exit_code == 0, first.output
    assert second.exit_code == 0, second.output
    with app.app_context():
        columns = {
            column["name"]
            for column in inspect(db.engine).get_columns("project")
        }
        assert "financing_facilities" in columns
        legacy = db.session.execute(text(
            "SELECT financing_facilities FROM project WHERE id = 'legacy-1'"
        )).scalar_one()
        assert legacy is None
