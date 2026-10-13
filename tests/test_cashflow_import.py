from unittest.mock import Mock, patch

import pytest

from q_flow import create_app
from q_flow.config import TestConfig
from q_flow.extensions import db
from q_flow.models.activity import Activity
from q_flow.models.cashflow import Cashflow


@pytest.fixture
def app(tmp_path):
    class RouteConfig(TestConfig):
        STORAGE_PATH = str(tmp_path)

    app = create_app(RouteConfig)
    user = {
        "user_id": "owner-1",
        "name": "Owner",
        "is_active": True,
        "token": "user-token",
    }
    with patch("q_flow.services.decorators.u_api.verify_token", return_value=user):
        yield app
    with app.app_context():
        db.session.remove()
        db.drop_all()


def _auth():
    return {"Authorization": "Bearer user-token"}


def _payload():
    return {
        "format": "cashflowpot.cashflow",
        "version": 1,
        "cashflow": {
            "name": "Imported tender",
            "description": "Portable scenario",
            "contract_value": 1250000,
            "advance": 0.1,
            "retention": 0.1,
            "release_retention_eop": 0.5,
            "dlp": 12,
            "duration_for_payment": 1,
            "interest_rate": 0.005,
            "wieb": 0.2,
            "activities": [
                {
                    "name": "Concrete",
                    "activity_type": "General",
                    "cost": 500000,
                    "duration": 4,
                    "duration_units": "Periods",
                    "start": 0,
                    "advance": 0.1,
                    "retention": 0.1,
                    "release_retention_eop": 0.5,
                    "dlp": 6,
                    "duration_for_payment": 1,
                    "work_in_excess": 0.1,
                    "mobilization_period": 0,
                    "subcontracted": 0.5,
                    "skew": 0.0,
                    "no_billing_period": 0,
                }
            ],
        },
    }


def _permission():
    return Mock(return_value={"user_id": "owner-1", "unit_id": "unit-1"})


def _import(app, payload):
    with patch("q_flow.routes.cashflows.ensure_unit_permission", _permission()):
        return app.test_client().post(
            "/project/unit-1/cashflows/import",
            headers=_auth(),
            json=payload,
        )


def test_import_cashflow_creates_complete_scenario_atomically(app):
    result = _import(app, _payload())

    assert result.status_code == 201
    snapshot = result.get_json()["data"]
    assert snapshot["unit_id"] == "unit-1"
    assert snapshot["name"] == "Imported tender"
    assert snapshot["use_independent_inflow_curve"] is True
    assert snapshot["inflow_curve_type"] == "s_curve"
    assert snapshot["inflow_curve_skew"] == 0.0
    assert len(snapshot["activities"]) == 1
    assert snapshot["activities"][0]["name"] == "Concrete"
    assert snapshot["activities"][0]["cashflow_id"] == snapshot["id"]
    assert snapshot["activities"][0]["activity_mode"] == "work"
    assert snapshot["activities"][0]["distribution_type"] == "s_curve"
    assert snapshot["workflow"]
    assert snapshot["outflow"]

    with app.app_context():
        assert Cashflow.query.filter_by(unit_id="unit-1").count() == 1
        assert Activity.query.count() == 1


def test_import_cashflow_preserves_independent_inflow_settings(app):
    payload = _payload()
    payload["cashflow"].update({
        "use_independent_inflow_curve": False,
        "inflow_curve_type": "linear",
        "inflow_curve_skew": 0.35,
    })

    result = _import(app, payload)

    assert result.status_code == 201
    snapshot = result.get_json()["data"]
    assert snapshot["use_independent_inflow_curve"] is False
    assert snapshot["inflow_curve_type"] == "linear"
    assert snapshot["inflow_curve_skew"] == pytest.approx(0.35)


def test_import_cashflow_preserves_facility_terms_and_calculated_rows(app):
    payload = _payload()
    payload["cashflow"]["financing_facilities"] = [{
        "id": "od-1",
        "name": "Project overdraft",
        "type": "Overdraft",
        "draw_method": "automatic_shortfall",
        "repayment_method": "cashflow_sweep",
        "start": 0,
        "end": 4,
        "limit": 100000,
        "fees": 250,
        "interest_rate": 0.01,
        "revolving": True,
        "sweep_priority": 0,
    }]

    result = _import(app, payload)

    assert result.status_code == 201
    snapshot = result.get_json()["data"]
    assert snapshot["financing_facilities"] == payload["cashflow"]["financing_facilities"]
    assert snapshot["facility_rows"][0]["id"] == "od-1"
    assert snapshot["facility_fees"]


def test_import_cashflow_accepts_manual_work_schedule_without_cost_or_duration(app):
    payload = _payload()
    payload["cashflow"]["activities"] = [{
        "name": "Manual MEP work",
        "activity_type": "mep",
        "activity_mode": "work",
        "distribution_type": "manual",
        "cost_schedule_json": [200, 0, 500, 300],
        "start": 1,
        "advance": 0,
        "retention": 0,
        "release_retention_eop": 0,
        "dlp": 0,
        "duration_for_payment": 0,
        "work_in_excess": 0,
        "mobilization_period": 0,
        "subcontracted": 0,
        "skew": 0,
        "no_billing_period": 0,
    }]

    result = _import(app, payload)

    assert result.status_code == 201
    activity = result.get_json()["data"]["activities"][0]
    assert activity["activity_mode"] == "work"
    assert activity["distribution_type"] == "manual"
    assert activity["cost_schedule_json"] == [200.0, 0.0, 500.0, 300.0]
    assert activity["cost"] == 1000.0
    assert activity["duration"] == 4


def test_import_cashflow_accepts_scheduled_cost_and_keeps_it_out_of_work(app):
    payload = _payload()
    payload["cashflow"]["use_independent_inflow_curve"] = False
    payload["cashflow"]["activities"] = [
        {
            "name": "Work",
            "activity_type": "General",
            "activity_mode": "work",
            "distribution_type": "linear",
            "cost": 800,
            "duration": 2,
            "start": 0,
            "advance": 0,
            "retention": 0,
            "release_retention_eop": 0,
            "dlp": 0,
            "duration_for_payment": 0,
            "work_in_excess": 0,
            "mobilization_period": 0,
            "subcontracted": 0,
            "skew": 0,
            "no_billing_period": 0,
        },
        {
            "name": "Purchase",
            "activity_type": "mep",
            "activity_mode": "scheduled_cost",
            "distribution_type": "manual",
            "cost_schedule_json": [0, 200],
            "start": 0,
        },
    ]

    result = _import(app, payload)

    assert result.status_code == 201
    snapshot = result.get_json()["data"]
    purchase = snapshot["activities"][1]
    assert purchase["cost"] == 200.0
    assert purchase["duration"] == 2
    assert purchase["cash_flow_json"]["marginal_work"] == [0.0, 0.0]
    assert purchase["cash_flow_json"]["marginal_out_flow"] == [0.0, 200.0]
    assert snapshot["summary"]["direct_cost"] == 1000.0
    assert snapshot["duration"] == 2


def test_import_old_version_one_linear_activity_keeps_legacy_linear_distribution(app):
    payload = _payload()
    activity = payload["cashflow"]["activities"][0]
    activity["activity_type"] = "linear"
    activity["cost"] = 100
    activity["duration"] = 2
    activity["subcontracted"] = 0
    payload["cashflow"]["contract_value"] = 100
    payload["cashflow"]["use_independent_inflow_curve"] = False

    result = _import(app, payload)

    assert result.status_code == 201
    imported = result.get_json()["data"]["activities"][0]
    assert imported["activity_mode"] == "work"
    assert imported["distribution_type"] == "linear"
    assert imported["cash_flow_json"]["marginal_work"] == [50.0, 50.0]


def test_import_cashflow_rejects_invalid_activity_without_partial_rows(app):
    payload = _payload()
    payload["cashflow"]["activities"][0]["cost"] = 0

    result = _import(app, payload)

    assert result.status_code == 400
    with app.app_context():
        assert Cashflow.query.count() == 0
        assert Activity.query.count() == 0


def test_import_cashflow_rejects_unknown_format_version(app):
    payload = _payload()
    payload["version"] = 2

    result = _import(app, payload)

    assert result.status_code == 400
    with app.app_context():
        assert Cashflow.query.count() == 0
        assert Activity.query.count() == 0


def test_import_cashflow_rejects_non_text_name_without_partial_rows(app):
    payload = _payload()
    payload["cashflow"]["name"] = 123

    result = _import(app, payload)

    assert result.status_code == 400
    with app.app_context():
        assert Cashflow.query.count() == 0
        assert Activity.query.count() == 0
