"""Independent cashflow scenario routes."""

from math import isfinite

from flask import Blueprint, jsonify, request
from sqlalchemy import func

from q_flow.exceptions import InvalidData, MissingData, ProjectNotDeleted, ProjectNotFound
from q_flow.extensions import db
from q_flow.models.activity import Activity, ActivityType
from q_flow.models.cashflow import Cashflow
from q_flow.routes.activities import (
    _set_cached_cashflow,
    _set_scalar_defaults as _set_activity_scalar_defaults,
    _validate_activity,
)
from q_flow.services.decorators import auth_required
from q_flow.services.units import EDIT_CASHFLOW, VIEW_CASHFLOW, ensure_unit_permission
from q_flow.services.utils import read_data

cashflows = Blueprint("cashflows", __name__)

_IMPORT_FORMAT = "cashflowpot.cashflow"
_IMPORT_VERSION = 1
_CASHFLOW_IMPORT_FIELDS = {
    "name",
    "description",
    "advance",
    "retention",
    "release_retention_eop",
    "dlp",
    "duration_for_payment",
    "interest_rate",
    "contract_value",
    "wieb",
}
_ACTIVITY_IMPORT_FIELDS = {
    "name",
    "activity_type",
    "cost",
    "duration",
    "duration_units",
    "start",
    "advance",
    "retention",
    "release_retention_eop",
    "dlp",
    "duration_for_payment",
    "work_in_excess",
    "mobilization_period",
    "subcontracted",
    "skew",
    "no_billing_period",
}


def _permission(user, cashflow: Cashflow, permission: str):
    result = ensure_unit_permission(user, cashflow.unit_id, permission)
    return result if isinstance(result, tuple) else None


def _active_cashflow(cashflow_id: str) -> Cashflow:
    cashflow = Cashflow.query.get(cashflow_id)
    ProjectNotFound.require_condition(
        cashflow and not cashflow.is_deleted, "Cashflow not found")
    return cashflow


def _finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and isfinite(value)
    )


def _set_scalar_defaults(model):
    for column in model.__table__.columns:
        if getattr(model, column.key) is not None:
            continue
        default = column.default
        if default is not None and default.is_scalar:
            setattr(model, column.key, default.arg)


def _validate_cashflow(cashflow):
    InvalidData.require_condition(
        _finite_number(cashflow.contract_value)
        and cashflow.contract_value >= 0,
        "Contract value must be a finite non-negative number",
    )
    for field in ("advance", "retention", "release_retention_eop", "wieb"):
        value = getattr(cashflow, field)
        InvalidData.require_condition(
            _finite_number(value) and 0 <= value <= 1,
            f"Cashflow {field} must be between zero and one",
        )
    InvalidData.require_condition(
        cashflow.advance + cashflow.retention <= 1,
        "Cashflow advance and retention must not exceed one combined",
    )
    InvalidData.require_condition(
        _finite_number(cashflow.interest_rate)
        and cashflow.interest_rate >= 0,
        "Interest rate must be a finite non-negative number",
    )
    for field in ("dlp", "duration_for_payment"):
        value = getattr(cashflow, field)
        InvalidData.require_condition(
            isinstance(value, int)
            and not isinstance(value, bool)
            and value >= 0,
            f"Cashflow {field} must be a non-negative integer",
        )


def _apply_cashflow_updates(cashflow, data, user_id):
    protected = {"id", "unit_id", "created_at", "created_by"}
    for key in cashflow.__table__.columns.keys():
        if key in data and key not in protected:
            setattr(cashflow, key, data[key])
    cashflow.updated_by = user_id
    cashflow.updated_at = func.now()


def _filtered(data, allowed_fields):
    return {key: value for key, value in data.items() if key in allowed_fields}


def _require_text(data, key, label):
    value = data.get(key)
    InvalidData.require_condition(
        isinstance(value, str) and value.strip(),
        f"{label} must be non-empty text",
    )


def _optional_text(data, key, label):
    if key not in data:
        return
    InvalidData.require_condition(
        isinstance(data[key], str),
        f"{label} must be text",
    )


def _read_import_payload(data):
    InvalidData.require_condition(
        isinstance(data, dict), "Invalid cashflow import payload")
    InvalidData.require_condition(
        data.get("format") == _IMPORT_FORMAT,
        "Unsupported cashflow file format",
    )
    InvalidData.require_condition(
        data.get("version") == _IMPORT_VERSION,
        "Unsupported cashflow file version",
    )
    cashflow_data = data.get("cashflow")
    InvalidData.require_condition(
        isinstance(cashflow_data, dict),
        "Missing cashflow data",
    )
    activities = cashflow_data.get("activities", [])
    InvalidData.require_condition(
        isinstance(activities, list),
        "Cashflow activities must be a list",
    )
    return cashflow_data, activities


@cashflows.route("/project/<unit_id>/cashflows", methods=["POST"])
@auth_required
def new_cashflow(user, unit_id):
    result = ensure_unit_permission(user, unit_id, EDIT_CASHFLOW)
    if isinstance(result, tuple):
        return result
    data = read_data(request)
    MissingData.require_condition(data.get("name"), "Missing cashflow name")
    cashflow = Cashflow().from_dict(data, user.get("user_id"))
    cashflow.unit_id = unit_id
    db.session.add(cashflow)
    try:
        _set_scalar_defaults(cashflow)
        _validate_cashflow(cashflow)
        db.session.flush()
        snapshot = cashflow.as_dict_with_activities()
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return jsonify(
        data=snapshot,
        message="Cashflow created successfully",
    ), 201


@cashflows.route("/project/<unit_id>/cashflows/import", methods=["POST"])
@auth_required
def import_cashflow(user, unit_id):
    result = ensure_unit_permission(user, unit_id, EDIT_CASHFLOW)
    if isinstance(result, tuple):
        return result

    raw = read_data(request)
    cashflow_data, activity_rows = _read_import_payload(raw)
    _require_text(cashflow_data, "name", "Cashflow name")
    _optional_text(cashflow_data, "description", "Cashflow description")

    user_id = user.get("user_id")
    cashflow = Cashflow().from_dict(
        _filtered(cashflow_data, _CASHFLOW_IMPORT_FIELDS),
        user_id,
    )
    cashflow.unit_id = unit_id
    cashflow.is_deleted = False
    db.session.add(cashflow)

    try:
        _set_scalar_defaults(cashflow)
        _validate_cashflow(cashflow)

        for row in activity_rows:
            InvalidData.require_condition(
                isinstance(row, dict),
                "Each imported activity must be an object",
            )
            _require_text(row, "name", "Activity name")
            _optional_text(row, "activity_type", "Activity type")
            _optional_text(row, "duration_units", "Activity duration units")
            MissingData.require_condition(
                "cost" in row and "duration" in row,
                "Missing activity cost or duration",
            )

            activity_data = _filtered(row, _ACTIVITY_IMPORT_FIELDS)
            activity = Activity().from_dict(activity_data, user_id)
            activity.cashflow_id = cashflow.id
            activity.is_deleted = False
            _set_activity_scalar_defaults(activity)
            if "skew" not in activity_data or activity.skew is None:
                activity.skew = ActivityType.skew_by_code(activity.activity_type)
            _validate_activity(activity)
            _set_cached_cashflow(activity)
            db.session.add(activity)

        db.session.flush()
        snapshot = cashflow.as_dict_with_activities()
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    return jsonify(
        data=snapshot,
        message="Cashflow imported successfully",
    ), 201


@cashflows.route("/cashflow/<cashflow_id>")
@auth_required
def get_cashflow(user, cashflow_id):
    cashflow = _active_cashflow(cashflow_id)
    error = _permission(user, cashflow, VIEW_CASHFLOW)
    if error:
        return error
    return jsonify(data=cashflow.as_dict_with_activities()), 200


@cashflows.route("/cashflow/<cashflow_id>", methods=["PUT"])
@auth_required
def update_cashflow(user, cashflow_id):
    cashflow = _active_cashflow(cashflow_id)
    error = _permission(user, cashflow, EDIT_CASHFLOW)
    if error:
        return error
    data = read_data(request)
    _apply_cashflow_updates(cashflow, data, user.get("user_id"))
    try:
        _validate_cashflow(cashflow)
        db.session.flush()
        snapshot = cashflow.as_dict_with_activities()
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return jsonify(
        data=snapshot,
        message="Cashflow updated successfully",
    ), 200


@cashflows.route("/cashflow/<cashflow_id>", methods=["DELETE"])
@auth_required
def delete_cashflow(user, cashflow_id):
    cashflow = _active_cashflow(cashflow_id)
    error = _permission(user, cashflow, EDIT_CASHFLOW)
    if error:
        return error
    cashflow.delete()
    return jsonify(message="Cashflow deleted successfully"), 200


@cashflows.route("/cashflow/<cashflow_id>/restore", methods=["PUT"])
@auth_required
def restore_cashflow(user, cashflow_id):
    cashflow = Cashflow.query.get(cashflow_id)
    ProjectNotFound.require_condition(cashflow, "Cashflow not found")
    ProjectNotDeleted.require_condition(cashflow.is_deleted, "Cashflow is not deleted")
    error = _permission(user, cashflow, EDIT_CASHFLOW)
    if error:
        return error
    cashflow.is_deleted = False
    cashflow.commit()
    return jsonify(message="Cashflow restored successfully"), 200


@cashflows.route("/cashflow/<cashflow_id>/hard", methods=["DELETE"])
@auth_required
def hard_delete_cashflow(user, cashflow_id):
    cashflow = Cashflow.query.get(cashflow_id)
    ProjectNotFound.require_condition(cashflow, "Cashflow not found")
    error = _permission(user, cashflow, EDIT_CASHFLOW)
    if error:
        return error
    Activity.query.filter_by(cashflow_id=cashflow.id).delete(
        synchronize_session=False)
    db.session.delete(cashflow)
    db.session.commit()
    return jsonify(message="Cashflow hard deleted successfully"), 200
