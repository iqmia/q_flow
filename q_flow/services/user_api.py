import logging
from flask import Flask, current_app
import jwt
import requests

log = logging.getLogger(__name__)

class U_Api_resp:
    def __init__(self, status_code, message):
        self.status_code = status_code
        self.message = message
        self.response = None

    @property
    def error(self):
        return self.status_code >= 301

class User_API:
    def init_app(self, app: Flask):
        self.app = app
        self.url = app.config.get("USER_API_URL")
        self.app_name = app.config.get("APP_NAME")
        self.app_id = app.config.get("APP_ID")
        self.public_key = app.config.get("PUBLIC_KEY")
        self.algo = app.config.get("ALGO")

    def __init__(self):

        self.url: str = ""
        self.app_name = ""
        self.app_id: str = ""
        self.public_key: str = ""
        self.algo: str = ""

    def url_of(self, route):
        return f"{self.url}/{route}"

    def post(self, route, data=None, files=None) -> U_Api_resp:
        usr_resp = U_Api_resp(200, "Success")
        print(self.url_of(route))
        try:
            response = requests.post(
                self.url_of(route),
                data=data,
                files=files,
                headers={
                    'client-app-id': self.app_id,})
        except requests.RequestException as e:
            usr_resp.status_code = 500
            usr_resp.message = str(e)
        except Exception as e:
            usr_resp.status_code = 500
            usr_resp.message = str(e)
        else:
            usr_resp.status_code = response.status_code
            if "application/json" in response.headers.get("content-type"):
                usr_resp.message = response.json().get("message")
            else:
                usr_resp.message = response.text
            usr_resp.response = response
        print(usr_resp.message)
        return usr_resp

    def get(self, route, data=None) -> U_Api_resp:
        url = self.url_of(route)
        usr_resp = U_Api_resp(200, "Success")
        try:
            response = requests.get(
                url=url,
                params=data,
                headers={'client-app-id': self.app_id},
            )
        except Exception as e:
            usr_resp.status_code = 500
            usr_resp.message = str(type(e).__name__)
        else:
            usr_resp.status_code = response.status_code
            if "application/json" in response.headers.get("content-type"):
                usr_resp.message = response.json().get("message")
            else:
                usr_resp.message = response.text
            usr_resp.response = response
        return usr_resp

    def verify_token(self, token: str) -> dict:
        '''
        decodes the token using the public key and returns the user info
        user: dict {
            email: str,
            name: str,
            role: str,
            user_id: str,
            client_app_id: str,
            is_active: bool
        }
        '''
        log.debug(f"Verifying token {token}")
        log.debug(f"algo: {self.algo}")
        if current_app.config.get("TESTING"):
            return {
                "email": "test@exampl.com",
                "name": "Test User",
                "role": "test",
                "user_id": '1',
                "client_app_id": self.app_id,
                "is_active": True
                }
        resp: dict = {}
        try:
            tokenDict = jwt.decode(
                token, self.public_key, algorithms=[self.algo])
            for key, value in tokenDict.items():
                resp[key] = value

            # check if client_app_id is the same as the app_id
            if resp.get("client_app_id") != self.app_id:
                resp["error"] = "Invalid Application"
        except jwt.ExpiredSignatureError:
            print("expiry error")
            resp = {"error": "Token Expired"}
        except jwt.InvalidTokenError as e:
            resp = {"error": f"Invalid Token {str(e)}"}
        except ValueError:
            resp = {"error": "Error Decoding Token, wrong public key"}
        except Exception as e:
            print(f"Error Decoding Token: {str(e.__class__.__name__)}")
            resp = {"error": f"Failed Decoding Token: {str(e.__class__.__name__)}"}
        if not resp.get("error"):
            if resp.get("name") is None or "":
                resp["name"] = resp.get("email").split("@")[0]
        return resp