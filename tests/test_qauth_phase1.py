import io
import json
from unittest.mock import Mock, patch

import jwt
from flask import g

from q_flow.services.user_api import U_Api_resp, User_API


def _response(status, payload):
    response = Mock()
    response.status_code = status
    response.reason = payload.get("message", "")
    response.text = json.dumps(payload)
    response.headers = {"content-type": "application/json"}
    response.json.return_value = payload
    return response


def test_user_api_normalizes_legacy_user_base_url():
    api = User_API()
    api.url = "https://qauth.example/api/user/"

    assert api._build_url("user/login") == "https://qauth.example/api/user/login"
    assert api._build_url("unit/new") == "https://qauth.example/api/unit/new"


def test_expired_token_uses_fresh_token_endpoint_and_preserves_scope(app):
    api = User_API()
    api.app_id = "cashflowpot"
    api.public_key = "public"
    api.algo = "RS256"
    refreshed = {"user_id": "u1", "unit_id": "p1", "unit_permissions": ["view:cashflow"],
                 "client_app_id": "cashflowpot", "is_active": True}
    refresh_response = U_Api_resp(200, "ok", _response(200, {"data": {"token": "fresh"}}))

    with app.test_request_context("/"), \
            patch("q_flow.services.user_api.jwt.decode", side_effect=[jwt.ExpiredSignatureError, refreshed]), \
            patch.object(api, "post", return_value=refresh_response) as post:
        app.config["TESTING"] = False
        result = api.verify_token("expired")

        assert result["unit_id"] == "p1"
        assert g.new_token == "fresh"
        post.assert_called_once_with("user/get_fresh_token", token="expired")


def test_refresh_failure_is_structured_as_reauthentication(app):
    api = User_API()
    api.app_id = "cashflowpot"
    api.public_key = "public"
    api.algo = "RS256"

    with app.test_request_context("/"), \
            patch("q_flow.services.user_api.jwt.decode", side_effect=jwt.ExpiredSignatureError), \
            patch.object(api, "post", return_value=U_Api_resp(401, "refresh expired")):
        app.config["TESTING"] = False
        result = api.verify_token("expired")

    assert result == {"error": "refresh expired", "code": "reauth_required"}


def test_roles_config_contains_cashflow_roles_and_permissions():
    with open("q_flow/static/cashflowpot_roles.json", encoding="utf-8") as roles_file:
        config = json.load(roles_file)

    permissions = {item["name"] for item in config["permissions"]}
    roles = {item["name"]: item["grants"] for item in config["roles"]}
    assert {"view:cashflow", "edit:cashflow"} <= permissions
    assert roles["creator"] == ["*"]
    assert "edit:cashflow" in roles["editor"]
    assert "edit:unit" in roles["editor"]
    assert roles["viewer"] == ["view:unit", "leave:unit", "view:cashflow"]


def test_create_unit_sends_roles_config_and_project_id(app):
    from q_flow.services.units import create_project_unit

    api_response = U_Api_resp(200, "created", _response(200, {
        "data": {"unit": {"id": "project-1", "name": "Tower"}},
        "token": "unit-token",
    }))
    api = Mock()
    api.post.return_value = api_response

    with app.test_request_context("/"):
        unit = create_project_unit(
            api, token="user-token", project_id="project-1",
            data={"name": "Tower", "description": "Residential"})
        assert g.new_token == "unit-token"

    assert unit["id"] == "project-1"
    _, kwargs = api.post.call_args
    assert kwargs["data"]["id"] == "project-1"
    assert "roles_config" in kwargs["files"]
    assert isinstance(kwargs["files"]["roles_config"][1], (bytes, bytearray))


def test_unit_permission_rejects_missing_permission(app):
    from q_flow.services.units import ensure_unit_permission

    with app.test_request_context("/"):
        result = ensure_unit_permission(
            {"unit_id": "project-1", "unit_permissions": [], "token": "token"},
            "project-1", "view:cashflow", api=Mock())

    assert result[0].get_json()["code"] == "unit_access_denied"
    assert result[1] == 403


def test_google_login_proxies_provider_token_to_current_qauth_endpoint(app):
    qauth_response = U_Api_resp(200, "Success", _response(200, {
        "data": {"token": "qauth-token"},
    }))
    with patch("q_flow.routes.users.u_api.post", return_value=qauth_response) as post, \
            patch("q_flow.routes.users.u_api.verify_token", return_value={
                "user_id": "u1", "name": "User", "email": "u@example.com", "photo": "avatar"
            }):
        response = app.test_client().put("/google_login", json={
            "idToken": "google-id-token",
            "accessToken": "google-access-token",
            "platform": "windows",
            "user_info": {"email": "untrusted@example.com"},
        })

    assert response.status_code == 200
    post.assert_called_once_with("user/tp_login/google", data={
        "id_token": "google-id-token",
        "access_token": "google-access-token",
        "platform": "windows",
    })
    assert response.get_json()["data"]["user"]["image"] == "avatar"


def test_new_project_creates_qauth_unit_with_same_local_id(app):
    unit = {"id": "unused", "name": "Tower", "description": "QAuth description",
            "color": "#123456", "image_url": "https://qauth/unit/image/tower"}

    def create_unit(_api, **kwargs):
        unit["id"] = kwargs["project_id"]
        return unit

    with patch("q_flow.routes.projects.create_project_unit", side_effect=create_unit) as create:
        response = app.test_client().post(
            "/new_project",
            headers={"Authorization": "Bearer user-token"},
            json={"name": "Tower", "description": "Local description", "contract_value": 1_000_000},
        )

    assert response.status_code == 201
    data = response.get_json()["data"]
    assert data["id"] == create.call_args.kwargs["project_id"]
    assert data["name"] == "Tower"
    assert data["description"] == "QAuth description"
    assert data["contract_value"] == 1_000_000
    assert data["photo"] == "https://qauth/unit/image/tower"


def test_projects_are_listed_from_qauth_units_and_merged_with_profiles(app):
    from q_flow.models.project import Project

    with app.app_context():
        Project(id="p1", name="stale", description="stale", color="stale",
                created_by="legacy", contract_value=250_000).commit()
    qauth_response = U_Api_resp(200, "ok", _response(200, {
        "data": {
            "units_with_roles": [{
                "unit": {"id": "p1", "name": "Canonical", "description": "From QAuth",
                         "color": "#abcdef", "image_url": None},
                "roles": ["editor"],
            }],
            "pages": 1,
        }
    }))

    with patch("q_flow.routes.projects.u_api.get", return_value=qauth_response):
        response = app.test_client().get(
            "/projects", headers={"Authorization": "Bearer user-token"})

    assert response.status_code == 200
    data = response.get_json()["data"][0]
    assert data["name"] == "Canonical"
    assert data["contract_value"] == 250_000
    assert data["roles"] == ["editor"]


def test_activity_mutation_requires_edit_cashflow_permission(app):
    from q_flow.models.project import Project

    with app.app_context():
        Project(id="p1", name="Project", description="", created_by="u1").commit()
    viewer = {
        "user_id": "u1", "name": "Viewer", "email": "viewer@example.com",
        "is_active": True, "unit_id": "p1", "unit_permissions": ["view:cashflow"],
        "token": "viewer-token",
    }
    with patch("q_flow.services.decorators.u_api.verify_token", return_value=viewer):
        response = app.test_client().post(
            "/new_activity/p1",
            headers={"Authorization": "Bearer viewer-token"},
            json={"name": "Concrete", "cost": 1000, "duration": 4},
        )

    assert response.status_code == 403
    assert response.get_json()["code"] == "unit_access_denied"


def test_legacy_project_migration_skips_existing_units(app):
    from q_flow.models.project import Project

    with app.app_context():
        Project(id="existing", name="Existing", created_by="1").commit()
        Project(id="legacy", name="Legacy", created_by="1").commit()
    qauth_response = U_Api_resp(200, "ok", _response(200, {
        "data": {"units_with_roles": [{"unit": {"id": "existing"}, "roles": ["creator"]}]}
    }))
    with patch("q_flow.routes.projects.u_api.get", return_value=qauth_response), \
            patch("q_flow.routes.projects.create_project_unit", return_value={"id": "legacy"}) as create:
        response = app.test_client().post(
            "/migrate_projects_to_units",
            headers={"Authorization": "Bearer user-token"},
        )

    assert response.status_code == 200
    assert response.get_json()["data"]["migrated"] == ["legacy"]
    assert create.call_count == 1
    assert create.call_args.kwargs["project_id"] == "legacy"


def test_restore_uses_qauth_inactive_unit_endpoint_without_loading_unit(app):
    from q_flow.models.project import Project

    with app.app_context():
        Project(id="inactive", name="Inactive", created_by="1", is_deleted=True).commit()
    qauth_response = U_Api_resp(200, "activated", _response(200, {
        "data": {"unit": {"id": "inactive", "name": "Inactive"}}
    }))
    with patch("q_flow.routes.projects.u_api.post", return_value=qauth_response) as post, \
            patch("q_flow.routes.projects.ensure_unit_permission") as permission:
        response = app.test_client().put(
            "/restore_project/inactive",
            headers={"Authorization": "Bearer user-token"},
        )

    assert response.status_code == 200
    permission.assert_not_called()
    post.assert_called_once_with("unit/activate", token="user-token", unit_id="inactive")


import pytest
from q_flow import create_app
from q_flow.config import TestConfig


@pytest.fixture
def app(tmp_path):
    class Phase1TestConfig(TestConfig):
        STORAGE_PATH = str(tmp_path)

    return create_app(Phase1TestConfig)
