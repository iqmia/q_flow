import logging
import os
from flask import Blueprint, jsonify, request, send_file
from werkzeug.datastructures import FileStorage
from q_flow.exceptions import MissingData, PermissionDenied, ProjectNotDeleted, ProjectNotFound
from q_flow.models.project import Project
from q_flow.services.decorators import auth_required
from q_flow.services.utils import read_data, rnd_color
from q_flow.extensions import fs

projects = Blueprint('projects', __name__)

log = logging.getLogger(__name__)

@projects.route('/api', methods=['GET'])
def api():
    return jsonify(
        dict(
            message='Welcome to the Q-Flow API',
        )), 200

@projects.route('/projects')
@auth_required
def get_projects(user):
    log.info(f'User {user.get("name")} requested projects')
    data = read_data(request)
    page = data.get('page', 1, int)
    per_page = data.get('per_page', 10, int)
    projects = Project.query.filter_by(created_by=user.get('user_id'), is_deleted=False
        ).order_by(Project.updated_at.desc()
        ).paginate(page=page, per_page=per_page, error_out=False)
    return jsonify(data=[p.as_dict_with_activities() for p in projects.items], pages=projects.pages ), 200

@projects.route('/new_project', methods=['POST'])
@auth_required
def new_project(user):
    log.info(f'User {user.get("name")} requested to create a new project')
    data = read_data(request)
    photo: FileStorage = request.files.get('photo')
    MissingData.require_condition(data.get('name'), 'Missing name')
    project = Project().from_dict(data, user.get('user_id'))
    project.photo = fs.save_project_photo(photo, project)
    project.color = rnd_color()
    project.commit()
    return jsonify(
        data=project.as_dict(),
        message='Project created successfully'), 201

@projects.route('/project/<project_id>')
@auth_required
def get_project(user, project_id):
    log.info(f'User {user.get("name")} requested project {project_id}')
    project: Project = Project.query.get(project_id)
    ProjectNotFound.require_condition(project and not project.is_deleted, 'Project not found')
    PermissionDenied.require_condition(
        project.created_by == user.get('user_id'), f'Permission denied for user {user.get("name")}')
    return jsonify(data=project.as_dict_with_activities()), 200

@projects.route('/delete_project/<project_id>', methods=['DELETE'])
@auth_required
def delete_project(user, project_id):
    log.info(f'User {user.get("name")} requested to delete project {project_id}')
    project: Project = Project.query.get(project_id)
    ProjectNotFound.require_condition(project and not project.is_deleted, 'Project not found')
    PermissionDenied.require_condition(
        project.created_by == user.get('user_id'), f'Permission denied for user {user.get("name")}')
    project.delete()
    return jsonify(message='Project deleted successfully'), 200

@projects.route('/hard_delete_project/<project_id>', methods=['DELETE'])
@auth_required
def hard_delete_project(user, project_id):
    log.info(f'User {user.get("name")} requested to hard delete project {project_id}')
    project: Project = Project.query.get(project_id)
    ProjectNotFound.require_condition(project and not project.is_deleted, 'Project not found')
    PermissionDenied.require_condition(
        project.created_by == user.get('user_id'), f'Permission denied for user {user.get("name")}')
    project.hard_delete()
    return jsonify(message='Project hard deleted successfully'), 200

@projects.route('/update_project/<project_id>', methods=['PUT'])
@auth_required
def update_project(user, project_id):
    log.info(f'User {user.get("name")} requested to update project {project_id}')
    project: Project = Project.query.get(project_id)
    ProjectNotFound.require_condition(project and not project.is_deleted, 'Project not found')
    PermissionDenied.require_condition(
        project.created_by == user.get('user_id'), f'Permission denied for user {user.get("name")}')
    data = read_data(request)
    project.update(user.get("id"), **data)
    project.photo = fs.save_project_photo(request.files.get('photo'), project)
    return jsonify(data=project.as_dict_with_activities(), message='Project updated successfully'), 200

@projects.route('/restore_project/<project_id>', methods=['PUT'])
@auth_required
def restore_project(user, project_id):
    log.info(f'User {user.get("name")} requested to restore project {project_id}')
    project: Project = Project.query.get(project_id)
    ProjectNotFound.require_condition(project, 'Project not found')
    ProjectNotDeleted.require_condition(project.is_deleted, 'Project is not deleted')
    PermissionDenied.require_condition(
        project.created_by == user.get('user_id'), f'Permission denied for user {user.get("name")}')
    project.is_deleted = False
    project.commit()
    return jsonify(message='Project restored successfully'), 200

@projects.route('/photo/<photo>', methods=['GET'])
def get_photo(photo):
    return send_file(os.path.join(fs.project_photos, photo))
