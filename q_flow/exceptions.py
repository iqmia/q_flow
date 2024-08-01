from flask_buzz import FlaskBuzz

class Q_ERROR(FlaskBuzz):
    '''
    Uses FlaskBuzz to handle errors
    '''
    status_code = 400

class PermissionDenied(Q_ERROR):
    status_code = 403

class UserNotFound(Q_ERROR):
    status_code = 404

class UserExists(Q_ERROR):
    status_code = 400

class InvalidCredentials(Q_ERROR):
    status_code = 401

class InvalidEmail(Q_ERROR):
    status_code = 400

class ClientAppNotFound(Q_ERROR):
    status_code = 404

class ClientAppExists(Q_ERROR):
    status_code = 400

class InvalidClientApp(Q_ERROR):
    status_code = 401

class InvalidToken(Q_ERROR):
    status_code = 401

class TokenExpired(Q_ERROR):
    status_code = 401

class TokenNotFound(Q_ERROR):
    status_code = 403

class AppNotActive(Q_ERROR):
    status_code = 401

class UserNotActive(Q_ERROR):
    status_code = 401

class MissingData(Q_ERROR):
    status_code = 400

class InvalidData(Q_ERROR):
    status_code = 400

class PhotoNotFound(Q_ERROR):
    status_code = 404

class EmailNotVerified(Q_ERROR):
    status_code = 401

class EmailAlreadyVerified(Q_ERROR):
    status_code = 400

class Keys_Not_Found(Q_ERROR):
    status_code = 404

class ENV_Not_Found(Q_ERROR):
    status_code = 404

class ProjectNotFound(Q_ERROR):
    status_code = 404

class ProjectNotDeleted(Q_ERROR):
    status_code = 400
