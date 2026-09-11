from logging import getLogger
from flask import Blueprint, jsonify, request
from q_flow.services.decorators import auth_required
from q_flow.services.user_api import U_Api_resp
from q_flow.extensions import u_api
from q_flow.services.utils import read_data

users = Blueprint('users', __name__)

log = getLogger(__name__)


def _token_user(token):
    user = u_api.verify_token(token)
    if user.get('error'):
        return user
    # Keep the Flutter login model compatible with QAuth's current `photo` claim.
    user['image'] = user.get('image') or user.get('photo') or ''
    return user

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
    resp: U_Api_resp = u_api.post('user/login', data=dict(email=email, password=password))
    if resp.error:
        log.info(f"User {email} login failed")
        return jsonify(
            dict(
                error=resp.error,
                message=resp.message,
            )), resp.status_code
    token = resp.response.json().get('data').get('token')
    user = _token_user(token)
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
        'user/register', data=dict(
            email=email,
            password=password,
            name=data.get('name'),
            platform=data.get('platform'),
        ))
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
        'user/verify', data=dict(email=email, verification_code=code))
    if resp.error:
        log.info(f"User {email} email verification failed")
        return jsonify(
            dict(
                error=resp.error,
                message=resp.message,
            )), resp.status_code
    token = resp.response.json().get('data').get('token')
    user = _token_user(token)
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
    resp: U_Api_resp = u_api.post('user/request_password_reset', data=dict(email=email))
    if resp.error:
        log.info(f"User {email} password recovery failed")
        return jsonify(
            dict(
                error=resp.error,
                message=resp.message,
        )), resp.status_code
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
        'user/reset_password', data=dict(
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
    resp: U_Api_resp = u_api.post('user/resend_verify_code', data=dict(email=email))
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
        'user/deactivate_user', data=dict(id=user.get('user_id')))
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

@users.route('/google_login', methods=['POST', 'PUT'])
def google_login():
    """Proxy a native Google token to QAuth, which performs verification."""
    log.info("User requested to login with Google")
    data = read_data(request)
    id_token_value = data.get('id_token') or data.get('idToken') or data.get('credential')
    access_token = data.get('access_token') or data.get('accessToken')
    if not id_token_value and not access_token:
        return jsonify(code='invalid_google_token', message='No Google token provided'), 400
    qauth_data = {
        'id_token': id_token_value,
        'access_token': access_token,
        'platform': data.get('platform'),
    }
    resp = u_api.post('user/tp_login/google', data=qauth_data)
    if resp.error:
        return jsonify(dict(error=resp.error, message=resp.message)), resp.status_code
    token = resp.response.json().get('data').get('token')
    user = _token_user(token)
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
