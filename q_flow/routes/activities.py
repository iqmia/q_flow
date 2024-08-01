from os import path
from flask import Blueprint, current_app, jsonify, request
from q_flow.cashflow import Activity_cf
from q_flow.exceptions import MissingData, PermissionDenied, ProjectNotFound
from q_flow.models.activity import Activity, ActivityType
from q_flow.models.project import Project
from q_flow.services.decorators import auth_required
from q_flow.services.utils import check_required, read_data
import json

activities = Blueprint('activities', __name__)

@activities.route('/activities', methods=['GET'])
def get_activities():
    return jsonify({'data': 'activities', 'message': 'test for roger'}), 200

@activities.route('/activities/types', methods=['GET'])
@auth_required
def get_activity_types(_):
    with open(path.join(current_app.static_folder, 'activity_types.json')) as file:
        activity_types = json.load(file)
    return jsonify(data=activity_types), 200

@activities.route('/new_activity/<project_id>', methods=['POST'])
@auth_required
def new_activity(user, project_id):
    data = read_data(request)
    check_required(data, ['name', 'cost', 'duration'])
    activity = Activity()
    activity.project_id = project_id
    MissingData.require_condition(
        data.get('name') and data.get("cost"), 'Missing name or cost')
    ProjectNotFound.require_condition(Project.Identify(project_id), 'Project not found')
    activity.from_dict(data, user.get('user_id')).commit()
    if activity.skew == 0 or activity.skew == None:
        activity.skew = ActivityType.skew_by_code(activity.activity_type)
    Activity_cf(activity).set_cashflow()
    return jsonify(data=activity.as_dict(), message='Activity created successfully'), 201

@activities.route('/activity/<activity_id>', methods=['GET'])
@auth_required
def get_activity(user, activity_id):
    activity = Activity.query.get(activity_id)
    PermissionDenied.require_condition(
        activity and not activity.is_deleted, 'Activity not found')
    PermissionDenied.require_condition(
        activity.project.created_by == user.get('user_id'), f'Permission denied for user {user.get("name")}')
    return jsonify(data=activity.as_dict(), message='Activity retrieved successfully'), 200

@activities.route('/update_activity/<activity_id>', methods=['PUT'])
@auth_required
def update_activity(user, activity_id):
    data = read_data(request)
    activity: Activity = Activity.query.get(activity_id)
    check_required(data, ['name', 'cost', 'duration'])
    PermissionDenied.require_condition(
        activity and not activity.is_deleted, 'Activity not found')
    PermissionDenied.require_condition(
        activity.project.created_by == user.get('user_id'), f'Permission denied for user {user.get("name")}')
    activity.update(user.get('id'), **data)
    if activity.skew == 0 or activity.skew == None:
        activity.skew = ActivityType.skew_by_code(activity.activity_type)
    Activity_cf(activity).set_cashflow()
    activity.commit()
    return jsonify(data=activity.as_dict(), message='Activity updated successfully'), 200

@activities.route('/delete_activity/<activity_id>', methods=['DELETE'])
@auth_required
def delete_activity(user, activity_id):
    activity = Activity.query.get(activity_id)
    PermissionDenied.require_condition(
        activity and not activity.is_deleted, 'Activity not found')
    PermissionDenied.require_condition(
        activity.project.created_by == user.get('user_id'), f'Permission denied for user {user.get("name")}')
    activity.delete()
    return jsonify(message='Activity deleted successfully'), 200

@activities.route('/hard_delete_activity/<activity_id>', methods=['DELETE'])
@auth_required
def hard_delete_activity(user, activity_id):
    activity = Activity.query.get(activity_id)
    PermissionDenied.require_condition(activity, 'Activity not found')
    PermissionDenied.require_condition(
        activity.project.created_by == user.get('user_id'), f'Permission denied for user {user.get("name")}')
    activity.hard_delete()
    return jsonify(message='Activity hard deleted successfully'), 200

@activities.route('/restore_activity/<activity_id>', methods=['PUT'])
@auth_required
def restore_activity(user, activity_id):
    activity = Activity.query.get(activity_id)
    PermissionDenied.require_condition(activity, 'Activity not found')
    activity.is_deleted = False
    activity.commit()
    return jsonify(message='Activity restored successfully'), 200

@activities.route('/restore_activities', methods=['PUT'])
@auth_required
def restore_activities(user):
    data = read_data(request)
    actList = data.get("data")
    activities = Activity.query.filter(Activity.id.in_(actList)).all()
    for activity in activities:
        if activity.created_by != user.get('user_id'):
            continue
        activity.is_deleted = False
        activity.commit()
    return jsonify(message='Activities restored successfully'), 200


@activities.route('/deleted_activities/<projectId>', methods=['GET'])
@auth_required
def get_deleted_activities(user, projectId):
    ProjectNotFound.require_condition(Project.Identify(projectId), 'Project not found')
    PermissionDenied.require_condition(
        Project.Identify(projectId).created_by == user.get('user_id'), f'Permission denied for user {user.get("name")}')
    activities = Activity.query.filter_by(project_id=projectId, is_deleted=True).all()
    return jsonify(data=[activity.as_dict() for activity in activities]), 200

