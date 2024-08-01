import json
from flask import Blueprint, current_app, jsonify, request
from google.auth.transport import requests
from google.oauth2 import id_token
from matplotlib.font_manager import json_dump
from q_flow.services.user_api import U_Api_resp
from q_flow.extensions import u_api
from q_flow.services.utils import read_data

users = Blueprint('users', __name__)


@users.route('/api', methods=['GET'])
def api():
    return jsonify(
        dict(
            message='Welcome to the Q-Flow API',
        )), 200
    
@users.route('/login', methods=['POST'])
def login():
    data = read_data(request)
    email = data.get('email')
    password = data.get('password')
    print(data)
    resp: U_Api_resp = u_api.post('login', data=dict(email=email, password=password))
    if resp.error:
        return jsonify(
            dict(
                error=resp.error,
                message=resp.message,
            )), resp.status_code
    token = resp.response.json().get('data').get('token')
    user = u_api.verify_token(token)
    return jsonify(
        dict(
            message='Login successful',
            data={'token': token, 'user': user},
        )), 200

@users.route('/register', methods=['POST'])
def register():
    data = read_data(request)
    email = data.get('email')
    password = data.get('password')
    resp: U_Api_resp = u_api.post(
        'register', data=dict(email=email, password=password))
    if resp.error:
        return jsonify(
            dict(
                error=resp.error,
                message=resp.message,
            )), resp.status_code
    return jsonify(
        dict(
            message='Registration successful, please verify your email address',
        )), 201

@users.route('/verify_email', methods=['POST'])
def verify_email():
    data = read_data(request)
    email = data.get('email')
    code = data.get('code')
    resp: U_Api_resp = u_api.post(
        'verify', data=dict(email=email, verification_code=code))
    token = resp.response.json().get('data').get('token')
    user = u_api.verify_token(token)
    return jsonify(
        dict(
            message=resp.message,
            data = {'token': token, 'user': user},
        )), resp.status_code

@users.route('/resend_reset_code', methods=['POST'])
@users.route('/recover', methods=['POST'])
def recover():
    data = read_data(request)
    email = data.get('email')
    resp: U_Api_resp = u_api.post('request_password_reset', data=dict(email=email))
    return jsonify(
        dict(
            message=resp.message,
        )), resp.status_code

@users.route('/reset_password', methods=['POST'])
def reset_password():
    data = read_data(request)
    email = data.get('email')
    code = data.get('code')
    password = data.get('password')
    resp: U_Api_resp = u_api.post(
        'reset_password', data=dict(
            email=email, reset_code=code, new_password=password))
    return jsonify(
        dict(
            message=resp.message,
        )), resp.status_code

@users.route('/resend_verify_code', methods=['POST'])
def resend_verify_code():
    data = read_data(request)
    email = data.get('email')
    resp: U_Api_resp = u_api.post('resend_verify_code', data=dict(email=email))
    return jsonify(
        dict(
            message=resp.message,
        )), resp.status_code

@users.route('/google_login', methods=['PUT'])
def google_login():
    data = read_data(request)
    print(data)
    client_platform = data.get('platform')
    user_info = None
    if client_platform != 'web':
        code = data.get('code')
        audience = current_app.config['GOOGLE_CLIENT_ID']
        try:
            id_info = id_token.verify_oauth2_token(
                code, requests.Request(), audience=audience, clock_skew_in_seconds=1)
            print(id_info)
            user_info = dict(
                email=id_info.get('email'),
                name=id_info.get('name'),
                picture=id_info.get('picture')
            )
        except ValueError as e:
            return jsonify(dict(error='Invalid token', message=str(e))), 400
    else:
        user_info = data.get('user_info')
    resp =  u_api.post('oauth_login', data=dict(
        oauth='google', verify_email=False, user_info = json.dumps(user_info)
    ))
    token = resp.response.json().get('data').get('token')
    user = u_api.verify_token(token)
    return jsonify(
        dict(
            message=resp.message,
            data = {'token': token, 'user': user},
        )), resp.status_code

