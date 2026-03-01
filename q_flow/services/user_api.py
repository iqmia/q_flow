# import logging
# from flask import Flask, current_app, g, jsonify
# import jwt
# import requests
# from requests.exceptions import ConnectionError, Timeout, HTTPError

# log = logging.getLogger(__name__)

# class U_Api_resp:
#     def __init__(self, status_code, message):
#         self.status_code = status_code
#         self.message = message
#         self.response = None

#     @property
#     def error(self):
#         return self.status_code >= 400

# class User_API:
#     def init_app(self, app: Flask):
#         self.app = app
#         self.url = app.config.get("USER_API_URL", "")
#         self.app_name = app.config.get("APP_NAME", "")
#         self.app_id = app.config.get("APP_ID", "")
#         self.public_key = app.config.get("PUBLIC_KEY", "")
#         self.algo = app.config.get("ALGO", "HS256")

#     def __init__(self):
#         self.url = ""
#         self.app_name = ""
#         self.app_id = ""
#         self.public_key = ""
#         self.algo = "HS256"

#     def url_of(self, route):
#         return f"{self.url}/{route}"

#     def post(self, route, data=None, files=None) -> U_Api_resp:
#         usr_resp = U_Api_resp(200, "Success")
#         try:
#             response = requests.post(
#                 self.url_of(route),
#                 json=data if not files else None,
#                 data=data if files else None,
#                 files=files,
#                 headers={'client-app-id': self.app_id},
#                 timeout=30
#             )
#             # response.raise_for_status()
#             usr_resp.status_code = response.status_code
#             usr_resp.message = response.json().get("message", "Success")
#             usr_resp.response = response
#         except ConnectionError:
#             usr_resp.status_code = 503
#             usr_resp.message = "Service Unavailable: Unable to connect to qAuth."
#         except Timeout:
#             usr_resp.status_code = 408
#             usr_resp.message = "Request Timeout: API took too long to respond."
#         except HTTPError as e:
#             usr_resp.status_code = e.response.status_code
#             usr_resp.message = f"HTTP Error: {e.response.text}"
#         except requests.RequestException as e:
#             usr_resp.status_code = 500
#             usr_resp.message = f"Request Exception: {str(e)}"
#         return usr_resp

#     def get(self, route, data=None) -> U_Api_resp:
#         usr_resp = U_Api_resp(200, "Success")
#         try:
#             response = requests.get(
#                 self.url_of(route),
#                 params=data,
#                 headers={'client-app-id': self.app_id},
#                 timeout=30
#             )
#             response.raise_for_status()
#             usr_resp.status_code = response.status_code
#             usr_resp.message = response.json().get("message", "Success")
#             usr_resp.response = response
#         except ConnectionError:
#             usr_resp.status_code = 503
#             usr_resp.message = "Service Unavailable: Unable to connect to qAuth."
#         except Timeout:
#             usr_resp.status_code = 408
#             usr_resp.message = "Request Timeout: API took too long to respond."
#         except HTTPError as e:
#             usr_resp.status_code = e.response.status_code
#             usr_resp.message = f"HTTP Error: {e.response.text}"
#         except requests.RequestException as e:
#             usr_resp.status_code = 500
#             usr_resp.message = f"Request Exception: {str(e)}"
#         return usr_resp

#     def verify_token(self, token: str) -> dict:
#         log.debug(f"Verifying token {token}")
#         log.debug(f"Algorithm: {self.algo}")

#         if current_app.config.get("TESTING"):
#             return {
#                 "email": "test@example.com",
#                 "name": "Test User",
#                 "role": "test",
#                 "user_id": "1",
#                 "client_app_id": self.app_id,
#                 "is_active": True
#             }
        
#         resp = {}
#         try:
#             decoded_token = jwt.decode(token, self.public_key, algorithms=[self.algo])
#             resp.update(decoded_token)
            
#             if resp.get("client_app_id") != self.app_id:
#                 return {"error": "Invalid Application"}
#         except jwt.ExpiredSignatureError:
#             log.warning("Token expired, attempting to refresh...")
#             refresh_resp = self.post("refresh_token", data={"refresh_token": token})
#             if refresh_resp.error:
#                 return {"error": refresh_resp.message}
#             new_token = refresh_resp.response.json().get("data", {}).get("token")
#             if not new_token:
#                 return {"error": "Token refresh failed"}
#             g.new_token = new_token
#             return self.verify_token(new_token)
#         except jwt.DecodeError:
#             return {"error": "Invalid Token: Cannot decode"}
#         except jwt.InvalidTokenError:
#             return {"error": "Invalid Token: Token is malformed or invalid"}
#         except ValueError:
#             return {"error": "Decoding Error: Wrong public key"}
#         except Exception as e:
#             log.error(f"Unexpected error during token verification: {str(e)}")
#             return {"error": f"Unexpected error: {str(e)}"}
        
#         if not resp.get("name"):
#             resp["name"] = resp.get("email", "").split("@")[0]
        
#         return resp

"""
User_API – QFlow adapter for QAuth (JWT-based client-app-id)

Drop-in replacement for the previous User_API.
- Keeps the same public API (init_app, get, post, verify_token) so other code remains unchanged.
- Sends `client-app-id` as a short‑lived JWT signed with APP_SECRET/APP_ALGO.
- Centralizes token refresh propagation via a per-app `after_request` hook registered in init_app.
- Adds stronger network/JSON error handling without raising unless you want to.

Required app.config keys:
    USER_API_URL  (str)  – Base URL to QAuth
    APP_NAME      (str)
    APP_ID        (str)
    PUBLIC_KEY    (str)  – QAuth public key for verifying user tokens
    ALGO          (str)  – Algo for verifying user tokens from QAuth (e.g., "RS256")
    APP_SECRET    (str)  – Secret used to sign the app token you send to QAuth
    APP_ALGO      (str)  – Algo to sign app token (e.g., "HS256")

Optional:
    TESTING       (bool) – When True, verify_token returns a test user
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import jwt
import requests
from flask import Flask, current_app, g
from requests.exceptions import ConnectionError, Timeout, HTTPError

log = logging.getLogger(__name__)


class U_Api_resp:
    def __init__(self, status_code: int, message: str, response: Optional[requests.Response] = None):
        self.status_code = status_code
        self.message = message
        self.response = response

    @property
    def error(self) -> bool:
        return self.status_code >= 400


class User_API:
    """QFlow's QAuth client with JWT `client-app-id` header and centralized refresh."""

    # ------------------------- Lifecycle ------------------------- #
    def __init__(self) -> None:
        self.app: Optional[Flask] = None
        self.url: str = ""
        self.app_name: str = ""
        self.app_id: str = ""
        self.public_key: str = ""
        self.algo: str = "HS256"
        self.app_secret: str = ""
        self.app_algo: str = "HS256"
        self._app_token_cache: Dict[str, Any] = {"value": None, "exp": 0}

    def init_app(self, app: Flask) -> None:
        self.app = app
        self.url = app.config.get("USER_API_URL", "")
        self.app_name = app.config.get("APP_NAME", "")
        self.app_id = app.config.get("APP_ID", "")
        self.public_key = app.config.get("PUBLIC_KEY", "")
        self.algo = app.config.get("ALGO", "HS256")
        self.app_secret = app.config.get("APP_SECRET", "")
        self.app_algo = app.config.get("APP_ALGO", "HS256")

        missing = [k for k, v in {
            "USER_API_URL": self.url,
            "APP_ID": self.app_id,
            "PUBLIC_KEY": self.public_key,
            "ALGO": self.algo,
            "APP_SECRET": self.app_secret,
            "APP_ALGO": self.app_algo,
        }.items() if not v]
        if missing:
            raise ValueError(f"Missing required configuration keys: {', '.join(missing)}")

        # Centralize refresh propagation (removes the need for create_app after_request)
        app.after_request(self._attach_refreshed_token)

    # ------------------------- Internals ------------------------- #
    def _attach_refreshed_token(self, response):
        """Attach a refreshed token into the JSON response body or header.
        The frontend should watch for `Authorization: Bearer <token>` or
        the `token` property in the JSON payload.
        """
        new = getattr(g, "new_token", None)
        if not new:
            return response

        # Always add Authorization header for universal handling
        try:
            response.headers["Authorization"] = f"Bearer {new}"
        except Exception:  # pragma: no cover – header set failures are rare
            pass

        # If response is JSON, also include token in body to keep current UX
        try:
            data = response.get_json(silent=True)
            if isinstance(data, dict):
                data["token"] = new
                response.set_data(current_app.response_class.response_class.dumps(data))
        except Exception:
            # Non-JSON or immutable body – header is already set
            pass
        return response

    def _build_url(self, route: str) -> str:
        return f"{self.url.rstrip('/')}/{route.lstrip('/')}"

    def _app_token(self) -> str:
        """Return a short-lived JWT for the `client-app-id` header.
        Uses a 9-minute cached token to minimize signing ops.
        """
        now = int(datetime.now(tz=timezone.utc).timestamp())
        cached = self._app_token_cache
        if cached["value"] and now < cached["exp"] - 30:  # 30s early refresh
            return cached["value"]
        payload = {
            "client_app_id": self.app_id,
            "iat": now,
            "exp": now + 9 * 60,  # 9 minutes
        }
        try:
            token = jwt.encode(payload, self.app_secret, algorithm=self.app_algo)
        except Exception as e:
            log.error(f"Error generating app token: {e}")
            raise
        cached.update({"value": token, "exp": payload["exp"]})
        return token

    def _extract_message(self, response: requests.Response) -> str:
        ctype = (response.headers.get("content-type") or "").lower()
        if "application/json" in ctype:
            try:
                js = response.json()
                return (js.get("message") or js.get("error") or "").strip() or response.reason
            except ValueError:
                return response.text or response.reason
        return response.text or response.reason

    def _headers(self, token: Optional[str] = None, unit_id: Optional[str] = None) -> Dict[str, str]:
        hdrs = {
            "client-app-id": self._app_token(),
        }
        if token:
            hdrs["Authorization"] = f"Bearer {token}"
        if unit_id:
            hdrs["unit-id"] = unit_id
        return hdrs

    # ------------------------- Public HTTP ------------------------- #
    def post(self, route: str, data: Optional[dict] = None, files: Optional[dict] = None,
            token: Optional[str] = None, unit_id: Optional[str] = None, timeout: int = 30) -> U_Api_resp:
        """Backward-compatible POST. Added optional token/unit_id/timeout without breaking callers."""
        url = self._build_url(route)
        try:
            resp = requests.post(
                url,
                json=data if not files else None,
                data=data if files else None,
                files=files,
                headers=self._headers(token=token, unit_id=unit_id),
                timeout=timeout,
            )
        except ConnectionError:
            return U_Api_resp(503, "Service Unavailable: Unable to connect to QAuth.")
        except Timeout:
            return U_Api_resp(408, "Request Timeout: QAuth took too long to respond.")
        except requests.RequestException as e:
            return U_Api_resp(500, f"Request Error: {e}")
        # Do not raise_for_status; we return status/content to caller unchanged
        msg = self._extract_message(resp)
        return U_Api_resp(resp.status_code, msg, resp)

    def get(self, route: str, data: Optional[dict] = None,
            token: Optional[str] = None, unit_id: Optional[str] = None, timeout: int = 30) -> U_Api_resp:
        url = self._build_url(route)
        try:
            resp = requests.get(
                url,
                params=data,
                headers=self._headers(token=token, unit_id=unit_id),
                timeout=timeout,
            )
        except ConnectionError:
            return U_Api_resp(503, "Service Unavailable: Unable to connect to QAuth.")
        except Timeout:
            return U_Api_resp(408, "Request Timeout: QAuth took too long to respond.")
        except requests.RequestException as e:
            return U_Api_resp(500, f"Request Error: {e}")
        msg = self._extract_message(resp)
        return U_Api_resp(resp.status_code, msg, resp)

    # ------------------------- Token Verification/Refresh ------------------------- #
    def verify_token(self, token: str) -> Dict[str, Any]:
        """Verify a user token with QAuth's PUBLIC_KEY/ALGO.
        If expired, try to refresh via `user/refresh_token` and stash new token in `g.new_token`.
        """
        if current_app.config.get("TESTING"):
            return {
                "email": "test@example.com",
                "name": "Test User",
                "role": "test",
                "user_id": "1",
                "client_app_id": self.app_id,
                "is_active": True,
                "exp": int(datetime.now(tz=timezone.utc).timestamp()) + 3600,
                "token": token,
            }

        if not token:
            return {"error": "Token not provided"}

        try:
            decoded = jwt.decode(token, self.public_key, algorithms=[self.algo], audience=self.app_id)
            # App binding safety check
            if decoded.get("client_app_id") != self.app_id:
                return {"error": "Invalid Application"}
            if not decoded.get("name") and decoded.get("email"):
                decoded["name"] = decoded["email"].split("@")[0]
            decoded["token"] = token
            return decoded
        except jwt.ExpiredSignatureError:
            log.warning("Token expired; attempting refresh")
            refresh = self.post("user/refresh_token", data={"refresh_token": token})
            if refresh.error:
                return {"error": refresh.message}
            try:
                new_tok = refresh.response.json().get("data", {}).get("token")
            except Exception:
                new_tok = None
            if not new_tok:
                return {"error": "Token refresh failed"}
            g.new_token = new_tok
            return self.verify_token(new_tok)
        except jwt.InvalidSignatureError:
            return {"error": "Invalid Token Signature"}
        except jwt.InvalidAudienceError:
            return {"error": "Invalid Audience: Token not meant for this app"}
        except jwt.DecodeError:
            return {"error": "Invalid Token: Cannot decode"}
        except jwt.InvalidTokenError as e:
            return {"error": f"Invalid Token: {e}"}
        except ValueError:
            return {"error": "Error Decoding Token: wrong public key"}
        except Exception as e:
            log.error(f"Unexpected verify_token error: {e}")
            return {"error": f"Unexpected error: {e}"}
