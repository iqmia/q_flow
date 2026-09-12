"""QAuth Unit helpers for Cashflowpot projects."""

from os import path
from typing import Optional

from flask import current_app, g, jsonify

from q_flow.extensions import u_api
from q_flow.services.user_api import U_Api_resp, User_API


VIEW_CASHFLOW = "view:cashflow"
EDIT_CASHFLOW = "edit:cashflow"


def response_json(response: U_Api_resp) -> dict:
    if response.response is None:
        return {}
    try:
        return response.response.json()
    except (TypeError, ValueError):
        return {}


def qauth_error(response: U_Api_resp):
    status = response.status_code if response.status_code >= 400 else 502
    code = "qauth_unavailable" if status in (408, 502, 503, 504) else "qauth_error"
    return jsonify(code=code, message=response.message or "QAuth request failed"), status


def _roles_config_bytes() -> bytes:
    roles_path = path.join(current_app.static_folder, "cashflowpot_roles.json")
    with open(roles_path, "rb") as roles_file:
        return roles_file.read()


def create_project_unit(
    api: User_API,
    *,
    token: str,
    project_id: str,
    data: dict,
    image: Optional[object] = None,
) -> dict:
    form = {
        "id": project_id,
        "name": data.get("name"),
        "description": data.get("description") or "",
        "color": data.get("color") or "",
    }
    files = {
        "roles_config": (
            "cashflowpot_roles.json",
            _roles_config_bytes(),
            "application/json",
        )
    }
    if image:
        files["image"] = (
            getattr(image, "filename", "project-image"),
            image.stream,
            getattr(image, "mimetype", "application/octet-stream"),
        )
    response = api.post("unit/new", data=form, files=files, token=token)
    if response.error:
        raise QAuthUnitError(response)
    payload = response_json(response)
    new_token = payload.get("token") or payload.get("data", {}).get("token")
    if new_token:
        g.new_token = new_token
    return payload.get("data", {}).get("unit") or {}


def create_unit_for_owner(
    api: User_API,
    *,
    owner_user_id: str,
    unit_id: str,
    name: str,
    description: str = "",
    color: str = "",
) -> tuple[dict, bool]:
    """Create a Unit through QAuth's trusted app-service endpoint."""
    response = api.post(
        "unit/admin/new",
        data={
            "owner_user_id": owner_user_id,
            "id": unit_id,
            "name": name,
            "description": description or "",
            "color": color or "",
        },
        files={
            "roles_config": (
                "cashflowpot_roles.json",
                _roles_config_bytes(),
                "application/json",
            )
        },
    )
    if response.error:
        raise QAuthUnitError(response)
    data = response_json(response).get("data") or {}
    return data.get("unit") or {}, bool(data.get("already_exists"))


def load_project_unit(user: dict, unit_id: str, api: User_API = u_api):
    response = api.get("unit/load", token=user.get("token"), unit_id=unit_id)
    if response.error:
        return None, qauth_error(response)
    payload = response_json(response)
    data = payload.get("data") or {}
    token = data.get("token") or payload.get("token")
    if not token:
        return None, (jsonify(code="qauth_error", message="QAuth did not return a unit token"), 502)
    scoped_user = api.verify_token(token)
    if scoped_user.get("error"):
        return None, (jsonify(code="reauth_required", message=scoped_user["error"]), 401)
    g.new_token = token
    return (scoped_user, data.get("unit") or {}), None


def ensure_unit_permission(
    user: dict,
    unit_id: str,
    permission: str,
    *,
    api: User_API = u_api,
):
    """Return a scoped user or a Flask error tuple."""
    scoped_user = user
    if user.get("unit_id") != unit_id:
        loaded, error = load_project_unit(user, unit_id, api=api)
        if error:
            return error
        scoped_user, _ = loaded
    permissions = set(scoped_user.get("unit_permissions") or [])
    if scoped_user.get("unit_id") != unit_id or permission not in permissions:
        return jsonify(
            code="unit_access_denied",
            message=f"Missing required project permission: {permission}",
        ), 403
    return scoped_user


def merge_unit_identity(project_data: dict, unit: dict, roles=None) -> dict:
    merged = dict(project_data)
    merged.update({
        "id": unit.get("id", merged.get("id")),
        "name": unit.get("name", merged.get("name", "")),
        "description": unit.get("description", merged.get("description", "")),
        "color": unit.get("color", merged.get("color", "")),
        "photo": unit.get("image_url") or "",
    })
    if roles is not None:
        merged["roles"] = roles
    return merged


class QAuthUnitError(Exception):
    def __init__(self, response: U_Api_resp):
        super().__init__(response.message)
        self.response = response
