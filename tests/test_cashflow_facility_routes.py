from unittest.mock import Mock, patch

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


def _auth():
    return {"Authorization": "Bearer user-token"}


def _permission():
    return Mock(return_value={"user_id": "owner-1", "unit_id": "unit-1"})


def _base_facility(name="OD", facility_id=None):
    value = {
        "name": name,
        "type": "Overdraft",
        "draw_method": "automatic_shortfall",
        "repayment_method": "cashflow_sweep",
        "limit": 100,
        "interest_rate": 0,
        "fees": 0,
        "revolving": True,
        "start": 0,
        "sweep_priority": 0,
    }
    if facility_id is not None:
        value["id"] = facility_id
    return value


def _cashflow_payload(facilities=None):
    return {
        "format": "cashflowpot.cashflow",
        "version": 1,
        "cashflow": {
            "name": "Facility test",
            "contract_value": 100,
            "advance": 0,
            "retention": 0,
            "release_retention_eop": 0.5,
            "dlp": 0,
            "duration_for_payment": 0,
            "interest_rate": 0,
            "wieb": 0,
            "use_independent_inflow_curve": True,
            "inflow_curve_type": "linear",
            "inflow_curve_skew": 0,
            "financing_facilities": facilities or [],
            "activities": [
                {
                    "name": "Work",
                    "activity_type": "General",
                    "activity_mode": "work",
                    "distribution_type": "linear",
                    "cost": 100,
                    "duration": 2,
                    "duration_units": "Periods",
                    "start": 0,
                    "advance": 0,
                    "retention": 0,
                    "release_retention_eop": 0.5,
                    "dlp": 0,
                    "duration_for_payment": 0,
                    "work_in_excess": 0,
                    "mobilization_period": 0,
                    "subcontracted": 0,
                    "skew": 0,
                    "no_billing_period": 0,
                }
            ],
        },
    }


def _create(app, facilities=None):
    with patch("q_flow.routes.cashflows.ensure_unit_permission", _permission()):
        response = app.test_client().post(
            "/project/unit-1/cashflows/import",
            headers=_auth(),
            json=_cashflow_payload(facilities),
        )
    assert response.status_code == 201, response.get_json()
    return response.get_json()["data"]


def _request(app, method, path, json=None):
    with patch("q_flow.routes.cashflows.ensure_unit_permission", _permission()):
        return app.test_client().open(path, method=method, headers=_auth(), json=json)


def test_list_normalizes_legacy_facility_ids_and_persists_them(app):
    created = _create(app, [_base_facility()])

    response = _request(app, "GET", f"/cashflow/{created['id']}/facilities")

    assert response.status_code == 200
    facilities = response.get_json()["data"]
    assert len(facilities) == 1
    generated_id = facilities[0]["id"]
    assert isinstance(generated_id, str) and generated_id

    again = _request(app, "GET", f"/cashflow/{created['id']}/facilities")
    assert again.get_json()["data"][0]["id"] == generated_id
    with app.app_context():
        stored = db.session.get(Cashflow, created["id"])
        assert stored.financing_facilities[0]["id"] == generated_id


def test_add_get_update_and_delete_target_one_embedded_facility(app):
    created = _create(app)
    supplied = _base_facility("LC MEP", "facility-1")
    supplied.update({
        "type": "Working Capital",
        "draw_method": "scheduled",
        "draw_schedule": {"0": 50},
        "repayment_method": "scheduled",
        "repayment_schedule": {"1": 50},
        "revolving": False,
    })

    added = _request(
        app,
        "POST",
        f"/cashflow/{created['id']}/facilities",
        supplied,
    )
    assert added.status_code == 201, added.get_json()
    assert added.get_json()["facility"]["id"] == "facility-1"
    assert added.get_json()["cashflow"]["financing_facilities"][0]["name"] == "LC MEP"
    assert added.get_json()["cashflow"]["facility_rows"][0]["name"] == "LC MEP"

    fetched = _request(
        app,
        "GET",
        f"/cashflow/{created['id']}/facilities/facility-1",
    )
    assert fetched.status_code == 200
    assert fetched.get_json()["data"]["name"] == "LC MEP"

    updated = _request(
        app,
        "PUT",
        f"/cashflow/{created['id']}/facilities/facility-1",
        {"name": "LC Revised", "id": "attempted-new-id"},
    )
    assert updated.status_code == 200
    assert updated.get_json()["facility"]["id"] == "facility-1"
    assert updated.get_json()["facility"]["name"] == "LC Revised"

    deleted = _request(
        app,
        "DELETE",
        f"/cashflow/{created['id']}/facilities/facility-1",
    )
    assert deleted.status_code == 200
    assert deleted.get_json()["cashflow"]["financing_facilities"] == []
    assert deleted.get_json()["cashflow"]["facility_rows"] == []


def test_add_generates_id_and_rejects_duplicate_id_or_name_atomically(app):
    created = _create(app, [_base_facility("OD Existing", "od-existing")])

    generated = _request(
        app,
        "POST",
        f"/cashflow/{created['id']}/facilities",
        _base_facility("Second OD"),
    )
    assert generated.status_code == 201
    generated_id = generated.get_json()["facility"]["id"]
    assert generated_id and generated_id != "od-existing"

    duplicate_id = _request(
        app,
        "POST",
        f"/cashflow/{created['id']}/facilities",
        _base_facility("Different name", "od-existing"),
    )
    assert duplicate_id.status_code == 400

    duplicate_name = _request(
        app,
        "POST",
        f"/cashflow/{created['id']}/facilities",
        _base_facility("OD Existing", "other-id"),
    )
    assert duplicate_name.status_code == 400

    listed = _request(app, "GET", f"/cashflow/{created['id']}/facilities")
    assert [row["id"] for row in listed.get_json()["data"]] == [
        "od-existing",
        generated_id,
    ]


def test_invalid_update_rolls_back_complete_facility_list(app):
    created = _create(app, [_base_facility("OD", "od-1")])

    response = _request(
        app,
        "PUT",
        f"/cashflow/{created['id']}/facilities/od-1",
        {"draw_method": "not-a-method"},
    )
    assert response.status_code == 400

    with app.app_context():
        stored = db.session.get(Cashflow, created["id"])
        assert stored.financing_facilities[0]["draw_method"] == "automatic_shortfall"


def test_set_order_requires_every_id_once_and_updates_sweep_priority(app):
    facilities = [
        _base_facility("First", "f-1"),
        _base_facility("Second", "f-2"),
        _base_facility("Third", "f-3"),
    ]
    created = _create(app, facilities)

    reordered = _request(
        app,
        "PUT",
        f"/cashflow/{created['id']}/facilities/order",
        {"facility_ids": ["f-3", "f-1", "f-2"]},
    )
    assert reordered.status_code == 200
    saved = reordered.get_json()["cashflow"]["financing_facilities"]
    assert [row["id"] for row in saved] == ["f-3", "f-1", "f-2"]
    assert [row["sweep_priority"] for row in saved] == [0, 1, 2]

    invalid = _request(
        app,
        "PUT",
        f"/cashflow/{created['id']}/facilities/order",
        {"facility_ids": ["f-1", "f-1", "f-2"]},
    )
    assert invalid.status_code == 400

    listed = _request(app, "GET", f"/cashflow/{created['id']}/facilities")
    assert [row["id"] for row in listed.get_json()["data"]] == ["f-3", "f-1", "f-2"]
