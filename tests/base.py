
from shutil import rmtree
from unittest.mock import patch

from flask import jsonify
from flask_testing import TestCase
from q_flow import create_app
from q_flow.config import TestConfig
from q_flow.extensions import db, fs
from q_flow.models.project import Project
from q_flow.services.user_api import U_Api_resp


class _FakeHTTPResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code
        self.reason = payload.get("message", "")
        self.text = str(payload)
        self.headers = {"content-type": "application/json"}

    def json(self):
        return self._payload

class Base(TestCase):
    def create_app(self):
        print("setting up base test")

        app = create_app(TestConfig)
        print(TestConfig)
        return app

    def setUp(self):
        print("setting up creating db")
        self.app = self.create_app()
        self._units = {}
        self._qauth_patchers = [
            patch("q_flow.routes.projects.create_project_unit", side_effect=self._create_unit),
            patch("q_flow.routes.projects.load_project_unit", side_effect=self._load_unit),
            patch("q_flow.routes.projects.ensure_unit_permission", side_effect=self._permission),
            patch("q_flow.routes.activities.ensure_unit_permission", side_effect=self._permission),
            patch("q_flow.routes.projects.u_api.get", side_effect=self._qauth_get),
            patch("q_flow.routes.projects.u_api.post", side_effect=self._qauth_post),
        ]
        for patcher in self._qauth_patchers:
            patcher.start()

    @staticmethod
    def _unit(project, **overrides):
        unit = {
            "id": project.id,
            "name": project.name,
            "description": project.description,
            "color": project.color,
            "image_url": f"https://qauth.test/unit/image/{project.photo}" if project.photo else None,
        }
        unit.update(overrides)
        return unit

    def _create_unit(self, _api, **kwargs):
        data = kwargs["data"]
        image = kwargs.get("image")
        unit = {
            "id": kwargs["project_id"],
            "name": data.get("name"),
            "description": data.get("description") or "",
            "color": data.get("color"),
            "image_url": f"https://qauth.test/unit/image/{image.filename}" if image else None,
        }
        self._units[unit["id"]] = {**unit, "created_by": "1", "is_deleted": False}
        return unit

    def _find_unit(self, unit_id):
        unit = self._units.get(unit_id)
        if unit:
            return unit
        legacy = Project.query.get(unit_id)
        if legacy:
            return {**self._unit(legacy), "created_by": legacy.created_by,
                    "is_deleted": legacy.is_deleted}
        return None

    def _load_unit(self, user, unit_id):
        unit = self._find_unit(unit_id)
        if not unit:
            return None, (jsonify(message="Project not found"), 404)
        if unit["created_by"] != user.get("user_id"):
            return None, (jsonify(message="Permission denied"), 403)
        scoped = dict(user, unit_id=unit_id,
                      unit_permissions=["view:cashflow", "edit:cashflow"])
        return (scoped, unit), None

    def _permission(self, user, unit_id, _permission):
        unit = self._find_unit(unit_id)
        if unit and unit["created_by"] != user.get("user_id"):
            return jsonify(message="Permission denied"), 403
        return dict(user, unit_id=unit_id,
                    unit_permissions=["view:cashflow", "edit:cashflow"])

    def _qauth_get(self, route, data=None, **_kwargs):
        if route == "unit/units":
            page = int((data or {}).get("page", 1))
            per_page = int((data or {}).get("per_page", 10))
            units = [unit for unit in self._units.values()
                     if unit["created_by"] == "1" and not unit["is_deleted"]]
            legacy = Project.query.filter_by(
                created_by="1", unit_id=None, is_deleted=False).all()
            units.extend({**self._unit(project), "created_by": project.created_by,
                          "is_deleted": project.is_deleted} for project in legacy)
            start = (page - 1) * per_page
            items = units[start:start + per_page]
            pages = (len(units) + per_page - 1) // per_page
            payload = {"data": {
                "units_with_roles": [
                    {"unit": unit, "roles": ["creator"]} for unit in items
                ],
                "pages": pages,
            }}
            return U_Api_resp(200, "ok", _FakeHTTPResponse(payload))
        return U_Api_resp(404, "not found", _FakeHTTPResponse({"message": "not found"}, 404))

    def _qauth_post(self, route, data=None, files=None, unit_id=None, **_kwargs):
        if route in {"unit/activate", "unit/deactivate", "unit/delete"}:
            unit = self._find_unit(unit_id)
            if not unit:
                return U_Api_resp(404, "Project not found", _FakeHTTPResponse(
                    {"message": "Project not found"}, 404))
            if unit["created_by"] != "1":
                payload = {"code": "unit_access_denied", "message": "Permission denied"}
                return U_Api_resp(403, "Permission denied", _FakeHTTPResponse(payload, 403))
            if route == "unit/activate" and not unit["is_deleted"]:
                return U_Api_resp(400, "Project is not deleted", _FakeHTTPResponse(
                    {"message": "Project is not deleted"}, 400))
            if route == "unit/activate":
                unit["is_deleted"] = False
            elif route == "unit/deactivate":
                unit["is_deleted"] = True
            elif route == "unit/delete":
                self._units.pop(unit_id, None)
        if route == "unit/edit":
            current = self._find_unit(unit_id)
            if not current:
                return U_Api_resp(404, "Project not found", _FakeHTTPResponse(
                    {"message": "Project not found"}, 404))
            unit = dict(
                current,
                name=(data or {}).get("name", current["name"]),
                description=(data or {}).get("description", current["description"]),
                color=(data or {}).get("color", current["color"]),
                image_url=(f"https://qauth.test/unit/image/{files['image'][0]}" if files else None),
            )
            self._units[unit_id] = unit
            return U_Api_resp(200, "ok", _FakeHTTPResponse({"data": {"unit": unit}}))
        return U_Api_resp(200, "ok", _FakeHTTPResponse({"message": "ok"}))

    def tearDown(self):
        '''
        Clean up after each test
        '''
        # empty database
        db.session.remove()
        db.drop_all()

        # delete storage
        rmtree(fs.storage_dir, ignore_errors=True)
        for patcher in reversed(getattr(self, "_qauth_patchers", [])):
            patcher.stop()
