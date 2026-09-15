from unittest.mock import patch

import pytest

from q_flow import create_app
from q_flow.config import TestConfig
from q_flow.extensions import db
from q_flow.models.cashflow import Cashflow


@pytest.fixture
def app(tmp_path):
    class RouteConfig(TestConfig):
        STORAGE_PATH = str(tmp_path)

    app = create_app(RouteConfig)
    user = {
        "user_id": "owner-1",
        "name": "Owner",
        "is_active": True,
        "token": "user-token",
    }
    with patch("q_flow.services.decorators.u_api.verify_token", return_value=user):
        yield app
    with app.app_context():
        db.session.remove()
        db.drop_all()


def test_project_contract_value_seeds_base_cashflow_without_reaching_qauth(app):
    def create_unit(_api, **kwargs):
        return {
            "id": kwargs["project_id"],
            "name": kwargs["data"]["name"],
            "description": kwargs["data"].get("description", ""),
            "color": kwargs["data"]["color"],
        }

    with patch(
        "q_flow.routes.projects.create_project_unit",
        side_effect=create_unit,
    ) as create:
        response = app.test_client().post(
            "/new_project",
            headers={"Authorization": "Bearer user-token"},
            json={
                "name": "Tower",
                "description": "Residential",
                "contract_value": 2_500_000,
            },
        )

    assert response.status_code == 201
    assert "contract_value" not in create.call_args.kwargs["data"]

    with app.app_context():
        base = Cashflow.query.one()
        assert base.name == "Base Cashflow"
        assert base.contract_value == 2_500_000
