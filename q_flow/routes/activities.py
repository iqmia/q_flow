from logging import getLogger
from math import isfinite
from os import path

from flask import Blueprint, current_app, jsonify, request, json
from sqlalchemy import func

from q_flow.cashflow import Activity_cf
from q_flow.exceptions import (
    InvalidData,
    MissingData,
    PermissionDenied,
    ProjectNotFound,
)
from q_flow.extensions import db
from q_flow.models.activity import Activity, ActivityType
from q_flow.models.cashflow import Cashflow
from q_flow.services.decorators import auth_required
from q_flow.services.units import EDIT_CASHFLOW, VIEW_CASHFLOW, ensure_unit_permission
from q_flow.services.utils import check_required, read_data

activities = Blueprint("activities", __name__)
log = getLogger(__name__)

_FRACTION_FIELDS = (
    "advance",
    "retention",
    "release_retention_eop",
    "work_in_excess",
    "mobilization",
    "profit",
    "subcontracted",
)
_NON_NEGATIVE_INTEGER_FIELDS = (
    "start",
    "dlp",
    "duration_for_payment",
    "mobilization_period",
    "no_billing_period",
)


def _permission_error(user, cashflow, permission):
    result = ensure_unit_permission(user, cashflow.unit_id, permission)
    return result if isinstance(result, tuple) else None


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and isfinite(value)
    )


def _validate_activity(activity):
    InvalidData.require_condition(
        _is_finite_number(activity.cost) and activity.cost > 0,
        "Activity cost must be a finite number greater than zero",
    )
    InvalidData.require_condition(
        isinstance(activity.duration, int)
        and not isinstance(activity.duration, bool)
        and activity.duration > 0,
        "Activity duration must be an integer greater than zero",
    )
    InvalidData.require_condition(
        _is_finite_number(activity.skew) and -1 < activity.skew < 1,
        "Activity skew must be greater than -1 and less than 1",
    )

    for field in _NON_NEGATIVE_INTEGER_FIELDS:
        value = getattr(activity, field)
        InvalidData.require_condition(
            isinstance(value, int)
            and not isinstance(value, bool)
            and value >= 0,
            f"Activity {field} must be a non-negative integer",
        )

    for field in _FRACTION_FIELDS:
        value = getattr(activity, field)
        InvalidData.require_condition(
            _is_finite_number(value) and 0 <= value <= 1,
            f"Activity {field} must be between zero and one",
        )
    InvalidData.require_condition(
        activity.advance + activity.retention <= 1,
        "Activity advance and retention must not exceed one combined",
    )


def _apply_activity_updates(activity, data, user_id):
    protected = {
        "id",
        "project_id",
        "created_at",
        "created_by",
        "cash_flow_json",
        "is_deleted",
    }
    for key in activity.__table__.columns.keys():
        if key in data and key not in protected:
            setattr(activity, key, data[key])
    activity.updated_by = user_id
    activity.updated_at = func.now()


def _set_scalar_defaults(model):
    for column in model.__table__.columns:
        if getattr(model, column.key) is not None:
            continue
        default = column.default
        if default is not None and default.is_scalar:
            setattr(model, column.key, default.arg)


def _set_cached_cashflow(activity):
    calculator = Activity_cf(activity)
    activity.cash_flow_json = {
        **calculator.marginal_work_as_json(),
        **calculator.out_flow_as_json(),
    }


def _finalize_mutation(cashflow, activity=None, use_type_skew=False):
    try:
        if activity is not None:
            _set_scalar_defaults(activity)
            if use_type_skew and activity.skew in (None, 0):
                activity.skew = ActivityType.skew_by_code(activity.activity_type)
            _validate_activity(activity)
            _set_cached_cashflow(activity)

        db.session.flush()
        snapshot = cashflow.as_dict_with_activities()
        db.session.commit()
        return snapshot
    except Exception:
        db.session.rollback()
        raise


@activities.route("/activities", methods=["GET"])
def get_activities():
    return jsonify({"data": "activities", "message": "test for roger"}), 200


@activities.route("/activities/types", methods=["GET"])
@auth_required
def get_activity_types(user):
    log.info(f"{user.get('name')} requested activity types")
    with open(path.join(current_app.static_folder, "activity_types.json")) as file:
        activity_types = json.load(file)
    return jsonify(data=activity_types), 200


@activities.route("/new_activity/<cashflow_id>", methods=["POST"])
@auth_required
def new_activity(user, cashflow_id):
    log.info(f"{user.get('name')} requested to create a new activity")
    data = read_data(request)
    cashflow = Cashflow.Identify(cashflow_id)
    ProjectNotFound.require_condition(cashflow, "Cashflow not found")
    error = _permission_error(user, cashflow, EDIT_CASHFLOW)
    if error:
        return error

    check_required(data, ["name", "cost", "duration"])
    MissingData.require_condition(
        data.get("name") and data.get("cost"), "Missing name or cost"
    )

    activity = Activity()
    activity.cashflow_id = cashflow_id
    activity.from_dict(data, user.get("user_id"))
    activity.cashflow_id = cashflow_id
    activity.is_deleted = False
    db.session.add(activity)
    snapshot = _finalize_mutation(
        cashflow, activity=activity, use_type_skew=True
    )
    return jsonify(
        data=activity.as_dict(),
        cashflow=snapshot,
        message="Activity created successfully",
    ), 201


@activities.route("/activity/<activity_id>", methods=["GET"])
@auth_required
def get_activity(user, activity_id):
    log.info(f"{user.get('name')} requested activity {activity_id}")
    activity = Activity.query.get(activity_id)
    PermissionDenied.require_condition(
        activity and not activity.is_deleted, "Activity not found"
    )
    error = _permission_error(user, activity.cashflow, VIEW_CASHFLOW)
    if error:
        return error
    return jsonify(
        data=activity.as_dict(), message="Activity retrieved successfully"
    ), 200


@activities.route("/update_activity/<activity_id>", methods=["PUT"])
@auth_required
def update_activity(user, activity_id):
    log.info(f"{user.get('name')} requested to update activity {activity_id}")
    data = read_data(request)
    activity = Activity.query.get(activity_id)
    PermissionDenied.require_condition(
        activity and not activity.is_deleted, "Activity not found"
    )
    error = _permission_error(user, activity.cashflow, EDIT_CASHFLOW)
    if error:
        return error

    check_required(data, ["name", "cost", "duration"])
    _apply_activity_updates(activity, data, user.get("user_id"))
    snapshot = _finalize_mutation(
        activity.cashflow, activity=activity, use_type_skew=True
    )
    return jsonify(
        data=activity.as_dict(),
        cashflow=snapshot,
        message="Activity updated successfully",
    ), 200


@activities.route("/delete_activity/<activity_id>", methods=["DELETE"])
@auth_required
def delete_activity(user, activity_id):
    log.info(f"{user.get('name')} requested to delete activity {activity_id}")
    activity = Activity.query.get(activity_id)
    PermissionDenied.require_condition(
        activity and not activity.is_deleted, "Activity not found"
    )
    cashflow = activity.cashflow
    error = _permission_error(user, cashflow, EDIT_CASHFLOW)
    if error:
        return error

    activity.is_deleted = True
    activity.updated_by = user.get("user_id")
    snapshot = _finalize_mutation(cashflow)
    return jsonify(
        cashflow=snapshot, message="Activity deleted successfully"
    ), 200


@activities.route("/hard_delete_activity/<activity_id>", methods=["DELETE"])
@auth_required
def hard_delete_activity(user, activity_id):
    log.info(f"{user.get('name')} requested to hard delete activity {activity_id}")
    activity = Activity.query.get(activity_id)
    PermissionDenied.require_condition(activity, "Activity not found")
    cashflow = activity.cashflow
    error = _permission_error(user, cashflow, EDIT_CASHFLOW)
    if error:
        return error

    try:
        # Exclude it from the response snapshot, then delete it in the same
        # transaction so a calculation failure cannot leave a partial write.
        activity.is_deleted = True
        db.session.flush()
        snapshot = cashflow.as_dict_with_activities()
        db.session.delete(activity)
        db.session.flush()
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return jsonify(
        cashflow=snapshot, message="Activity hard deleted successfully"
    ), 200


@activities.route("/restore_activity/<activity_id>", methods=["PUT"])
@auth_required
def restore_activity(user, activity_id):
    log.info(f"{user.get('name')} requested to restore activity {activity_id}")
    activity = Activity.query.get(activity_id)
    PermissionDenied.require_condition(activity, "Activity not found")
    cashflow = activity.cashflow
    error = _permission_error(user, cashflow, EDIT_CASHFLOW)
    if error:
        return error

    activity.is_deleted = False
    activity.updated_by = user.get("user_id")
    snapshot = _finalize_mutation(cashflow, activity=activity)
    return jsonify(
        cashflow=snapshot, message="Activity restored successfully"
    ), 200


@activities.route("/restore_activities", methods=["PUT"])
@auth_required
def restore_activities(user):
    data = read_data(request)
    activity_ids = data.get("data") or []
    log.info(
        f"{user.get('name')} requested to restore activities {activity_ids}"
    )
    restored_activities = Activity.query.filter(
        Activity.id.in_(activity_ids)
    ).all()
    affected_cashflows = sorted(
        {activity.cashflow for activity in restored_activities},
        key=lambda cashflow: cashflow.id,
    )
    for cashflow in affected_cashflows:
        error = _permission_error(user, cashflow, EDIT_CASHFLOW)
        if error:
            return error

    try:
        for activity in restored_activities:
            activity.is_deleted = False
            activity.updated_by = user.get("user_id")
        for activity in restored_activities:
            _validate_activity(activity)
            _set_cached_cashflow(activity)
        db.session.flush()
        snapshots = [
            cashflow.as_dict_with_activities()
            for cashflow in affected_cashflows
        ]
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    return jsonify(
        cashflows=snapshots, message="Activities restored successfully"
    ), 200


@activities.route("/deleted_activities/<cashflow_id>", methods=["GET"])
@auth_required
def get_deleted_activities(user, cashflow_id):
    log.info(
        f"{user.get('name')} requested deleted activities for cashflow {cashflow_id}"
    )
    cashflow = Cashflow.Identify(cashflow_id)
    ProjectNotFound.require_condition(cashflow, "Cashflow not found")
    error = _permission_error(user, cashflow, VIEW_CASHFLOW)
    if error:
        return error
    deleted = Activity.query.filter_by(
        cashflow_id=cashflow_id, is_deleted=True
    ).all()
    return jsonify(data=[activity.as_dict() for activity in deleted]), 200
