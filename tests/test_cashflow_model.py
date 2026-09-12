import pytest

from q_flow import create_app
from q_flow.config import TestConfig


@pytest.fixture
def app(tmp_path):
    class CashflowTestConfig(TestConfig):
        STORAGE_PATH = str(tmp_path)

    return create_app(CashflowTestConfig)


def test_cashflow_uses_legacy_table_and_activity_column(app):
    from q_flow.models.activity import Activity
    from q_flow.models.cashflow import Cashflow

    with app.app_context():
        cashflow = Cashflow(
            name="Tender",
            unit_id="unit-1",
            created_by="user-1",
            contract_value=1_000_000,
        ).commit()
        activity = Activity(
            name="Concrete",
            cashflow_id=cashflow.id,
            created_by="user-1",
        ).commit()

        assert Cashflow.__tablename__ == "project"
        assert activity.cashflow_id == cashflow.id
        assert activity.as_dict()["cashflow_id"] == cashflow.id
        assert "project_id" not in activity.as_dict()


def test_cashflow_calculation_matches_legacy_project_calculation(app):
    from q_flow.cashflow import CashflowCalculator, Project_cf
    from q_flow.models.activity import Activity
    from q_flow.models.cashflow import Cashflow

    with app.app_context():
        cashflow = Cashflow(
            name="Base Cashflow",
            unit_id="unit-1",
            created_by="user-1",
            contract_value=100_000,
        ).commit()
        Activity(
            name="Concrete",
            cashflow_id=cashflow.id,
            created_by="user-1",
            cost=80_000,
            duration=4,
        ).commit()

        assert CashflowCalculator(cashflow).inflow() == Project_cf(cashflow).inflow()
        assert CashflowCalculator(cashflow).outflow() == Project_cf(cashflow).outflow()
