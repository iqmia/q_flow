"""Deletion and partial-edit contracts with isolated SQLite and mocked QAuth."""

from unittest.mock import Mock, patch

import pytest

from q_flow import create_app
from q_flow.config import TestConfig
from q_flow.extensions import db
from q_flow.models.activity import Activity
from q_flow.models.cashflow import Cashflow
from q_flow.services.user_api import U_Api_resp


def _qauth(status=200, **payload):
    response = Mock()
    response.json.return_value = payload
    return U_Api_resp(status, payload.get("message", "QAuth response"), response)


@pytest.fixture
def state(tmp_path):
    class IsolatedConfig(TestConfig):
        STORAGE_PATH = str(tmp_path)

    app = create_app(IsolatedConfig)
    user = {
        "user_id": "owner", "name": "Owner", "is_active": True,
        "token": "test-token", "unit_id": "unit-1",
        "unit_permissions": ["view:cashflow", "edit:cashflow"],
    }
    with app.app_context():
        for cf_id, unit, deleted in [
            ("cf-1", "unit-1", False), ("cf-deleted", "unit-1", True),
            ("cf-other", "unit-2", False), ("unit-1", None, True),
        ]:
            Cashflow(id=cf_id, unit_id=unit, name=cf_id, created_by="owner",
                     is_deleted=deleted).commit()
            for suffix, removed in [("active", False), ("deleted", True)]:
                Activity(id=f"{cf_id}-{suffix}", cashflow_id=cf_id,
                         name=suffix, created_by="owner", cost=100, duration=2,
                         is_deleted=removed).commit()
    with patch("q_flow.extensions.u_api.verify_token", return_value=user) as verify, \
         patch("q_flow.extensions.u_api.get", return_value=_qauth(403, message="Denied")) as get, \
         patch("q_flow.extensions.u_api.post", return_value=_qauth()) as post:
        yield app, user, verify, get, post
    with app.app_context():
        db.session.remove()
        db.drop_all()


def _delete(state, path, authenticated=True):
    headers = {"Authorization": "Bearer test-token"} if authenticated else {}
    return state[0].test_client().delete(path, headers=headers)


def _ids(state):
    with state[0].app_context():
        return (
            {row.id for row in Cashflow.query.all()},
            {row.id for row in Activity.query.all()},
        )


@pytest.mark.parametrize("path", [
    "/hard_delete_project/unit-1", "/cashflow/cf-1/hard",
    "/hard_delete_activity/cf-1-active",
])
def test_unauthenticated_delete_has_no_local_or_qauth_mutation(state, path):
    before = _ids(state)
    assert _delete(state, path, authenticated=False).status_code == 403
    assert _ids(state) == before
    state[4].assert_not_called()
    state[3].assert_not_called()


@pytest.mark.parametrize("path", [
    "/cashflow/cf-1/hard", "/hard_delete_activity/cf-1-active",
])
def test_same_unit_without_edit_permission_cannot_permanently_delete(state, path):
    state[1]["unit_permissions"] = ["view:cashflow"]
    before = _ids(state)
    assert _delete(state, path).status_code == 403
    assert _ids(state) == before
    state[3].assert_not_called()


@pytest.mark.parametrize("path", [
    "/cashflow/cf-other/hard", "/hard_delete_activity/cf-other-active",
])
def test_other_unit_requires_qauth_authorization_and_preserves_all_data(state, path):
    before = _ids(state)
    assert _delete(state, path).status_code == 403
    assert _ids(state) == before
    state[3].assert_called_once_with("unit/load", token="test-token", unit_id="unit-2")


@pytest.mark.parametrize("status", [403, 404, 408, 500, 503])
def test_project_qauth_denial_missing_id_or_failure_causes_no_local_loss(state, status):
    state[4].return_value = _qauth(status, message="Rejected")
    before = _ids(state)
    response = _delete(state, "/hard_delete_project/unit-1")
    assert response.status_code == status
    assert _ids(state) == before
    state[4].assert_called_once_with("unit/delete", token="test-token", unit_id="unit-1")


def test_project_delete_cascades_active_deleted_and_legacy_rows_only_in_unit(state):
    response = _delete(state, "/hard_delete_project/unit-1")
    assert response.status_code == 200
    assert _ids(state) == ({"cf-other"}, {"cf-other-active", "cf-other-deleted"})
    state[4].assert_called_once_with("unit/delete", token="test-token", unit_id="unit-1")
    state[4].return_value = _qauth(404, message="Project not found")
    assert _delete(state, "/hard_delete_project/unit-1").status_code == 404
    assert _ids(state) == ({"cf-other"}, {"cf-other-active", "cf-other-deleted"})


@pytest.mark.parametrize("cashflow_id", ["cf-1", "cf-deleted"])
def test_scenario_delete_cascades_only_its_active_and_deleted_activities(state, cashflow_id):
    cashflows, activities = _ids(state)
    assert _delete(state, f"/cashflow/{cashflow_id}/hard").status_code == 200
    assert _ids(state) == (
        cashflows - {cashflow_id},
        activities - {f"{cashflow_id}-active", f"{cashflow_id}-deleted"},
    )
    assert _delete(state, f"/cashflow/{cashflow_id}/hard").status_code == 404
    state[4].assert_not_called()


@pytest.mark.parametrize("suffix", ["active", "deleted"])
def test_activity_delete_removes_only_target_and_returns_remaining_snapshot(state, suffix):
    before_cashflows, before_activities = _ids(state)
    target = f"cf-1-{suffix}"
    response = _delete(state, f"/hard_delete_activity/{target}")
    assert response.status_code == 200
    assert _ids(state) == (before_cashflows, before_activities - {target})
    assert target not in {row["id"] for row in response.get_json()["cashflow"]["activities"]}
    assert _delete(state, f"/hard_delete_activity/{target}").status_code == 404


@pytest.mark.parametrize("path", ["/cashflow/missing/hard", "/hard_delete_activity/missing"])
def test_missing_scenario_and_activity_have_consistent_not_found_response(state, path):
    before = _ids(state)
    assert _delete(state, path).status_code == 404
    assert _ids(state) == before


@pytest.mark.parametrize("path", [
    "/cashflow/cf-other/hard", "/hard_delete_activity/cf-other-active",
])
def test_scenario_and_activity_qauth_outage_causes_no_local_loss(state, path):
    state[3].return_value = _qauth(503, message="Unavailable")
    before = _ids(state)
    assert _delete(state, path).status_code == 503
    assert _ids(state) == before


def test_activity_calculation_failure_rolls_back_permanent_delete(state):
    before = _ids(state)
    with patch.object(Cashflow, "as_dict_with_activities", side_effect=ValueError("Calculation failed")):
        with pytest.raises(ValueError, match="Calculation failed"):
            _delete(state, "/hard_delete_activity/cf-1-active")
    assert _ids(state) == before
    with state[0].app_context():
        assert db.session.get(Activity, "cf-1-active").is_deleted is False


@pytest.mark.parametrize("update", [{"start": 3}, {"name": "Renamed"}, {"cost": 250}, {"duration": 4}])
def test_activity_update_validates_merged_saved_source_for_partial_edits(state, update):
    response = state[0].test_client().put(
        "/update_activity/cf-1-active", headers={"Authorization": "Bearer test-token"}, json=update,
    )
    assert response.status_code == 200
    saved = response.get_json()["data"]
    for key, value in update.items():
        assert saved[key] == value
    assert saved["cashflow_id"] == "cf-1"
    with state[0].app_context():
        activity = db.session.get(Activity, "cf-1-active")
        for key, value in update.items():
            assert getattr(activity, key) == value


@pytest.mark.parametrize("parent_field", ["cashflow_id", "project_id"])
def test_activity_update_cannot_move_activity_across_unit_boundary(state, parent_field):
    response = state[0].test_client().put(
        "/update_activity/cf-1-active", headers={"Authorization": "Bearer test-token"},
        json={parent_field: "cf-other", "name": "Updated", "cost": 100, "duration": 2},
    )
    assert response.status_code == 200
    assert response.get_json()["data"]["cashflow_id"] == "cf-1"
    assert response.get_json()["cashflow"]["unit_id"] == "unit-1"
    with state[0].app_context():
        assert db.session.get(Activity, "cf-1-active").cashflow_id == "cf-1"


@pytest.mark.parametrize("update", [
    {"name": ""}, {"cost": 0}, {"duration": 0}, {"start": -1},
])
def test_invalid_partial_edit_preserves_saved_source(state, update):
    with state[0].app_context():
        before = db.session.get(Activity, "cf-1-active").as_dict()
    response = state[0].test_client().put(
        "/update_activity/cf-1-active", headers={"Authorization": "Bearer test-token"}, json=update,
    )
    assert response.status_code == 400
    with state[0].app_context():
        assert db.session.get(Activity, "cf-1-active").as_dict() == before
