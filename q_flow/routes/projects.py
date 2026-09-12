"""Project routes backed by QAuth Units."""

import logging

from flask import Blueprint, g, jsonify, request

from q_flow.exceptions import MissingData
from q_flow.extensions import db, u_api
from sqlalchemy import or_
from q_flow.models.activity import Activity
from q_flow.models.cashflow import Cashflow
from q_flow.services.decorators import auth_required
from q_flow.services.units import (
    EDIT_CASHFLOW,
    VIEW_CASHFLOW,
    QAuthUnitError,
    create_project_unit,
    ensure_unit_permission,
    load_project_unit,
    qauth_error,
    response_json,
)
from q_flow.services.utils import gen_id, read_data, rnd_color

projects = Blueprint("projects", __name__)
log = logging.getLogger(__name__)


def _cashflows(unit_id: str, *, include_deleted: bool = False):
    query = Cashflow.query.filter_by(unit_id=unit_id)
    if not include_deleted:
        query = query.filter_by(is_deleted=False)
    return query.order_by(Cashflow.name.asc()).all()


def _project_dict(unit: dict, roles=None, *, full_cashflows: bool = False) -> dict:
    cashflows = _cashflows(unit.get("id")) if unit.get("id") else []
    data = {
        "id": unit.get("id"),
        "name": unit.get("name") or "",
        "description": unit.get("description") or "",
        "color": unit.get("color") or "",
        "photo": unit.get("image_url") or "",
        "cashflows": [
            item.as_dict_with_activities() if full_cashflows else item.compact_dict()
            for item in cashflows
        ],
    }
    if roles is not None:
        data["roles"] = roles
    return data


def _require_permission(user, unit_id, permission):
    result = ensure_unit_permission(user, unit_id, permission)
    if isinstance(result, tuple):
        return None, result
    return result, None


@projects.route("/api", methods=["GET"])
def api():
    return jsonify(message="Welcome to the Q-Flow API"), 200


@projects.route("/projects")
@auth_required
def get_projects(user):
    data = read_data(request)
    response = u_api.get("unit/units", data={
        "page": data.get("page", 1, int),
        "per_page": data.get("per_page", 10, int),
        "sort_by": "updated_at",
        "sort_order": "desc",
    }, token=user.get("token"))
    if response.error:
        return qauth_error(response)
    payload = response_json(response).get("data") or {}
    result = []
    for entry in payload.get("units_with_roles") or []:
        unit = entry.get("unit") or {}
        if unit.get("id"):
            result.append(_project_dict(unit, entry.get("roles") or []))
    return jsonify(data=result, pages=payload.get("pages", 0)), 200


@projects.route("/new_project", methods=["POST"])
@auth_required
def new_project(user):
    data = read_data(request)
    MissingData.require_condition(data.get("name"), "Missing name")
    unit_id = gen_id()
    color = data.get("color") or rnd_color()
    try:
        unit = create_project_unit(
            u_api,
            token=user.get("token"),
            project_id=unit_id,
            data={**data, "color": color},
            image=request.files.get("photo"),
        )
    except QAuthUnitError as error:
        return qauth_error(error.response)

    unit = {**data, "id": unit.get("id") or unit_id, "color": color, **unit}
    cashflow = Cashflow(
        unit_id=unit["id"], name="Base Cashflow", description="",
        created_by=user.get("user_id"), updated_by=user.get("user_id"),
    )
    try:
        cashflow.commit()
    except Exception:
        log.exception("Base Cashflow creation failed for Unit %s", unit["id"])
        u_api.post(
            "unit/delete",
            token=getattr(g, "new_token", None) or user.get("token"),
            unit_id=unit["id"],
        )
        raise
    return jsonify(data=_project_dict(unit), message="Project created successfully"), 201


@projects.route("/project/<unit_id>")
@auth_required
def get_project(user, unit_id):
    loaded, error = load_project_unit(user, unit_id)
    if error:
        return error
    scoped_user, unit = loaded
    if VIEW_CASHFLOW not in set(scoped_user.get("unit_permissions") or []):
        return jsonify(
            code="unit_access_denied",
            message="Missing required project permission: view:cashflow",
        ), 403
    return jsonify(data=_project_dict(unit, full_cashflows=True)), 200


@projects.route("/update_project/<unit_id>", methods=["PUT"])
@auth_required
def update_project(user, unit_id):
    _, error = _require_permission(user, unit_id, EDIT_CASHFLOW)
    if error:
        return error
    data = read_data(request)
    unit_data = {key: data[key] for key in ("name", "description", "color") if key in data}
    image = request.files.get("photo")
    files = {"image": (image.filename, image.stream, image.mimetype)} if image else None
    response = u_api.post(
        "unit/edit", data=unit_data, files=files,
        token=getattr(g, "new_token", None) or user.get("token"), unit_id=unit_id)
    if response.error:
        return qauth_error(response)
    unit = (response_json(response).get("data") or {}).get("unit") or {
        **unit_data, "id": unit_id,
    }
    return jsonify(data=_project_dict(unit), message="Project updated successfully"), 200


def _change_project_state(user, unit_id, qauth_route, message):
    response = u_api.post(
        qauth_route,
        token=getattr(g, "new_token", None) or user.get("token"),
        unit_id=unit_id,
    )
    if response.error:
        return qauth_error(response)
    return jsonify(message=message), 200


@projects.route("/delete_project/<unit_id>", methods=["DELETE"])
@auth_required
def delete_project(user, unit_id):
    return _change_project_state(
        user, unit_id, "unit/deactivate", "Project deleted successfully")


@projects.route("/restore_project/<unit_id>", methods=["PUT"])
@auth_required
def restore_project(user, unit_id):
    return _change_project_state(
        user, unit_id, "unit/activate", "Project restored successfully")


@projects.route("/hard_delete_project/<unit_id>", methods=["DELETE"])
@auth_required
def hard_delete_project(user, unit_id):
    response = u_api.post(
        "unit/delete",
        token=getattr(g, "new_token", None) or user.get("token"),
        unit_id=unit_id,
    )
    if response.error:
        return qauth_error(response)
    cashflows = Cashflow.query.filter(or_(
        Cashflow.unit_id == unit_id,
        (Cashflow.id == unit_id) & Cashflow.unit_id.is_(None),
    )).all()
    cashflow_ids = [cashflow.id for cashflow in cashflows]
    if cashflow_ids:
        Activity.query.filter(Activity.cashflow_id.in_(cashflow_ids)).delete(
            synchronize_session=False)
    for cashflow in cashflows:
        db.session.delete(cashflow)
    db.session.commit()
    return jsonify(message="Project hard deleted successfully"), 200
