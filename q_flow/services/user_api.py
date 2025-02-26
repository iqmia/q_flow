import logging
from flask import Flask, current_app
import jwt
import requests
from requests.exceptions import ConnectionError, Timeout, HTTPError

log = logging.getLogger(__name__)

class U_Api_resp:
    def __init__(self, status_code, message):
        self.status_code = status_code
        self.message = message
        self.response = None

    @property
    def error(self):
        return self.status_code >= 400

class User_API:
    def init_app(self, app: Flask):
        self.app = app
        self.url = app.config.get("USER_API_URL", "")
        self.app_name = app.config.get("APP_NAME", "")
        self.app_id = app.config.get("APP_ID", "")
        self.public_key = app.config.get("PUBLIC_KEY", "")
        self.algo = app.config.get("ALGO", "HS256")

    def __init__(self):
        self.url = ""
        self.app_name = ""
        self.app_id = ""
        self.public_key = ""
        self.algo = "HS256"

    def url_of(self, route):
        return f"{self.url}/{route}"

    def post(self, route, data=None, files=None) -> U_Api_resp:
        usr_resp = U_Api_resp(200, "Success")
        try:
            response = requests.post(
                self.url_of(route),
                json=data if not files else None,
                data=data if files else None,
                files=files,
                headers={'client-app-id': self.app_id},
                timeout=10
            )
            # response.raise_for_status()
            usr_resp.status_code = response.status_code
            usr_resp.message = response.json().get("message", "Success")
            usr_resp.response = response
        except ConnectionError:
            usr_resp.status_code = 503
            usr_resp.message = "Service Unavailable: Unable to connect to qAuth."
        except Timeout:
            usr_resp.status_code = 408
            usr_resp.message = "Request Timeout: API took too long to respond."
        except HTTPError as e:
            usr_resp.status_code = e.response.status_code
            usr_resp.message = f"HTTP Error: {e.response.text}"
        except requests.RequestException as e:
            usr_resp.status_code = 500
            usr_resp.message = f"Request Exception: {str(e)}"
        return usr_resp

    def get(self, route, data=None) -> U_Api_resp:
        usr_resp = U_Api_resp(200, "Success")
        try:
            response = requests.get(
                self.url_of(route),
                params=data,
                headers={'client-app-id': self.app_id},
                timeout=10
            )
            response.raise_for_status()
            usr_resp.status_code = response.status_code
            usr_resp.message = response.json().get("message", "Success")
            usr_resp.response = response
        except ConnectionError:
            usr_resp.status_code = 503
            usr_resp.message = "Service Unavailable: Unable to connect to qAuth."
        except Timeout:
            usr_resp.status_code = 408
            usr_resp.message = "Request Timeout: API took too long to respond."
        except HTTPError as e:
            usr_resp.status_code = e.response.status_code
            usr_resp.message = f"HTTP Error: {e.response.text}"
        except requests.RequestException as e:
            usr_resp.status_code = 500
            usr_resp.message = f"Request Exception: {str(e)}"
        return usr_resp

    def verify_token(self, token: str) -> dict:
        log.debug(f"Verifying token {token}")
        log.debug(f"Algorithm: {self.algo}")

        if current_app.config.get("TESTING"):
            return {
                "email": "test@example.com",
                "name": "Test User",
                "role": "test",
                "user_id": "1",
                "client_app_id": self.app_id,
                "is_active": True
            }
        
        resp = {}
        try:
            decoded_token = jwt.decode(token, self.public_key, algorithms=[self.algo])
            resp.update(decoded_token)
            
            if resp.get("client_app_id") != self.app_id:
                return {"error": "Invalid Application"}
        except jwt.ExpiredSignatureError:
            log.warning("Token expired, attempting to refresh...")
            refresh_resp = self.post("refresh_token", data={"refresh_token": token})
            if refresh_resp.error:
                return {"error": refresh_resp.message}
            new_token = refresh_resp.response.json().get("data", {}).get("token")
            return self.verify_token(new_token)
        except jwt.DecodeError:
            return {"error": "Invalid Token: Cannot decode"}
        except jwt.InvalidTokenError:
            return {"error": "Invalid Token: Token is malformed or invalid"}
        except ValueError:
            return {"error": "Decoding Error: Wrong public key"}
        except Exception as e:
            log.error(f"Unexpected error during token verification: {str(e)}")
            return {"error": f"Unexpected error: {str(e)}"}
        
        if not resp.get("name"):
            resp["name"] = resp.get("email", "").split("@")[0]
        
        return resp
