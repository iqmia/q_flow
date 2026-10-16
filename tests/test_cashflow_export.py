from unittest.mock import Mock, patch

import pytest

from q_flow import create_app
from q_flow.config import TestConfig
from q_flow.extensions import db


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


def _permission():
    return Mock(return_value={"user_id": "owner-1", "unit_id": "unit-1"})


def _portable_payload():
    return {
        "format": "cashflowpot.cashflow",
        "version": 1,
        "cashflow": {
            "name": "Tender scenario",
            "description": "Portable source model",
            "contract_value": 1000,
            "advance": 0.1,
            "retention": 0.05,
            "release_retention_eop": 0.5,
            "dlp": 12,
            "duration_for_payment": 1,
            "interest_rate": 0.005,
            "wieb": 0.2,
            "use_independent_inflow_curve": True,
            "inflow_curve_type": "s_curve",
            "inflow_curve_skew": 0.2,
            "financing_facilities": [
                {
                    "id": "od-1",
                    "name": "Project overdraft",
                    "type": "Overdraft",
                    "draw_method": "automatic_shortfall",
                    "repayment_method": "cashflow_sweep",
                    "start": 0,
                    "end": 4,
                    "limit": 500,
                    "fees": 10,
                    "interest_rate": 0.01,
                    "revolving": True,
                    "sweep_priority": 0,
                }
            ],
            "activities": [
                {
                    "name": "Structure",
                    "activity_type": "Structure",
                    "activity_mode": "work",
                    "distribution_type": "manual",
                    "cost_schedule_json": [100, 150, 50],
                    "duration_units": "Periods",
                    "start": 1,
                    "advance": 0.1,
                    "retention": 0.05,
                    "release_retention_eop": 0.5,
                    "dlp": 6,
                    "duration_for_payment": 1,
                    "work_in_excess": 0.1,
                    "mobilization_period": 0,
                    "subcontracted": 0.4,
                    "skew": 0.0,
                    "no_billing_period": 0,
                },
                {
                    "name": "MEP purchase",
                    "activity_type": "MEP",
                    "activity_mode": "scheduled_cost",
                    "distribution_type": "manual",
                    "cost_schedule_json": [0, 250, 100],
                    "duration_units": "Periods",
                    "start": 2,
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
            ],
        },
    }


def _create_cashflow(app):
    with patch("q_flow.routes.cashflows.ensure_unit_permission", _permission()):
        response = app.test_client().post(
            "/project/unit-1/cashflows/import",
            headers=_auth(),
            json=_portable_payload(),
        )
    assert response.status_code == 201
    return response.get_json()["data"]


def _export(app, cashflow_id):
    with patch("q_flow.routes.cashflows.ensure_unit_permission", _permission()):
        return app.test_client().get(
            f"/cashflow/{cashflow_id}/export",
            headers=_auth(),
        )


def test_export_returns_only_versioned_portable_source_inputs(app):
    snapshot = _create_cashflow(app)
    response = _export(app, snapshot["id"])

    assert response.status_code == 200
    exported = response.get_json()
    assert exported["format"] == "cashflowpot.cashflow"
    assert exported["version"] == 1

    cashflow = exported["cashflow"]
    assert cashflow["name"] == "Tender scenario"
    assert cashflow["use_independent_inflow_curve"] is True
    assert cashflow["inflow_curve_type"] == "s_curve"
    assert cashflow["inflow_curve_skew"] == pytest.approx(0.2)
    assert cashflow["financing_facilities"][0]["id"] == "od-1"
    assert cashflow["financing_facilities"][0]["name"] == "Project overdraft"

    assert len(cashflow["activities"]) == 2
    manual = cashflow["activities"][0]
    scheduled = cashflow["activities"][1]
    assert manual["activity_mode"] == "work"
    assert manual["distribution_type"] == "manual"
    assert manual["cost_schedule_json"] == [100.0, 150.0, 50.0]
    assert manual["start"] == 1
    assert scheduled["activity_mode"] == "scheduled_cost"
    assert scheduled["cost_schedule_json"] == [0.0, 250.0, 100.0]
    assert scheduled["start"] == 2

    forbidden_cashflow_fields = {
        "id",
        "unit_id",
        "created_at",
        "created_by",
        "updated_at",
        "updated_by",
        "timestamp",
        "is_deleted",
        "workflow",
        "inflow",
        "outflow",
        "netflow",
        "facility_rows",
        "summary",
    }
    assert forbidden_cashflow_fields.isdisjoint(cashflow)

    for activity in cashflow["activities"]:
        assert {
            "id",
            "cashflow_id",
            "project_id",
            "created_at",
            "created_by",
            "updated_at",
            "updated_by",
            "timestamp",
            "is_deleted",
            "cash_flow_json",
        }.isdisjoint(activity)


def test_export_can_be_imported_into_another_project_without_calculated_state(app):
    source = _create_cashflow(app)
    export_response = _export(app, source["id"])
    assert export_response.status_code == 200

    with patch("q_flow.routes.cashflows.ensure_unit_permission", _permission()):
        imported_response = app.test_client().post(
            "/project/unit-2/cashflows/import",
            headers=_auth(),
            json=export_response.get_json(),
        )

    assert imported_response.status_code == 201
    imported = imported_response.get_json()["data"]
    assert imported["unit_id"] == "unit-2"
    assert imported["name"] == source["name"]
    assert imported["use_independent_inflow_curve"] is True
    assert imported["inflow_curve_skew"] == pytest.approx(0.2)
    assert imported["financing_facilities"][0]["id"] == "od-1"
    assert [row["activity_mode"] for row in imported["activities"]] == [
        "work",
        "scheduled_cost",
    ]
    assert imported["activities"][0]["cost_schedule_json"] == [100.0, 150.0, 50.0]
    assert imported["activities"][1]["cost_schedule_json"] == [0.0, 250.0, 100.0]
    assert imported["workflow"]
    assert imported["outflow"]


def test_export_requires_normal_cashflow_view_permission(app):
    snapshot = _create_cashflow(app)
    denied = Mock(
        return_value=(
            {"code": "unit_access_denied", "message": "denied"},
            403,
        )
    )

    with patch("q_flow.routes.cashflows.ensure_unit_permission", denied):
        response = app.test_client().get(
            f"/cashflow/{snapshot['id']}/export",
            headers=_auth(),
        )

    assert response.status_code == 403
