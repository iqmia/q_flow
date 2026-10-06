from sqlalchemy import inspect, text

from q_flow import create_app
from q_flow.config import TestConfig
from q_flow.extensions import db
from q_flow.models.cashflow import Cashflow


def _app(tmp_path):
    class IndependentInflowSchemaConfig(TestConfig):
        STORAGE_PATH = str(tmp_path)

    return create_app(IndependentInflowSchemaConfig)


def test_new_cashflow_defaults_to_independent_s_curve(tmp_path):
    app = _app(tmp_path)
    with app.app_context():
        cashflow = Cashflow(
            name="Default curve",
            unit_id="unit-1",
            created_by="user-1",
            contract_value=100,
        ).commit()

        assert cashflow.use_independent_inflow_curve is True
        assert cashflow.inflow_curve_type == "s_curve"
        assert cashflow.inflow_curve_skew == 0.0


def test_schema_upgrade_adds_nullable_columns_without_backfill(tmp_path):
    app = _app(tmp_path)
    with app.app_context():
        db.drop_all()
        db.session.execute(text(
            "CREATE TABLE project ("
            "id VARCHAR(64) PRIMARY KEY, "
            "name VARCHAR(64)"
            ")"
        ))
        db.session.execute(text(
            "INSERT INTO project (id, name) VALUES ('legacy-1', 'Legacy')"
        ))
        db.session.commit()

    runner = app.test_cli_runner()
    first = runner.invoke(args=["add-independent-inflow-columns"])
    second = runner.invoke(args=["add-independent-inflow-columns"])

    assert first.exit_code == 0, first.output
    assert second.exit_code == 0, second.output

    with app.app_context():
        columns = {column["name"] for column in inspect(db.engine).get_columns("project")}
        assert {
            "use_independent_inflow_curve",
            "inflow_curve_type",
            "inflow_curve_skew",
        }.issubset(columns)

        row = db.session.execute(text(
            "SELECT use_independent_inflow_curve, inflow_curve_type, inflow_curve_skew "
            "FROM project WHERE id = 'legacy-1'"
        )).one()
        assert tuple(row) == (None, None, None)
