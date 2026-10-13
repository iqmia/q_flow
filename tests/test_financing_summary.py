import pytest

from q_flow import create_app
from q_flow.config import TestConfig
from q_flow.models.activity import Activity
from q_flow.models.cashflow import Cashflow


@pytest.fixture
def app(tmp_path):
    class FinancingSummaryTestConfig(TestConfig):
        STORAGE_PATH = str(tmp_path)

    return create_app(FinancingSummaryTestConfig)


def test_summary_exposes_financing_decision_metrics(app):
    with app.app_context():
        cashflow = Cashflow(
            name="Financing KPI test",
            unit_id="unit-1",
            created_by="user-1",
            contract_value=0,
            advance=0,
            retention=0,
            release_retention_eop=0.5,
            dlp=0,
            duration_for_payment=0,
            interest_rate=0,
            wieb=0,
            financing_facilities=[{
                "name": "LC",
                "type": "Letter of Credit",
                "draw_method": "scheduled",
                "draw_schedule": {0: 60, 1: 60},
                "repayment_method": "scheduled",
                "repayment_schedule": {1: 20},
                "limit": 100,
                "interest_rate": 0.1,
                "fees": 5,
                "revolving": True,
            }],
        ).commit()
        Activity(
            name="Work",
            cashflow_id=cashflow.id,
            created_by="user-1",
            activity_type="linear",
            cost=100,
            duration=2,
            start=0,
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

        summary = cashflow.as_dict_with_activities()["summary"]

        assert summary["minimum_pre_financing_balance"] == -100.0
        assert summary["minimum_pre_financing_period"] == 1
        assert summary["peak_facility_outstanding"] == 80.0
        assert summary["final_facility_outstanding"] == 80.0
        assert summary["total_facility_fees"] == 5.0
        assert summary["total_facility_interest"] == 14.0
        assert summary["financing_cost"] == 19.0
        assert summary["final_cash_balance"] == -39.0
        assert summary["cash_after_debt_settlement"] == -119.0
        assert summary["work_duration"] == 2
        assert summary["financial_horizon"] == 3


def test_summary_without_facilities_has_zero_financing_metrics(app):
    with app.app_context():
        cashflow = Cashflow(
            name="No facilities",
            unit_id="unit-1",
            created_by="user-1",
            contract_value=100,
            advance=0,
            retention=0,
            release_retention_eop=0.5,
            dlp=0,
            duration_for_payment=0,
            interest_rate=0,
            wieb=0,
            financing_facilities=[],
        ).commit()
        Activity(
            name="Work",
            cashflow_id=cashflow.id,
            created_by="user-1",
            activity_type="linear",
            cost=100,
            duration=1,
            start=0,
            mobilization_period=0,
            subcontracted=0,
        ).commit()

        summary = cashflow.as_dict_with_activities()["summary"]

        assert summary["total_facility_interest"] == 0.0
        assert summary["total_facility_fees"] == 0.0
        assert summary["peak_facility_outstanding"] == 0.0
        assert summary["final_facility_outstanding"] == 0.0
        assert summary["cash_after_debt_settlement"] == summary["final_cash_balance"]
