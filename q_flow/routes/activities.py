from os import path
from flask import Blueprint, current_app, jsonify, request, json
from q_flow.cashflow import Activity_cf
from q_flow.exceptions import MissingData, PermissionDenied, ProjectNotFound
from q_flow.models.activity import Activity, ActivityType
from q_flow.models.cashflow import Cashflow
from q_flow.services.decorators import auth_required
from q_flow.services.units import EDIT_CASHFLOW, VIEW_CASHFLOW, ensure_unit_permission
from q_flow.services.utils import check_required, read_data
from logging import getLogger

activities = Blueprint('activities', __name__)
log = getLogger(__name__)


def _permission_error(user, cashflow, permission):
    result = ensure_unit_permission(user, cashflow.unit_id, permission)
    return result if isinstance(result, tuple) else None


@activities.route('/activities', methods=['GET'])
def get_activities():
    return jsonify({'data': 'activities', 'message': 'test for roger'}), 200

@activities.route('/activities/types', methods=['GET'])
@auth_required
def get_activity_types(user):
    log.info(f"{user.get('name')} requested activity types")
    with open(path.join(current_app.static_folder, 'activity_types.json')) as file:
        activity_types = json.load(file)
    return jsonify(data=activity_types), 200

@activities.route('/new_activity/<cashflow_id>', methods=['POST'])
@auth_required
def new_activity(user, cashflow_id):
    log.info(f"{user.get('name')} requested to create a new activity")
    data = read_data(request)
    check_required(data, ['name', 'cost', 'duration'])
    cashflow = Cashflow.Identify(cashflow_id)
    ProjectNotFound.require_condition(cashflow, 'Cashflow not found')
    error = _permission_error(user, cashflow, EDIT_CASHFLOW)
    if error:
        return error
    activity = Activity()
    activity.cashflow_id = cashflow_id
    MissingData.require_condition(
        data.get('name') and data.get("cost"), 'Missing name or cost')
    activity.from_dict(data, user.get('user_id')).commit()
    if activity.skew == 0 or activity.skew == None:
        activity.skew = ActivityType.skew_by_code(activity.activity_type)
    Activity_cf(activity).set_cashflow()
    return jsonify(data=activity.as_dict(), message='Activity created successfully'), 201

@activities.route('/activity/<activity_id>', methods=['GET'])
@auth_required
def get_activity(user, activity_id):
    log.info(f"{user.get('name')} requested activity {activity_id}")
    activity = Activity.query.get(activity_id)
    PermissionDenied.require_condition(
        activity and not activity.is_deleted, 'Activity not found')
    error = _permission_error(user, activity.cashflow, VIEW_CASHFLOW)
    if error:
        return error
    return jsonify(data=activity.as_dict(), message='Activity retrieved successfully'), 200

@activities.route('/update_activity/<activity_id>', methods=['PUT'])
@auth_required
def update_activity(user, activity_id):
    log.info(f"{user.get('name')} requested to update activity {activity_id}")
    data = read_data(request)
    activity: Activity = Activity.query.get(activity_id)
    check_required(data, ['name', 'cost', 'duration'])
    PermissionDenied.require_condition(
        activity and not activity.is_deleted, 'Activity not found')
    error = _permission_error(user, activity.cashflow, EDIT_CASHFLOW)
    if error:
        return error
    activity.update(user.get('user_id'), **data)
    if activity.skew == 0 or activity.skew == None:
        activity.skew = ActivityType.skew_by_code(activity.activity_type)
    Activity_cf(activity).set_cashflow()
    activity.commit()
    return jsonify(data=activity.as_dict(), message='Activity updated successfully'), 200

@activities.route('/delete_activity/<activity_id>', methods=['DELETE'])
@auth_required
def delete_activity(user, activity_id):
    log.info(f"{user.get('name')} requested to delete activity {activity_id}")
    activity = Activity.query.get(activity_id)
    PermissionDenied.require_condition(
        activity and not activity.is_deleted, 'Activity not found')
    error = _permission_error(user, activity.cashflow, EDIT_CASHFLOW)
    if error:
        return error
    activity.delete()
    return jsonify(message='Activity deleted successfully'), 200

@activities.route('/hard_delete_activity/<activity_id>', methods=['DELETE'])
@auth_required
def hard_delete_activity(user, activity_id):
    log.info(f"{user.get('name')} requested to hard delete activity {activity_id}")
    activity = Activity.query.get(activity_id)
    PermissionDenied.require_condition(activity, 'Activity not found')
    error = _permission_error(user, activity.cashflow, EDIT_CASHFLOW)
    if error:
        return error
    activity.hard_delete()
    return jsonify(message='Activity hard deleted successfully'), 200

@activities.route('/restore_activity/<activity_id>', methods=['PUT'])
@auth_required
def restore_activity(user, activity_id):
    log.info(f"{user.get('name')} requested to restore activity {activity_id}")
    activity = Activity.query.get(activity_id)
    PermissionDenied.require_condition(activity, 'Activity not found')
    error = _permission_error(user, activity.cashflow, EDIT_CASHFLOW)
    if error:
        return error
    activity.is_deleted = False
    activity.commit()
    return jsonify(message='Activity restored successfully'), 200

@activities.route('/restore_activities', methods=['PUT'])
@auth_required
def restore_activities(user):
    
    data = read_data(request)
    actList = data.get("data")
    log.info(f"{user.get('name')} requested to restore activities {actList}")
    activities = Activity.query.filter(Activity.id.in_(actList)).all()
    for cashflow in {activity.cashflow for activity in activities}:
        error = _permission_error(user, cashflow, EDIT_CASHFLOW)
        if error:
            return error
    for activity in activities:
        activity.is_deleted = False
        activity.commit()
    return jsonify(message='Activities restored successfully'), 200


@activities.route('/deleted_activities/<cashflow_id>', methods=['GET'])
@auth_required
def get_deleted_activities(user, cashflow_id):
    log.info(f"{user.get('name')} requested deleted activities for cashflow {cashflow_id}")
    cashflow = Cashflow.Identify(cashflow_id)
    ProjectNotFound.require_condition(cashflow, 'Cashflow not found')
    error = _permission_error(user, cashflow, VIEW_CASHFLOW)
    if error:
        return error
    activities = Activity.query.filter_by(cashflow_id=cashflow_id, is_deleted=True).all()
    return jsonify(data=[activity.as_dict() for activity in activities]), 200
