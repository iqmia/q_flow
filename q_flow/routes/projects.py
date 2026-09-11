"""Project routes backed by QAuth Units."""

import logging
import os

from flask import Blueprint, g, jsonify, request, send_file

from q_flow.exceptions import MissingData, ProjectNotDeleted, ProjectNotFound
from q_flow.extensions import fs, u_api
from q_flow.models.project import Project
from q_flow.services.decorators import auth_required
from q_flow.services.units import (
    EDIT_CASHFLOW,
    VIEW_CASHFLOW,
    QAuthUnitError,
    create_project_unit,
    ensure_unit_permission,
    load_project_unit,
    merge_unit_identity,
    qauth_error,
    response_json,
)
from q_flow.services.utils import read_data, rnd_color

projects = Blueprint("projects", __name__)
log = logging.getLogger(__name__)

IDENTITY_FIELDS = {"id", "name", "description", "photo", "color", "image_url"}


def _get_or_create_profile(unit: dict, user_id: str) -> Project:
    project = Project.query.get(unit.get("id"))
    if project:
        if project.is_deleted:
            # An active QAuth Unit is authoritative over the compatibility flag.
            project.is_deleted = False
            project.commit()
        return project
    project = Project(
        id=unit.get("id"),
        name=unit.get("name") or "",
        description=unit.get("description") or "",
        color=unit.get("color") or rnd_color(),
        photo="",
        created_by=user_id,
        updated_by=user_id,
    )
    return project.commit()


def _unit_response(response):
    return response_json(response).get("data", {}).get("unit") or {}


def _require_permission(user, project_id, permission):
    result = ensure_unit_permission(user, project_id, permission)
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
    params = {
        "page": data.get("page", 1, int),
        "per_page": data.get("per_page", 10, int),
        "sort_by": "updated_at",
        "sort_order": "desc",
    }
    response = u_api.get("unit/units", data=params, token=user.get("token"))
    if response.error:
        return qauth_error(response)
    payload = response_json(response).get("data") or {}
    merged_projects = []
    for entry in payload.get("units_with_roles") or []:
        unit = entry.get("unit") or {}
        if not unit.get("id"):
            continue
        profile = _get_or_create_profile(unit, user.get("user_id"))
        merged_projects.append(merge_unit_identity(
            profile.as_dict_with_activities(), unit, entry.get("roles") or []))
    return jsonify(data=merged_projects, pages=payload.get("pages", 0)), 200


@projects.route("/new_project", methods=["POST"])
@auth_required
def new_project(user):
    data = read_data(request)
    MissingData.require_condition(data.get("name"), "Missing name")
    project = Project().from_dict(data, user.get("user_id"))
    project.color = data.get("color") or rnd_color()
    try:
        unit = create_project_unit(
            u_api,
            token=user.get("token"),
            project_id=project.id,
            data={**data, "color": project.color},
            image=request.files.get("photo"),
        )
    except QAuthUnitError as error:
        return qauth_error(error.response)

    project.name = unit.get("name") or project.name
    project.description = unit.get("description") or project.description
    project.color = unit.get("color") or project.color
    project.photo = ""
    try:
        project.commit()
    except Exception:
        log.exception("Local project profile creation failed for Unit %s", project.id)
        cleanup_token = getattr(g, "new_token", None) or user.get("token")
        u_api.post("unit/delete", token=cleanup_token, unit_id=project.id)
        raise
    return jsonify(
        data=merge_unit_identity(project.as_dict_with_activities(), unit),
        message="Project created successfully",
    ), 201


@projects.route("/project/<project_id>")
@auth_required
def get_project(user, project_id):
    loaded, error = load_project_unit(user, project_id)
    if error:
        return error
    scoped_user, unit = loaded
    if VIEW_CASHFLOW not in set(scoped_user.get("unit_permissions") or []):
        return jsonify(code="unit_access_denied", message="Missing required project permission: view:cashflow"), 403
    project = _get_or_create_profile(unit, user.get("user_id"))
    return jsonify(data=merge_unit_identity(project.as_dict_with_activities(), unit)), 200


@projects.route("/update_project/<project_id>", methods=["PUT"])
@auth_required
def update_project(user, project_id):
    _, error = _require_permission(user, project_id, EDIT_CASHFLOW)
    if error:
        return error
    project = Project.query.get(project_id)
    ProjectNotFound.require_condition(project and not project.is_deleted, "Project not found")
    data = read_data(request)
    unit_data = {key: data[key] for key in ("name", "description", "color") if key in data}
    image = request.files.get("photo")
    files = {"image": (image.filename, image.stream, image.mimetype)} if image else None
    response = u_api.post(
        "unit/edit", data=unit_data, files=files,
        token=getattr(g, "new_token", None) or user.get("token"), unit_id=project_id)
    if response.error:
        return qauth_error(response)
    financial_data = {key: value for key, value in data.items() if key not in IDENTITY_FIELDS}
    project.update(user.get("user_id"), **financial_data)
    unit = _unit_response(response)
    project.name = unit.get("name") or project.name
    project.description = unit.get("description") or project.description
    project.color = unit.get("color") or project.color
    project.commit()
    return jsonify(
        data=merge_unit_identity(project.as_dict_with_activities(), unit),
        message="Project updated successfully",
    ), 200


def _change_project_state(user, project_id, qauth_route, local_action, message):
    project = Project.query.get(project_id)
    ProjectNotFound.require_condition(project, "Project not found")
    response = u_api.post(
        qauth_route,
        token=getattr(g, "new_token", None) or user.get("token"),
        unit_id=project_id,
    )
    if response.error:
        return qauth_error(response)
    local_action(project)
    return jsonify(message=message), 200


@projects.route("/delete_project/<project_id>", methods=["DELETE"])
@auth_required
def delete_project(user, project_id):
    project = Project.query.get(project_id)
    ProjectNotFound.require_condition(project and not project.is_deleted, "Project not found")
    return _change_project_state(
        user, project_id, "unit/deactivate", lambda item: item.delete(),
        "Project deleted successfully")


@projects.route("/restore_project/<project_id>", methods=["PUT"])
@auth_required
def restore_project(user, project_id):
    project = Project.query.get(project_id)
    ProjectNotFound.require_condition(project, "Project not found")
    ProjectNotDeleted.require_condition(project.is_deleted, "Project is not deleted")

    def restore(item):
        item.is_deleted = False
        item.commit()

    return _change_project_state(
        user, project_id, "unit/activate", restore,
        "Project restored successfully")


@projects.route("/hard_delete_project/<project_id>", methods=["DELETE"])
@auth_required
def hard_delete_project(user, project_id):
    return _change_project_state(
        user, project_id, "unit/delete", lambda item: item.hard_delete(),
        "Project hard deleted successfully")


@projects.route("/migrate_projects_to_units", methods=["POST"])
@auth_required
def migrate_projects_to_units(user):
    response = u_api.get(
        "unit/units", data={"page": 1, "per_page": 1000, "include_inactive": "true"},
        token=user.get("token"))
    if response.error:
        return qauth_error(response)
    entries = (response_json(response).get("data") or {}).get("units_with_roles") or []
    existing_ids = {entry.get("unit", {}).get("id") for entry in entries}
    migrated = []
    failures = []
    legacy_projects = Project.query.filter_by(created_by=user.get("user_id")).all()
    for project in legacy_projects:
        if project.id in existing_ids:
            continue
        try:
            create_project_unit(
                u_api, token=user.get("token"), project_id=project.id,
                data=project.as_dict())
            if project.is_deleted:
                unit_token = getattr(g, "new_token", None) or user.get("token")
                deactivate = u_api.post(
                    "unit/deactivate", token=unit_token, unit_id=project.id)
                if deactivate.error:
                    u_api.post("unit/delete", token=unit_token, unit_id=project.id)
                    raise QAuthUnitError(deactivate)
            migrated.append(project.id)
        except QAuthUnitError as error:
            failures.append({"id": project.id, "name": project.name, "message": str(error)})
    message = f"Migrated {len(migrated)} project(s) to QAuth Units"
    if failures:
        message += f"; {len(failures)} failed"
    return jsonify(data={"migrated": migrated, "failures": failures}, message=message), 200


@projects.route("/photo/<photo>", methods=["GET"])
def get_photo(photo):
    """Legacy local project-photo endpoint retained for old stored records."""
    return send_file(os.path.join(fs.project_photos, photo))
