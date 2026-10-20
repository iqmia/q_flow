"""Independent cashflow scenario routes."""

from math import isfinite

from flask import Blueprint, jsonify, request
from sqlalchemy import func

from q_flow.exceptions import InvalidData, MissingData, ProjectNotDeleted, ProjectNotFound
from q_flow.financing import FACILITY_PRESETS, validate_financing_facilities
from q_flow.extensions import db
from q_flow.models.activity import (
    Activity,
    ActivityType,
    effective_distribution_type,
    normalize_activity,
)
from q_flow.models.cashflow import Cashflow
from q_flow.routes.activities import (
    _set_cached_cashflow,
    _set_scalar_defaults as _set_activity_scalar_defaults,
    _validate_activity,
)
from q_flow.services.cashflow_facilities import (
    add_facility,
    delete_facility,
    get_facility,
    new_facilities_with_defaults,
    normalize_facility_ids,
    set_facility_order,
    update_facility,
)
from q_flow.services.decorators import auth_required
from q_flow.services.portable_cashflow import (
    ACTIVITY_SOURCE_FIELDS,
    CASHFLOW_SOURCE_FIELDS,
    PORTABLE_FORMAT,
    PORTABLE_VERSION,
    build_portable_cashflow,
)
from q_flow.services.units import EDIT_CASHFLOW, VIEW_CASHFLOW, ensure_unit_permission
from q_flow.services.utils import read_data

cashflows = Blueprint("cashflows", __name__)


@cashflows.route("/financing-facility-presets")
def financing_facility_presets():
    """Return editable suggested models for the financing-plan UI."""
    return jsonify(data=list(FACILITY_PRESETS)), 200


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


def _restore_created_curve_nulls(cashflow, source):
    """Restore explicit nullable curve source fields after the INSERT flush.

    New scenarios with omitted fields still use the model's creation defaults.
    SQLAlchemy applies those INSERT defaults even to supplied Python None, so
    explicit legacy selector/skew nulls must be restored inside the transaction
    after insertion and before calculating or returning the scenario snapshot.
    """
    for field in (
        "use_independent_inflow_curve", "inflow_curve_type", "inflow_curve_skew",
    ):
        if field in source and source[field] is None:
            setattr(cashflow, field, None)
    db.session.flush()


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

    independent = getattr(cashflow, "use_independent_inflow_curve", None)
    InvalidData.require_condition(
        independent is None or isinstance(independent, bool),
        "Cashflow use_independent_inflow_curve must be boolean or null",
    )

    curve_type = getattr(cashflow, "inflow_curve_type", None)
    InvalidData.require_condition(
        curve_type is None or curve_type in {"s_curve", "linear"},
        "Cashflow inflow_curve_type must be s_curve, linear, or null",
    )

    skew = getattr(cashflow, "inflow_curve_skew", None)
    if skew is not None:
        InvalidData.require_condition(
            _finite_number(skew) and -1 < skew < 1,
            "Cashflow inflow_curve_skew must be finite and between -1 and 1",
        )

    facility_errors = validate_financing_facilities(
        getattr(cashflow, "financing_facilities", None) or []
    )
    InvalidData.require_condition(
        not facility_errors,
        "; ".join(facility_errors),
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


def _optional_text(data, key, label, *, allow_null=False):
    if key not in data:
        return
    if allow_null and data[key] is None:
        return
    InvalidData.require_condition(
        isinstance(data[key], str),
        f"{label} must be text",
    )


def _read_import_payload(data):
    InvalidData.require_condition(
        isinstance(data, dict), "Invalid cashflow import payload")
    InvalidData.require_condition(
        data.get("format") == PORTABLE_FORMAT,
        "Unsupported cashflow file format",
    )
    InvalidData.require_condition(
        data.get("version") == PORTABLE_VERSION,
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


def _normalized_facilities(cashflow: Cashflow, *, persist: bool = False):
    facilities, changed = normalize_facility_ids(
        cashflow.financing_facilities or []
    )
    if changed:
        cashflow.financing_facilities = facilities
        if persist:
            try:
                db.session.commit()
            except Exception:
                db.session.rollback()
                raise
    return facilities


def _finalize_facility_mutation(cashflow: Cashflow, facilities, user_id: str):
    cashflow.financing_facilities = facilities
    cashflow.updated_by = user_id
    cashflow.updated_at = func.now()
    try:
        _validate_cashflow(cashflow)
        db.session.flush()
        snapshot = cashflow.as_dict_with_activities()
        db.session.commit()
        return snapshot
    except Exception:
        db.session.rollback()
        raise


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
        if "financing_facilities" in data:
            supplied_facilities = data["financing_facilities"]
            cashflow.financing_facilities = new_facilities_with_defaults(
                [] if supplied_facilities is None else supplied_facilities
            )
        _validate_cashflow(cashflow)
        db.session.flush()
        _restore_created_curve_nulls(cashflow, data)
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
    _optional_text(cashflow_data, "description", "Cashflow description", allow_null=True)

    user_id = user.get("user_id")
    cashflow = Cashflow().from_dict(
        _filtered(cashflow_data, CASHFLOW_SOURCE_FIELDS),
        user_id,
    )
    cashflow.unit_id = unit_id
    cashflow.is_deleted = False
    db.session.add(cashflow)

    try:
        _set_scalar_defaults(cashflow)
        if "financing_facilities" in cashflow_data:
            supplied_facilities = cashflow_data["financing_facilities"]
            cashflow.financing_facilities = new_facilities_with_defaults(
                [] if supplied_facilities is None else supplied_facilities
            )
        _validate_cashflow(cashflow)

        for row in activity_rows:
            InvalidData.require_condition(
                isinstance(row, dict),
                "Each imported activity must be an object",
            )
            _require_text(row, "name", "Activity name")
            # Real portable exports preserve legacy nullable strings. Existing
            # activity normalization below already handles these source nulls.
            _optional_text(row, "activity_type", "Activity type", allow_null=True)
            _optional_text(row, "activity_mode", "Activity mode", allow_null=True)
            _optional_text(row, "distribution_type", "Activity distribution type", allow_null=True)
            _optional_text(row, "duration_units", "Activity duration units", allow_null=True)

            raw_mode = row.get("activity_mode") or "work"
            raw_distribution = row.get("distribution_type")
            uses_schedule = (
                raw_mode == "scheduled_cost" or raw_distribution == "manual"
            )
            if not uses_schedule:
                MissingData.require_condition(
                    "cost" in row and "duration" in row,
                    "Missing activity cost or duration",
                )

            activity_data = _filtered(row, ACTIVITY_SOURCE_FIELDS)
            activity = Activity().from_dict(activity_data, user_id)
            activity.cashflow_id = cashflow.id
            activity.is_deleted = False

            # Normalize before scalar defaults so old version-1 rows with
            # activity_type='linear' retain their legacy linear behavior.
            normalize_activity(activity)
            _set_activity_scalar_defaults(activity)
            if (
                effective_distribution_type(activity) == "s_curve"
                and ("skew" not in activity_data or activity.skew is None)
            ):
                activity.skew = ActivityType.skew_by_code(activity.activity_type)
            _validate_activity(activity)
            _set_cached_cashflow(activity)
            db.session.add(activity)

        db.session.flush()
        _restore_created_curve_nulls(cashflow, cashflow_data)
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


@cashflows.route("/cashflow/<cashflow_id>/export")
@auth_required
def export_cashflow(user, cashflow_id):
    cashflow = _active_cashflow(cashflow_id)
    error = _permission(user, cashflow, VIEW_CASHFLOW)
    if error:
        return error
    return jsonify(build_portable_cashflow(cashflow)), 200


@cashflows.route("/cashflow/<cashflow_id>/facilities", methods=["GET"])
@auth_required
def list_financing_facilities(user, cashflow_id):
    cashflow = _active_cashflow(cashflow_id)
    error = _permission(user, cashflow, VIEW_CASHFLOW)
    if error:
        return error
    return jsonify(data=_normalized_facilities(cashflow, persist=True)), 200


@cashflows.route(
    "/cashflow/<cashflow_id>/facilities/<facility_id>", methods=["GET"]
)
@auth_required
def get_financing_facility(user, cashflow_id, facility_id):
    cashflow = _active_cashflow(cashflow_id)
    error = _permission(user, cashflow, VIEW_CASHFLOW)
    if error:
        return error
    facilities = _normalized_facilities(cashflow, persist=True)
    return jsonify(data=get_facility(facilities, facility_id)), 200


@cashflows.route("/cashflow/<cashflow_id>/facilities", methods=["POST"])
@auth_required
def create_financing_facility(user, cashflow_id):
    cashflow = _active_cashflow(cashflow_id)
    error = _permission(user, cashflow, EDIT_CASHFLOW)
    if error:
        return error
    facilities = _normalized_facilities(cashflow)
    next_facilities, facility = add_facility(
        facilities, read_data(request) or {}
    )
    snapshot = _finalize_facility_mutation(
        cashflow, next_facilities, user.get("user_id")
    )
    return jsonify(
        facility=facility,
        cashflow=snapshot,
        message="Financing facility created successfully",
    ), 201


@cashflows.route("/cashflow/<cashflow_id>/facilities/order", methods=["PUT"])
@auth_required
def reorder_financing_facilities(user, cashflow_id):
    cashflow = _active_cashflow(cashflow_id)
    error = _permission(user, cashflow, EDIT_CASHFLOW)
    if error:
        return error
    data = read_data(request) or {}
    next_facilities = set_facility_order(
        _normalized_facilities(cashflow), data.get("facility_ids")
    )
    snapshot = _finalize_facility_mutation(
        cashflow, next_facilities, user.get("user_id")
    )
    return jsonify(
        cashflow=snapshot,
        message="Financing facility order updated successfully",
    ), 200


@cashflows.route(
    "/cashflow/<cashflow_id>/facilities/<facility_id>", methods=["PUT"]
)
@auth_required
def update_financing_facility(user, cashflow_id, facility_id):
    cashflow = _active_cashflow(cashflow_id)
    error = _permission(user, cashflow, EDIT_CASHFLOW)
    if error:
        return error
    next_facilities, facility = update_facility(
        _normalized_facilities(cashflow),
        facility_id,
        read_data(request) or {},
    )
    snapshot = _finalize_facility_mutation(
        cashflow, next_facilities, user.get("user_id")
    )
    # Return the validated, persisted representation (the object may have been
    # normalized by future validators), while keeping the addressed ID stable.
    facility = get_facility(snapshot["financing_facilities"], facility_id)
    return jsonify(
        facility=facility,
        cashflow=snapshot,
        message="Financing facility updated successfully",
    ), 200


@cashflows.route(
    "/cashflow/<cashflow_id>/facilities/<facility_id>", methods=["DELETE"]
)
@auth_required
def remove_financing_facility(user, cashflow_id, facility_id):
    cashflow = _active_cashflow(cashflow_id)
    error = _permission(user, cashflow, EDIT_CASHFLOW)
    if error:
        return error
    next_facilities = delete_facility(
        _normalized_facilities(cashflow), facility_id
    )
    snapshot = _finalize_facility_mutation(
        cashflow, next_facilities, user.get("user_id")
    )
    return jsonify(
        cashflow=snapshot,
        message="Financing facility deleted successfully",
    ), 200


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
        synchronize_session=False
    )
    db.session.delete(cashflow)
    db.session.commit()
    return jsonify(message="Cashflow hard deleted successfully"), 200
