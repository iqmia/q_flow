"""Compact results retain authoritative KPIs without serializing detailed inputs."""
import json
from unittest.mock import Mock, patch

import pytest

from q_flow.models.activity import Activity
from q_flow.models.cashflow import Cashflow
from tests.test_cashflow_facility_routes import app, _auth, _base_facility, _cashflow_payload, _create, _request


@pytest.mark.parametrize("financed", [False, True])
def test_summary_matches_full_kpis_and_preserves_material_properties(app, financed):
    facilities = [_base_facility()] if financed else []
    created = _create(app, facilities)
    full = _request(app, "GET", f"/cashflow/{created['id']}").get_json()["data"]
    with patch.object(Activity, "as_dict", side_effect=AssertionError("summary serialized activity details")):
        response = _request(app, "GET", f"/cashflow/{created['id']}?detail=summary")
    assert response.status_code == 200
    data = response.get_json()["data"]
    assert set(data) == {"id", "unit_id", "name", "summary", "properties"}
    assert data["summary"] == full["summary"]
    assert data["properties"]["contract"]["contract_value"] == full["contract_value"]
    assert data["properties"]["forecast"]["wieb"] == full["wieb"]
    assert data["properties"]["activity_counts"] == {"total": 1, "work": 1, "scheduled_cost": 0}
    assert "activities" not in data["properties"]
    assert data["properties"]["units"]["periods_per_year"] is None
    assert data["properties"]["units"]["interest_rate_basis"] == "per_model_period"
    assert "peak_unfunded_shortfall" in data["summary"]


def test_summary_removes_schedules_and_substantially_reduces_response_size(app):
    facility = _base_facility()
    facility.update(draw_method="scheduled", draw_schedule={str(p): 1 for p in range(100)},
                    repayment_method="scheduled", repayment_schedule={"101": 100}, end=101)
    created = _create(app, [facility])
    full = _request(app, "GET", f"/cashflow/{created['id']}?detail=full").get_json()["data"]
    compact = _request(app, "GET", f"/cashflow/{created['id']}?detail=summary").get_json()["data"]
    terms = compact["properties"]["financing"][0]
    assert terms["limit"] == 100
    assert terms["interest_rate"] == 0
    assert terms["fees"] == 0
    assert "draw_schedule" not in terms
    assert "repayment_schedule" not in terms
    assert len(json.dumps(compact)) < len(json.dumps(full)) / 2


def test_summary_counts_scheduled_costs_and_excludes_deleted_activities(app):
    payload = _cashflow_payload()
    scheduled = {**payload["cashflow"]["activities"][0], "name": "Equipment payment",
                 "activity_mode": "scheduled_cost", "distribution_type": "manual",
                 "cost_schedule_json": [0, 30]}
    payload["cashflow"]["activities"].append(scheduled)
    response = _request(app, "POST", "/project/unit-1/cashflows/import", payload)
    assert response.status_code == 201, response.get_json()
    created = response.get_json()["data"]
    path = f"/cashflow/{created['id']}?detail=summary"
    data = _request(app, "GET", path).get_json()["data"]
    assert data["properties"]["activity_counts"] == {"total": 2, "work": 1, "scheduled_cost": 1}
    with app.app_context():
        activity = Activity.query.filter_by(cashflow_id=created["id"], name="Equipment payment").one()
        activity.is_deleted = True
        activity.commit()
    data = _request(app, "GET", path).get_json()["data"]
    assert data["properties"]["activity_counts"] == {"total": 1, "work": 1, "scheduled_cost": 0}


def test_empty_summary_has_zero_counts_and_no_remaining_shortfall(app):
    with app.app_context():
        Cashflow(id="empty", name="Empty", unit_id="unit-1", created_by="owner-1").commit()
    data = _request(app, "GET", "/cashflow/empty?detail=summary").get_json()["data"]
    assert data["properties"]["activity_counts"] == {"total": 0, "work": 0, "scheduled_cost": 0}
    assert data["summary"]["peak_unfunded_shortfall"] == 0


def test_unfinanced_remaining_shortfall_includes_legacy_interest(app):
    created = _create(app)
    _request(app, "PUT", f"/cashflow/{created['id']}", {"contract_value": 0, "interest_rate": 0.1})
    full = _request(app, "GET", f"/cashflow/{created['id']}").get_json()["data"]
    compact = _request(app, "GET", f"/cashflow/{created['id']}?detail=summary").get_json()["data"]
    expected = max(0, -min(full["outflow_with_interest"], default=0))
    assert compact["summary"]["peak_unfunded_shortfall"] == expected
    assert expected > compact["summary"]["peak_pre_financing_need"]


@pytest.mark.parametrize("detail", ["", "unknown", "SUMMARY"])
def test_invalid_detail_is_rejected(app, detail):
    created = _create(app)
    response = _request(app, "GET", f"/cashflow/{created['id']}?detail={detail}")
    assert response.status_code == 400


def test_summary_enforces_parent_permission_before_calculating(app):
    created = _create(app)
    denied = Mock(return_value=({"message": "Forbidden"}, 403))
    with patch("q_flow.routes.cashflows.ensure_unit_permission", denied), patch.object(
        Cashflow, "as_dict_with_activities", side_effect=AssertionError("calculated without permission")
    ):
        response = app.test_client().get(f"/cashflow/{created['id']}?detail=summary", headers=_auth())
    assert response.status_code == 403
    assert denied.call_args.args[1] == "unit-1"


def test_summary_rejects_missing_and_deleted_scenarios(app):
    created = _create(app)
    _request(app, "DELETE", f"/cashflow/{created['id']}")
    for cashflow_id in (created["id"], "missing"):
        assert _request(app, "GET", f"/cashflow/{cashflow_id}?detail=summary").status_code == 404
