from logging import getLogger
from flask import Blueprint, current_app, jsonify, request
from google.auth.transport import requests as g_requests
from google.oauth2 import id_token
import requests
from q_flow.exceptions import InvalidCredentials
from q_flow.services.decorators import auth_required
from q_flow.services.user_api import U_Api_resp
from q_flow.extensions import u_api
from q_flow.services.utils import read_data

users = Blueprint('users', __name__)

log = getLogger(__name__)

@users.route('/api', methods=['GET'])
def api():
    return jsonify(
        dict(
            message='Welcome to the Q-Flow API',
        )), 200

@users.route('/user', methods=['GET'])
def get_user_by_token():
    data = read_data(request)
    token = data.get('token')
    user = u_api.verify_token(token)
    if user.get('error'):
        return jsonify(
            dict(
                error=user.get('error'),
                message=user.get('error'),
            )), 401
    return jsonify(
        dict(
            data=user,
        )), 200

@users.route('/login', methods=['POST'])
def login():
    data = read_data(request)
    email = data.get('email')
    password = data.get('password')
    log.info(f"User {email} requested to login")
    resp: U_Api_resp = u_api.post('login', data=dict(email=email, password=password))
    if resp.error:
        log.info(f"User {email} login failed")
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
    log.info(f"User {email} requested to register")
    resp: U_Api_resp = u_api.post(
        'register', data=dict(email=email, password=password))
    if resp.error:
        log.info(f"User {email} registration failed")
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
    log.info(f"User {email} requested to verify email")
    resp: U_Api_resp = u_api.post(
        'verify', data=dict(email=email, verification_code=code))
    if resp.error:
        log.info(f"User {email} email verification failed")
        return jsonify(
            dict(
                error=resp.error,
                message=resp.message,
            )), resp.status_code
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
    log.info(f"User {email} requested to recover password")
    resp: U_Api_resp = u_api.post('request_password_reset', data=dict(email=email))
    if resp.error:
        log.info(f"User {email} password recovery failed")
        return jsonify(
            dict(
                error=resp.error,
                message=resp.message,
            )), resp
    return jsonify(
        dict(
            message=resp.message,
        )), resp.status_code

@users.route('/reset_password', methods=['POST'])
def reset_password():
    data = read_data(request)
    email = data.get('email')
    log.info(f"User {email} requested to reset password")
    code = data.get('code')
    password = data.get('password')
    resp: U_Api_resp = u_api.post(
        'reset_password', data=dict(
            email=email, reset_code=code, new_password=password))
    if resp.error:
        log.info(f"User {email} password reset failed")
        return jsonify(
            dict(
                error=resp.error,
                message=resp.message,
            )), resp.status_code
    return jsonify(
        dict(
            message=resp.message,
        )), resp.status_code

@users.route('/resend_verify_code', methods=['POST'])
def resend_verify_code():
    data = read_data(request)
    email = data.get('email')
    log.info(f"User {email} requested to resend verification code")
    resp: U_Api_resp = u_api.post('resend_verify_code', data=dict(email=email))
    if resp.error:
        log.info(f"User {email} resend verification code failed")
        return jsonify(
            dict(
                error=resp.error,
                message=resp.message,
            )), resp.status_code
    return jsonify(
        dict(
            message=resp.message,
        )), resp.status_code

@users.route('/delete_account', methods=['POST'])
@users.route('/deactivate_account', methods=['POST'])
@auth_required
def deactivate_account(user):
    log.info(f"User {user.get('name')} requested to deactivate account")
    resp: U_Api_resp = u_api.post(
        'deactivate_user', data=dict(id=user.get('user_id')))
    if resp.error:
        log.info(f"User {user.get('name')} account deactivation failed")
        return jsonify(
            dict(
                error=resp.error,
                message=resp.message,
            )), resp.status_code
    return jsonify(
        dict(
            message=resp.message,
        )), resp.status_code

@users.route('/google_login', methods=['PUT'])
def google_login():
    log.info("User requested to login with google")
    data = read_data(request)
    client_platform = data.get('platform')
    user_info = None
    idToken = data.get('idToken')
    access_token = data.get('accessToken')
    audience = current_app.config['GOOGLE_CLIENT_ID']
    front_end_user_info = data.get('user_info')
    log.info(f"user trying to login with google on {client_platform}")
    try:
        if idToken:
            id_info = id_token.verify_oauth2_token(
                idToken, g_requests.Request(), audience=audience, clock_skew_in_seconds=1)
        elif access_token:
            id_info = requests.get(
                f"https://www.googleapis.com/oauth2/v3/userinfo?access_token={access_token}"
            ).json()
        else:
            return jsonify(dict(error='Invalid token', message='No token provided')), 400
        InvalidCredentials.require_condition(
            id_info.get('email'), "Invalid email from google token")
        user_info = {
                'email': id_info.get('email', front_end_user_info.get('email')),
                'name': id_info.get('name', front_end_user_info.get('name')),
                'picture': id_info.get('picture', front_end_user_info.get('picture'))
            }
    except ValueError as e:
        return jsonify(dict(error='Invalid token', message=str(e))), 400

    resp =  u_api.post(
        'oauth_login', 
        data={'oauth':'google', 'verify_email': False,  'user_info': user_info}
        )
    if resp.error:
        return jsonify(dict(error=resp.error, message=resp.message)), resp.status_code
    token = resp.response.json().get('data').get('token')
    user = u_api.verify_token(token)
    log.info(f"User {user.get('name')} logged in with google")
    return jsonify(
        dict(message=resp.message,
            data = {'token': token, 'user': user},)), resp.status_code

@users.route('/callback/google', methods=['POST'])
def google_callback():
    print("callback from google")
    data = read_data(request)
    print(data)
    return jsonify(dict(message='Google callback received')), 200