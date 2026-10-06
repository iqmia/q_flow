import pytest

from q_flow import create_app
from q_flow.cashflow import CashflowCalculator, Work
from q_flow.config import TestConfig
from q_flow.models.activity import Activity
from q_flow.models.cashflow import Cashflow
from q_flow.routes.cashflows import _validate_cashflow


@pytest.fixture
def app(tmp_path):
    class IndependentInflowSelectionConfig(TestConfig):
        STORAGE_PATH = str(tmp_path)

    return create_app(IndependentInflowSelectionConfig)


def test_true_flag_and_non_null_curve_type_select_independent_even_with_null_skew(app):
    with app.app_context():
        cashflow = Cashflow(
            name="Independent selector",
            unit_id="unit-1",
            created_by="user-1",
            contract_value=400,
            advance=0,
            retention=0,
            release_retention_eop=0.5,
            dlp=0,
            duration_for_payment=0,
            interest_rate=0,
            wieb=0,
            use_independent_inflow_curve=True,
            inflow_curve_type="s_curve",
        ).commit()
        cashflow.inflow_curve_skew = None
        Activity(
            name="Execution duration",
            cashflow_id=cashflow.id,
            created_by="user-1",
            activity_type="linear",
            cost=100,
            duration=4,
            start=0,
            mobilization_period=0,
            subcontracted=0,
        ).commit()

        _validate_cashflow(cashflow)
        calculator = CashflowCalculator(cashflow)
        expected = Work(4, 0.0, 400, "s").marginal_work()

        assert calculator.contract_work() == pytest.approx(expected)
        assert sum(calculator.contract_work()) == pytest.approx(400.0)
