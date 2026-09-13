from types import SimpleNamespace

import pytest

from q_flow import create_app
from q_flow.cashflow import Activity_cf, CashflowCalculator
from q_flow.config import TestConfig
from q_flow.exceptions import InvalidData
from q_flow.models.activity import Activity
from q_flow.models.cashflow import Cashflow
from q_flow.routes.activities import _validate_activity
from q_flow.routes.cashflows import _validate_cashflow


@pytest.fixture
def app(tmp_path):
    class CashflowHardeningTestConfig(TestConfig):
        STORAGE_PATH = str(tmp_path)

    return create_app(CashflowHardeningTestConfig)


def _one_period_cashflow(app, **overrides):
    cashflow_values = {
        "name": "Timing test",
        "unit_id": "unit-1",
        "created_by": "user-1",
        "contract_value": 100,
        "advance": 0,
        "retention": 0,
        "release_retention_eop": 0.5,
        "dlp": 0,
        "duration_for_payment": 0,
        "interest_rate": 0,
        "wieb": 0,
    }
    cashflow_values.update(overrides)
    cashflow = Cashflow(**cashflow_values).commit()
    Activity(
        name="One period",
        cashflow_id=cashflow.id,
        created_by="user-1",
        activity_type="linear",
        cost=100,
        duration=1,
        start=0,
        mobilization_period=0,
        subcontracted=0,
    ).commit()
    return cashflow


def test_project_wieb_defers_first_period_work(app):
    with app.app_context():
        cashflow = _one_period_cashflow(app, wieb=0.2)

        inflow = CashflowCalculator(cashflow).inflow()

        assert inflow[:2] == pytest.approx([80.0, 20.0])


def test_project_payment_delay_is_independent_of_advance(app):
    with app.app_context():
        cashflow = _one_period_cashflow(app, duration_for_payment=1)

        inflow = CashflowCalculator(cashflow).inflow()

        assert inflow[:2] == pytest.approx([0.0, 100.0])


def test_project_zero_dlp_releases_all_retention_in_same_end_period(app):
    with app.app_context():
        cashflow = _one_period_cashflow(
            app,
            retention=0.1,
            release_retention_eop=0.5,
            dlp=0,
        )

        inflow = CashflowCalculator(cashflow).inflow()

        assert inflow == pytest.approx([90.0, 10.0])


def _subcontract_activity(dlp):
    return SimpleNamespace(
        activity_type="linear",
        duration=1,
        skew=0,
        cost=100,
        mobilization_period=0,
        no_billing_period=0,
        subcontracted=1,
        work_in_excess=0,
        retention=0.1,
        advance=0,
        duration_for_payment=0,
        release_retention_eop=0.5,
        dlp=dlp,
        start=0,
    )


def test_activity_dlp_one_releases_remaining_retention_one_period_later():
    payments = Activity_cf(_subcontract_activity(dlp=1)).sub_payments()

    assert payments == pytest.approx([90.0, 5.0, 5.0])


def test_activity_dlp_two_releases_remaining_retention_two_periods_later():
    payments = Activity_cf(_subcontract_activity(dlp=2)).sub_payments()

    assert payments == pytest.approx([90.0, 5.0, 0.0, 5.0])


def test_cashflow_rejects_advance_plus_retention_above_contract_value():
    cashflow = SimpleNamespace(
        contract_value=100,
        advance=0.6,
        retention=0.5,
        release_retention_eop=0.5,
        wieb=0.2,
        interest_rate=0.01,
        dlp=0,
        duration_for_payment=1,
    )

    with pytest.raises(InvalidData):
        _validate_cashflow(cashflow)


def test_activity_rejects_advance_plus_retention_above_subcontract_value():
    activity = SimpleNamespace(
        cost=100,
        duration=1,
        skew=0,
        start=0,
        dlp=0,
        duration_for_payment=1,
        mobilization_period=0,
        no_billing_period=0,
        advance=0.6,
        retention=0.5,
        release_retention_eop=0.5,
        work_in_excess=0.2,
        mobilization=0,
        profit=0,
        subcontracted=1,
    )

    with pytest.raises(InvalidData):
        _validate_activity(activity)
