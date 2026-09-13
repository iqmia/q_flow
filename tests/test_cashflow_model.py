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


def _linear_activity(Cashflow, Activity, *, deleted=False, stored=None):
    cashflow = Cashflow(
        name="Base Cashflow",
        unit_id="unit-1",
        created_by="user-1",
        contract_value=120,
        advance=0.1,
        retention=0.1,
        release_retention_eop=0.5,
        dlp=2,
        duration_for_payment=1,
        interest_rate=0.01,
        wieb=0.2,
    ).commit()
    activity = Activity(
        name="Concrete",
        cashflow_id=cashflow.id,
        created_by="user-1",
        activity_type="linear",
        cost=100,
        duration=2,
        start=0,
        mobilization_period=0,
        subcontracted=0,
        is_deleted=deleted,
        cash_flow_json=stored,
    ).commit()
    return cashflow, activity


def test_cashflow_snapshot_uses_corrected_payment_timing(app):
    from q_flow.cashflow import CashflowCalculator
    from q_flow.models.activity import Activity
    from q_flow.models.cashflow import Cashflow

    with app.app_context():
        cashflow, _ = _linear_activity(Cashflow, Activity)
        snapshot = CashflowCalculator(cashflow).snapshot()

        assert snapshot == {
            "workflow": [50.0, 50.0],
            "inflow": [12.0, 38.4, 48.0, 15.6, 0.0, 6.0],
            "outflow": [50.0, 50.0, 0.0, 0.0],
            "netflow": [-38.0, -11.6, 48.0, 15.6, 0.0, 6.0],
            "outflow_with_interest": [
                -38.38, -50.48, -2.5, 13.1, 13.1, 19.1,
            ],
            "duration": 2,
        }


def test_calculator_recomputes_and_rounds_stale_activity_cashflow(app):
    from q_flow.cashflow import CashflowCalculator
    from q_flow.models.activity import Activity
    from q_flow.models.cashflow import Cashflow

    with app.app_context():
        cashflow, activity = _linear_activity(
            Cashflow,
            Activity,
            stored={
                "marginal_work": [999.123456],
                "marginal_out_flow": [888.123456],
            },
        )
        calculator = CashflowCalculator(cashflow)

        assert calculator.activity_cashflows[activity.id] == {
            "marginal_work": [50.0, 50.0],
            "marginal_out_flow": [50.0, 50.0, 0.0, 0.0],
        }


def test_empty_cashflow_snapshot_uses_empty_arrays(app):
    from q_flow.cashflow import CashflowCalculator
    from q_flow.models.cashflow import Cashflow

    with app.app_context():
        cashflow = Cashflow(
            name="Empty",
            unit_id="unit-1",
            created_by="user-1",
        ).commit()

        assert CashflowCalculator(cashflow).snapshot() == {
            "workflow": [],
            "inflow": [],
            "outflow": [],
            "netflow": [],
            "outflow_with_interest": [],
            "duration": 0,
        }


def test_zero_advance_and_payment_delay_still_has_first_inflow_period(app):
    from q_flow.cashflow import CashflowCalculator
    from q_flow.models.activity import Activity
    from q_flow.models.cashflow import Cashflow

    with app.app_context():
        cashflow = Cashflow(
            name="Immediate",
            unit_id="unit-1",
            created_by="user-1",
            contract_value=100,
            advance=0,
            retention=0,
            release_retention_eop=0,
            dlp=0,
            duration_for_payment=0,
            interest_rate=0,
            wieb=0,
        ).commit()
        Activity(
            name="One period",
            cashflow_id=cashflow.id,
            created_by="user-1",
            activity_type="linear",
            cost=100,
            duration=1,
            mobilization_period=0,
            subcontracted=0,
        ).commit()

        snapshot = CashflowCalculator(cashflow).snapshot()
        assert snapshot["inflow"] == [100.0, 0.0]
        assert snapshot["netflow"] == [0.0, 0.0, 0.0]


def test_cashflow_serialization_recomputes_active_activities(app):
    from q_flow.models.activity import Activity
    from q_flow.models.cashflow import Cashflow

    with app.app_context():
        cashflow, active = _linear_activity(
            Cashflow,
            Activity,
            stored={"marginal_work": [999], "marginal_out_flow": [999]},
        )
        Activity(
            name="Deleted",
            cashflow_id=cashflow.id,
            created_by="user-1",
            cost=500,
            duration=2,
            is_deleted=True,
        ).commit()

        data = cashflow.as_dict_with_activities()

        assert [item["id"] for item in data["activities"]] == [active.id]
        assert data["activities"][0]["cash_flow_json"] == {
            "marginal_work": [50.0, 50.0],
            "marginal_out_flow": [50.0, 50.0, 0.0, 0.0],
        }
        assert data["workflow"] == [50.0, 50.0]
        assert data["duration"] == 2


def test_empty_cashflow_serialization_is_complete(app):
    from q_flow.models.cashflow import Cashflow

    with app.app_context():
        cashflow = Cashflow(
            name="Empty",
            unit_id="unit-1",
            created_by="user-1",
        ).commit()

        data = cashflow.as_dict_with_activities()
        assert data["activities"] == []
        assert data["workflow"] == []
        assert data["inflow"] == []
        assert data["outflow"] == []
        assert data["netflow"] == []
        assert data["outflow_with_interest"] == []
        assert data["duration"] == 0
