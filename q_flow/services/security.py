
from flask import current_app
import jwt
from q_flow.exceptions import InvalidToken, TokenExpired

def validate_token(token: str):
    '''
    Validate the token and return the payload if the token is valid
    '''
    try:
        payload = jwt.decode(
            token,
            current_app.config.get("SECRET_KEY"),
            current_app.config.get("ALGORITHM")
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise TokenExpired("Token has expired")
    except jwt.InvalidTokenError:
        raise InvalidToken("Invalid token")