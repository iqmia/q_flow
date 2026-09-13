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
                    "duration_units": "Months",
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


def test_import_cashflow_creates_complete_scenario_atomically(app):
    permission = Mock(return_value={"user_id": "owner-1", "unit_id": "unit-1"})

    with patch("q_flow.routes.cashflows.ensure_unit_permission", permission):
        result = app.test_client().post(
            "/project/unit-1/cashflows/import",
            headers=_auth(),
            json=_payload(),
        )

    assert result.status_code == 201
    snapshot = result.get_json()["data"]
    assert snapshot["unit_id"] == "unit-1"
    assert snapshot["name"] == "Imported tender"
    assert len(snapshot["activities"]) == 1
    assert snapshot["activities"][0]["name"] == "Concrete"
    assert snapshot["activities"][0]["cashflow_id"] == snapshot["id"]
    assert snapshot["workflow"]
    assert snapshot["outflow"]

    with app.app_context():
        assert Cashflow.query.filter_by(unit_id="unit-1").count() == 1
        assert Activity.query.count() == 1


def test_import_cashflow_rejects_invalid_activity_without_partial_rows(app):
    payload = _payload()
    payload["cashflow"]["activities"][0]["cost"] = 0
    permission = Mock(return_value={"user_id": "owner-1", "unit_id": "unit-1"})

    with patch("q_flow.routes.cashflows.ensure_unit_permission", permission):
        result = app.test_client().post(
            "/project/unit-1/cashflows/import",
            headers=_auth(),
            json=payload,
        )

    assert result.status_code == 400
    with app.app_context():
        assert Cashflow.query.count() == 0
        assert Activity.query.count() == 0


def test_import_cashflow_rejects_unknown_format_version(app):
    payload = _payload()
    payload["version"] = 2
    permission = Mock(return_value={"user_id": "owner-1", "unit_id": "unit-1"})

    with patch("q_flow.routes.cashflows.ensure_unit_permission", permission):
        result = app.test_client().post(
            "/project/unit-1/cashflows/import",
            headers=_auth(),
            json=payload,
        )

    assert result.status_code == 400
    with app.app_context():
        assert Cashflow.query.count() == 0
        assert Activity.query.count() == 0
