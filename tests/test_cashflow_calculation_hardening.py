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


def _profile_cashflow(app, *, duration=4, start=0, **overrides):
    values = {
        "name": "Curve profile",
        "unit_id": "unit-1",
        "created_by": "user-1",
        "contract_value": 400,
        "advance": 0,
        "retention": 0,
        "release_retention_eop": 0.5,
        "dlp": 0,
        "duration_for_payment": 0,
        "interest_rate": 0,
        "wieb": 0,
        "use_independent_inflow_curve": True,
        "inflow_curve_type": "s_curve",
        "inflow_curve_skew": 0.0,
    }
    values.update(overrides)
    cashflow = Cashflow(**values).commit()
    Activity(
        name="Execution profile",
        cashflow_id=cashflow.id,
        created_by="user-1",
        activity_type="linear",
        cost=200,
        duration=duration,
        start=start,
        advance=0,
        retention=0,
        release_retention_eop=0.5,
        dlp=0,
        duration_for_payment=0,
        work_in_excess=0,
        mobilization_period=0,
        no_billing_period=0,
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


def test_null_curve_type_falls_back_to_activity_linked_contract_work(app):
    with app.app_context():
        cashflow = _profile_cashflow(
            app,
            duration=2,
            start=2,
            use_independent_inflow_curve=True,
            inflow_curve_type=None,
        )
        calculator = CashflowCalculator(cashflow)

        assert calculator.contract_work() == pytest.approx(calculator.factored_work())
        assert calculator.contract_work() == pytest.approx([0.0, 0.0, 200.0, 200.0])


def test_false_independent_flag_falls_back_to_activity_linked_contract_work(app):
    with app.app_context():
        cashflow = _profile_cashflow(
            app,
            duration=2,
            start=2,
            use_independent_inflow_curve=False,
            inflow_curve_type="linear",
        )
        calculator = CashflowCalculator(cashflow)

        assert calculator.contract_work() == pytest.approx(calculator.factored_work())
        assert calculator.contract_work() == pytest.approx([0.0, 0.0, 200.0, 200.0])


def test_independent_linear_curve_uses_derived_execution_duration(app):
    with app.app_context():
        cashflow = _profile_cashflow(
            app,
            duration=2,
            start=2,
            inflow_curve_type="linear",
            contract_value=400,
        )
        calculator = CashflowCalculator(cashflow)

        contract_work = calculator.contract_work()

        assert calculator.duration == 4
        assert contract_work == pytest.approx([100.0, 100.0, 100.0, 100.0])
        assert sum(contract_work) == pytest.approx(400.0)


def test_independent_s_curve_skew_changes_timing_but_not_total_value(app):
    with app.app_context():
        back = _profile_cashflow(app, duration=6, inflow_curve_skew=-0.5)
        balanced = _profile_cashflow(app, duration=6, inflow_curve_skew=0.0)
        front = _profile_cashflow(app, duration=6, inflow_curve_skew=0.5)

        back_work = CashflowCalculator(back).contract_work()
        balanced_work = CashflowCalculator(balanced).contract_work()
        front_work = CashflowCalculator(front).contract_work()

        assert front_work[0] > balanced_work[0] > back_work[0]
        assert sum(back_work) == pytest.approx(back.contract_value)
        assert sum(balanced_work) == pytest.approx(balanced.contract_value)
        assert sum(front_work) == pytest.approx(front.contract_value)


def test_switching_inflow_method_does_not_change_outflow(app):
    with app.app_context():
        cashflow = _profile_cashflow(app, duration=4, subcontracted=0)
        independent_outflow = CashflowCalculator(cashflow).outflow()

        cashflow.use_independent_inflow_curve = False
        linked_outflow = CashflowCalculator(cashflow).outflow()

        assert linked_outflow == pytest.approx(independent_outflow)


def test_independent_curve_still_applies_client_wieb(app):
    with app.app_context():
        cashflow = _profile_cashflow(
            app,
            duration=2,
            inflow_curve_type="linear",
            contract_value=200,
            wieb=0.2,
        )

        inflow = CashflowCalculator(cashflow).inflow()

        assert inflow == pytest.approx([80.0, 100.0, 20.0])
        assert sum(inflow) == pytest.approx(200.0)


def test_serialized_cashflow_exposes_canonical_scenario_summary(app):
    with app.app_context():
        cashflow = Cashflow(
            name="Summary test",
            unit_id="unit-1",
            created_by="user-1",
            contract_value=50,
            advance=0,
            retention=0,
            release_retention_eop=0.5,
            dlp=0,
            duration_for_payment=0,
            interest_rate=0.1,
            wieb=0,
        ).commit()
        Activity(
            name="Split activity",
            cashflow_id=cashflow.id,
            created_by="user-1",
            activity_type="linear",
            cost=100,
            duration=1,
            start=0,
            advance=0,
            retention=0,
            release_retention_eop=0.5,
            dlp=0,
            duration_for_payment=0,
            work_in_excess=0,
            mobilization_period=0,
            no_billing_period=0,
            subcontracted=0.5,
        ).commit()

        summary = cashflow.as_dict_with_activities()["summary"]

        assert summary == {
            "total_inflow": 50.0,
            "subcontracted_cost": 50.0,
            "self_performed_cost": 50.0,
            "direct_cost": 100.0,
            "financing_cost": 10.5,
            "total_cost": 110.5,
            "final_cash_balance": -60.5,
            "work_duration": 1,
            "dlp": 0,
            "financial_horizon": 2,
        }


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
