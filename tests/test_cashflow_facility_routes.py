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


@pytest.mark.parametrize("field", ["start", "interest_rate", "fees"])
def test_explicit_null_scalar_facility_update_is_rejected_atomically(app, field):
    with app.app_context():
        Cashflow(id="null-cost", unit_id="unit-1", name="Costs", created_by="owner-1",
                 financing_facilities=[_base_facility(facility_id="od-1")]).commit()
    with patch("q_flow.routes.cashflows.ensure_unit_permission", _permission()):
        response = app.test_client().put(
            "/cashflow/null-cost/facilities/od-1", headers=_auth(), json={field: None},
        )
    assert response.status_code == 400
    with app.app_context():
        facility = db.session.get(Cashflow, "null-cost").financing_facilities[0]
        assert facility[field] == 0


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
    # Existing snapshots omit facility-only calculated rows when no facilities
    # remain, so absence and an empty row list are equivalent here.
    assert deleted.get_json()["cashflow"].get("facility_rows", []) == []


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


def test_catalog_explains_editable_illustrative_cost_defaults(app):
    response = app.test_client().get("/financing-facility-presets")
    assert response.status_code == 200
    presets = {row["key"]: row for row in response.get_json()["data"]}
    for key, preset in presets.items():
        assert preset["interest_rate"] == (
            0.0 if key in {"owners_injection", "other"} else 0.005
        )
        assert preset["fees"] == 0.0
        assert preset["default_fees_rate"] == (
            0.0 if key in {"owners_injection", "other"} else 0.005 / 12
        )
        assert preset["default_fees_basis"] == "limit_or_scheduled_draw_total"
        assert preset["interest_rate_basis"] == "per_period"
        assert preset["fees_basis"] == "fixed_amount"
        assert "illustrative" in preset["costs_note"].lower()
        assert "editable" in preset["costs_note"].lower()


@pytest.mark.parametrize("creation", ["add", "import", "new"])
@pytest.mark.parametrize("facility_type, expected_rate", [
    ("Letter of Credit", 0.005), ("Overdraft", 0.005),
    ("PPC Discount", 0.005), ("Working Capital", 0.005),
    ("Equipment Loan", 0.005), ("Owner's Injection", 0.0), ("Other", 0.0),
    ("Custom agreement", 0.0),
])
def test_new_facilities_receive_only_omitted_cost_defaults(
    app, creation, facility_type, expected_rate
):
    facility = _base_facility("Funding", "new-funding")
    facility["type"] = facility_type
    del facility["interest_rate"]
    del facility["fees"]
    if creation == "add":
        created = _create(app)
        response = _request(app, "POST", f"/cashflow/{created['id']}/facilities", facility)
        assert response.status_code == 201
        saved = response.get_json()["facility"]
    elif creation == "import":
        saved = _create(app, [facility])["financing_facilities"][0]
    else:
        response = _request(app, "POST", "/project/unit-1/cashflows", {
            "name": "New scenario", "financing_facilities": [facility],
        })
        assert response.status_code == 201
        saved = response.get_json()["data"]["financing_facilities"][0]
    assert saved["interest_rate"] == expected_rate
    assert saved["fees"] == (0.04 if expected_rate else 0.0)
    assert "costs_note" not in saved
    assert "interest_rate_basis" not in saved
    assert "interest_rate" not in facility  # callers' dictionaries stay intact


@pytest.mark.parametrize("creation", ["add", "import", "new"])
def test_new_facilities_preserve_explicit_zero_or_entered_costs(app, creation):
    facility = _base_facility("No-interest funding", "zero-cost")
    facility["fees"] = 17.5
    if creation == "add":
        created = _create(app)
        response = _request(app, "POST", f"/cashflow/{created['id']}/facilities", facility)
        saved = response.get_json()["facility"]
    elif creation == "import":
        saved = _create(app, [facility])["financing_facilities"][0]
    else:
        response = _request(app, "POST", "/project/unit-1/cashflows", {
            "name": "Explicit terms", "financing_facilities": [facility],
        })
        saved = response.get_json()["data"]["financing_facilities"][0]
    assert saved["interest_rate"] == 0
    assert saved["fees"] == 17.5


def test_legacy_missing_costs_are_preserved_on_read_edit_order_add_and_calculation(app):
    legacy = _base_facility("Legacy bank", "legacy")
    legacy.update(draw_method="scheduled", draw_schedule={"0": 100}, end=1,
                  repayment_method="scheduled", repayment_schedule={})
    del legacy["interest_rate"]
    del legacy["fees"]
    with app.app_context():
        Cashflow(id="legacy-cf", unit_id="unit-1", name="Saved legacy", created_by="owner-1",
                 financing_facilities=[legacy]).commit()
    for path in ("/cashflow/legacy-cf", "/cashflow/legacy-cf/facilities",
                 "/cashflow/legacy-cf/facilities/legacy", "/cashflow/legacy-cf/export"):
        assert _request(app, "GET", path).status_code == 200
    calculated = _request(app, "GET", "/cashflow/legacy-cf").get_json()["data"]
    assert calculated["facility_rows"][0]["interest"] == [0.0, 0.0]
    assert _request(app, "PUT", "/cashflow/legacy-cf/facilities/legacy", {"name": "Legacy renamed"}).status_code == 200
    assert _request(app, "PUT", "/cashflow/legacy-cf/facilities/order", {"facility_ids": ["legacy"]}).status_code == 200
    assert _request(app, "PUT", "/cashflow/legacy-cf", {"name": "Scenario renamed"}).status_code == 200
    added = _base_facility("Additional bank", "additional")
    del added["interest_rate"]
    del added["fees"]
    assert _request(app, "POST", "/cashflow/legacy-cf/facilities", added).status_code == 201
    with app.app_context():
        saved = db.session.get(Cashflow, "legacy-cf").financing_facilities
        assert "interest_rate" not in saved[0]
        assert "fees" not in saved[0]
        assert saved[1]["interest_rate"] == 0.005


def test_new_default_interest_is_used_by_authoritative_calculation(app):
    facility = _base_facility("New bank", "new-bank")
    facility.update(draw_method="scheduled", draw_schedule={"0": 100}, end=1,
                    repayment_method="scheduled", repayment_schedule={})
    del facility["interest_rate"]
    del facility["fees"]
    calculated = _create(app, [facility])
    assert calculated["facility_rows"][0]["interest"][0] == 0.0
    assert calculated["facility_rows"][0]["interest"][1] == 0.5


@pytest.mark.parametrize("creation", ["add", "import", "new"])
@pytest.mark.parametrize("terms, expected_fee", [
    ({"limit": 500000}, 208.33),
    ({"limit": 0}, 0.0),
    ({"limit": None}, 0.0),
    ({"limit": None, "draw_method": "scheduled", "draw_schedule": {"0": 120000, "1": 120000}}, 100.0),
    ({"limit": 120000, "draw_method": "scheduled", "draw_schedule": {"0": 240000}}, 50.0),
    ({"limit": 500000, "fees": 0}, 0.0),
    ({"limit": 500000, "fees": 125}, 125.0),
])
def test_new_bank_fee_uses_facility_value_and_preserves_overrides(app, creation, terms, expected_fee):
    facility = _base_facility("Fee default", "fee-default")
    del facility["fees"]
    facility.update(terms)
    if creation == "add":
        created = _create(app)
        response = _request(app, "POST", f"/cashflow/{created['id']}/facilities", facility)
        assert response.status_code == 201, response.get_json()
        saved = response.get_json()["facility"]
    elif creation == "import":
        saved = _create(app, [facility])["financing_facilities"][0]
    else:
        response = _request(app, "POST", "/project/unit-1/cashflows", {
            "name": "Fee defaults", "financing_facilities": [facility],
        })
        assert response.status_code == 201, response.get_json()
        saved = response.get_json()["data"]["financing_facilities"][0]
    assert saved["fees"] == expected_fee
    assert "default_fees_rate" not in saved


def test_default_fee_is_charged_once_and_retained_on_edit(app):
    facility = _base_facility("Fee timing", "fee-timing")
    facility.update(limit=120000, start=1, end=2, draw_method="scheduled",
                    draw_schedule={"1": 100}, repayment_method="scheduled", repayment_schedule={})
    del facility["fees"]
    calculated = _create(app, [facility])
    assert calculated["facility_rows"][0]["fees"] == [0.0, 50.0, 0.0]
    assert calculated["summary"]["total_facility_fees"] == 50.0
    response = _request(app, "PUT", f"/cashflow/{calculated['id']}/facilities/fee-timing", {"limit": 240000})
    assert response.status_code == 200, response.get_json()
    assert response.get_json()["facility"]["fees"] == 50.0


@pytest.mark.parametrize("terms", [
    {"limit": "invalid"}, {"limit": -1}, {"limit": True},
    {"limit": None, "draw_method": "scheduled", "draw_schedule": {"0": "invalid"}},
])
def test_invalid_fee_basis_returns_controlled_validation_error(app, terms):
    created = _create(app)
    facility = _base_facility("Invalid fee basis")
    del facility["fees"]
    facility.update(terms)
    response = _request(app, "POST", f"/cashflow/{created['id']}/facilities", facility)
    assert response.status_code == 400
    with app.app_context():
        assert db.session.get(Cashflow, created["id"]).financing_facilities == []


@pytest.mark.parametrize("creation", ["add", "import", "new"])
@pytest.mark.parametrize("facility_type, draw_method, repayment_method, revolving", [
    ("Overdraft", "automatic_shortfall", "cashflow_sweep", True),
    ("Letter of Credit", "scheduled", "percent_of_ppc", False),
    ("PPC Discount", "ppc_base", "percent_of_ppc", False),
    ("Working Capital", "scheduled", "percent_of_ppc", False),
    ("Equipment Loan", "scheduled", "scheduled", False),
    ("Owner's Injection", "automatic_shortfall", "cashflow_sweep", False),
    (None, "scheduled", "cashflow_sweep", False),
    ("Custom agreement", "scheduled", "cashflow_sweep", False),
])
def test_minimal_new_facility_uses_its_backend_preset(
    app, creation, facility_type, draw_method, repayment_method, revolving
):
    facility = {"name": "Funding", "limit": 1000}
    if facility_type is not None:
        facility["type"] = facility_type
    if repayment_method == "percent_of_ppc":
        facility["repayment_percent"] = 0.1
    if draw_method == "ppc_base":
        facility["advance_portion"] = 0.5
    if creation == "add":
        created = _create(app)
        response = _request(app, "POST", f"/cashflow/{created['id']}/facilities", facility)
        assert response.status_code == 201, response.get_json()
        saved = response.get_json()["facility"]
    elif creation == "import":
        saved = _create(app, [facility])["financing_facilities"][0]
    else:
        response = _request(app, "POST", "/project/unit-1/cashflows", {
            "name": "Minimal scenario", "financing_facilities": [facility],
        })
        assert response.status_code == 201, response.get_json()
        saved = response.get_json()["data"]["financing_facilities"][0]
    assert saved["type"] == (facility_type or "Other")
    assert saved["draw_method"] == draw_method
    assert saved["repayment_method"] == repayment_method
    assert saved["revolving"] is revolving
    assert saved["start"] == 0


def test_new_facility_preserves_explicit_method_and_cost_overrides(app):
    created = _create(app)
    facility = {
        "name": "Custom OD terms", "type": "Overdraft", "draw_method": "scheduled",
        "repayment_method": "scheduled", "revolving": False, "start": 2,
        "interest_rate": 0, "fees": 23,
    }
    response = _request(app, "POST", f"/cashflow/{created['id']}/facilities", facility)
    assert response.status_code == 201
    for field, value in facility.items():
        assert response.get_json()["facility"][field] == value


@pytest.mark.parametrize("facility_type", ["Letter of Credit", "PPC Discount", "Working Capital"])
def test_preset_defaults_do_not_invent_required_contract_percentages(app, facility_type):
    created = _create(app)
    response = _request(app, "POST", f"/cashflow/{created['id']}/facilities", {
        "name": "Incomplete funding", "type": facility_type,
    })
    assert response.status_code == 400
    with app.app_context():
        assert db.session.get(Cashflow, created["id"]).financing_facilities == []
