from unittest.mock import Mock, patch

import pytest

from q_flow import create_app
from q_flow.config import TestConfig
from q_flow.extensions import db
from q_flow.models.activity import Activity
from q_flow.models.cashflow import Cashflow
from q_flow.services.user_api import U_Api_resp


class _Response:
    def __init__(self, payload, status_code=200):
        self.payload = payload
        self.status_code = status_code
        self.reason = payload.get("message", "")
        self.text = str(payload)
        self.headers = {"content-type": "application/json"}

    def json(self):
        return self.payload


def _qauth_response(payload, status=200):
    return U_Api_resp(status, payload.get("message", "ok"), _Response(payload, status))


@pytest.fixture
def app(tmp_path):
    class RouteConfig(TestConfig):
        STORAGE_PATH = str(tmp_path)

    app = create_app(RouteConfig)
    user = {
        "user_id": "owner-1", "name": "Owner", "is_active": True,
        "token": "user-token",
    }
    with patch("q_flow.services.decorators.u_api.verify_token", return_value=user):
        yield app
    with app.app_context():
        db.session.remove()
        db.drop_all()


def _auth():
    return {"Authorization": "Bearer user-token"}


def test_projects_group_cashflows_under_qauth_units(app):
    with app.app_context():
        Cashflow(id="cf-1", unit_id="unit-1", name="Tender", created_by="owner-1").commit()
        Cashflow(id="cf-2", unit_id="unit-1", name="Bank", created_by="owner-1").commit()
    response = _qauth_response({"data": {
        "units_with_roles": [{
            "unit": {"id": "unit-1", "name": "Tower", "description": "Residential"},
            "roles": ["creator"],
        }],
        "pages": 1,
    }})

    with patch("q_flow.routes.projects.u_api.get", return_value=response):
        result = app.test_client().get("/projects", headers=_auth())

    assert result.status_code == 200
    project = result.get_json()["data"][0]
    assert project["id"] == "unit-1"
    assert project["name"] == "Tower"
    assert [item["name"] for item in project["cashflows"]] == ["Bank", "Tender"]


def test_new_project_creates_qauth_unit_and_base_cashflow(app):
    def create_unit(_api, **kwargs):
        return {
            "id": kwargs["project_id"], "name": "Tower",
            "description": "Residential", "color": "#123456",
        }

    with patch("q_flow.routes.projects.create_project_unit", side_effect=create_unit) as create:
        result = app.test_client().post(
            "/new_project", headers=_auth(),
            json={"name": "Tower", "description": "Residential"},
        )

    assert result.status_code == 201
    project = result.get_json()["data"]
    assert project["id"] == create.call_args.kwargs["project_id"]
    assert len(project["cashflows"]) == 1
    assert project["cashflows"][0]["name"] == "Base Cashflow"
    with app.app_context():
        cashflow = Cashflow.query.one()
        assert cashflow.unit_id == project["id"]
        assert cashflow.id != project["id"]


def test_cashflow_crud_is_scoped_to_parent_unit(app):
    permission = Mock(return_value={"user_id": "owner-1", "unit_id": "unit-1"})
    with patch("q_flow.routes.cashflows.ensure_unit_permission", permission):
        created = app.test_client().post(
            "/project/unit-1/cashflows", headers=_auth(),
            json={"name": "Financing", "contract_value": 1_000_000},
        )
        cashflow_id = created.get_json()["data"]["id"]
        fetched = app.test_client().get(f"/cashflow/{cashflow_id}", headers=_auth())
        updated = app.test_client().put(
            f"/cashflow/{cashflow_id}", headers=_auth(),
            json={"name": "Bank Financing", "contract_value": 1_250_000},
        )

    assert created.status_code == 201
    assert fetched.status_code == 200
    assert updated.get_json()["data"]["name"] == "Bank Financing"
    assert updated.get_json()["data"]["contract_value"] == 1_250_000
    assert all(call.args[1] == "unit-1" for call in permission.call_args_list)


def test_activity_permission_uses_cashflow_unit(app):
    with app.app_context():
        cashflow = Cashflow(id="cf-1", unit_id="unit-1", name="Tender", created_by="owner-1").commit()
        activity = Activity(name="Concrete", cashflow_id=cashflow.id, created_by="owner-1").commit()
        activity_id = activity.id
    permission = Mock(return_value={"user_id": "owner-1", "unit_id": "unit-1"})

    with patch("q_flow.routes.activities.ensure_unit_permission", permission):
        result = app.test_client().get(f"/activity/{activity_id}", headers=_auth())

    assert result.status_code == 200
    assert result.get_json()["data"]["cashflow_id"] == "cf-1"
    permission.assert_called_once()
    assert permission.call_args.args[1] == "unit-1"


def test_removed_request_time_migration_route_returns_not_found(app):
    result = app.test_client().post("/migrate_projects_to_units", headers=_auth())
    assert result.status_code == 404


def test_hard_delete_project_removes_all_local_cashflows_after_qauth(app):
    with app.app_context():
        first = Cashflow(id="cf-1", unit_id="unit-1", name="Tender", created_by="owner-1").commit()
        Cashflow(id="cf-2", unit_id="unit-1", name="Bank", created_by="owner-1").commit()
        Activity(name="Concrete", cashflow_id=first.id, created_by="owner-1").commit()
    response = _qauth_response({"message": "deleted"})

    with patch("q_flow.routes.projects.u_api.post", return_value=response):
        result = app.test_client().delete("/hard_delete_project/unit-1", headers=_auth())

    assert result.status_code == 200
    with app.app_context():
        assert Cashflow.query.filter_by(unit_id="unit-1").count() == 0
        assert Activity.query.count() == 0
