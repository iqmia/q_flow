from flask import current_app, request, jsonify
from functools import wraps
from q_flow.exceptions import PermissionDenied, TokenNotFound
from q_flow.extensions import u_api


# user is a dict with user data in the following format:
# {
#     "user_id": str,
#     "name": str,
#     "email": str,
#     "role": str,
#     "is_active": bool,
#     "client_app_id": str
# }
def auth_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs) -> dict:
        print("Auth decorator started")
        token = request.headers.get("Authorization")
        TokenNotFound.require_condition(
            token and token.startswith("Bearer "), "Missing Authorization header (Token)")
        token = token.split(" ")[1]
        user = u_api.verify_token(token)
        if user.get("error"):
            return jsonify(
                code=user.get("code", "reauth_required"),
                message=user.get("error"),
            ), 401
        PermissionDenied.require_condition(user.get("is_active"), "User is not active")
        PermissionDenied.require_condition(
            user.get("app_user_active", True), "User is not active for this app")
        print("auth decorator passed")
        return f(user, *args, **kwargs)
    return decorated_function
