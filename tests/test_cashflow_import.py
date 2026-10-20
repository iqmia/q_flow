from unittest.mock import Mock, patch

import pytest

from q_flow import create_app
from q_flow.config import TestConfig
from q_flow.extensions import db
from q_flow.models.activity import Activity
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


def _payload():
    return {
        "format": "cashflowpot.cashflow",
        "version": 1,
        "cashflow": {
            "name": "Imported tender",
            "description": "Portable scenario",
            "contract_value": 1250000,
            "advance": 0.1,
            "retention": 0.1,
            "release_retention_eop": 0.5,
            "dlp": 12,
            "duration_for_payment": 1,
            "interest_rate": 0.005,
            "wieb": 0.2,
            "activities": [
                {
                    "name": "Concrete",
                    "activity_type": "General",
                    "cost": 500000,
                    "duration": 4,
                    "duration_units": "Periods",
                    "start": 0,
                    "advance": 0.1,
                    "retention": 0.1,
                    "release_retention_eop": 0.5,
                    "dlp": 6,
                    "duration_for_payment": 1,
                    "work_in_excess": 0.1,
                    "mobilization_period": 0,
                    "subcontracted": 0.5,
                    "skew": 0.0,
                    "no_billing_period": 0,
                }
            ],
        },
    }


def _permission():
    return Mock(return_value={"user_id": "owner-1", "unit_id": "unit-1"})


def _import(app, payload):
    with patch("q_flow.routes.cashflows.ensure_unit_permission", _permission()):
        return app.test_client().post(
            "/project/unit-1/cashflows/import",
            headers=_auth(),
            json=payload,
        )


@pytest.mark.parametrize(
    "pre_work_delay, expected_work_period",
    [(None, 2), (0, 2), (1, 3)],
)
def test_import_activity_prework_defaults_to_zero_unless_explicit(app, pre_work_delay, expected_work_period):
    payload = _payload()
    activity = payload["cashflow"]["activities"][0]
    activity.update(
        name="One-period task",
        activity_type="linear",
        distribution_type="linear",
        start=1,  # P2 in the user-facing frontend
        duration=1,
        cost=100,
        subcontracted=0,
    )
    if pre_work_delay is None:
        activity.pop("mobilization_period")
    else:
        activity["mobilization_period"] = pre_work_delay

    response = _import(app, payload)
    assert response.status_code == 201
    scenario = response.get_json()["data"]
    actual = scenario["activities"][0]
    assert actual["mobilization_period"] == (pre_work_delay or 0)
    assert scenario["summary"]["work_duration"] == expected_work_period
    assert actual["cash_flow_json"]["marginal_work"] == (
        [0.0] * (expected_work_period - 1) + [100.0]
    )


def test_import_cashflow_creates_complete_scenario_atomically(app):
    result = _import(app, _payload())

    assert result.status_code == 201
    snapshot = result.get_json()["data"]
    assert snapshot["unit_id"] == "unit-1"
    assert snapshot["name"] == "Imported tender"
    assert snapshot["use_independent_inflow_curve"] is True
    assert snapshot["inflow_curve_type"] == "s_curve"
    assert snapshot["inflow_curve_skew"] == 0.0
    assert len(snapshot["activities"]) == 1
    assert snapshot["activities"][0]["name"] == "Concrete"
    assert snapshot["activities"][0]["cashflow_id"] == snapshot["id"]
    assert snapshot["activities"][0]["activity_mode"] == "work"
    assert snapshot["activities"][0]["distribution_type"] == "s_curve"
    assert snapshot["workflow"]
    assert snapshot["outflow"]

    with app.app_context():
        assert Cashflow.query.filter_by(unit_id="unit-1").count() == 1
        assert Activity.query.count() == 1


def test_import_cashflow_preserves_independent_inflow_settings(app):
    payload = _payload()
    payload["cashflow"].update({
        "use_independent_inflow_curve": False,
        "inflow_curve_type": "linear",
        "inflow_curve_skew": 0.35,
    })

    result = _import(app, payload)

    assert result.status_code == 201
    snapshot = result.get_json()["data"]
    assert snapshot["use_independent_inflow_curve"] is False
    assert snapshot["inflow_curve_type"] == "linear"
    assert snapshot["inflow_curve_skew"] == pytest.approx(0.35)


def test_import_cashflow_preserves_facility_terms_and_calculated_rows(app):
    payload = _payload()
    payload["cashflow"]["financing_facilities"] = [{
        "id": "od-1",
        "name": "Project overdraft",
        "type": "Overdraft",
        "draw_method": "automatic_shortfall",
        "repayment_method": "cashflow_sweep",
        "start": 0,
        "end": 4,
        "limit": 100000,
        "fees": 250,
        "interest_rate": 0.01,
        "revolving": True,
        "sweep_priority": 0,
    }]

    result = _import(app, payload)

    assert result.status_code == 201
    snapshot = result.get_json()["data"]
    assert snapshot["financing_facilities"] == payload["cashflow"]["financing_facilities"]
    assert snapshot["facility_rows"][0]["id"] == "od-1"
    assert snapshot["facility_fees"]


def test_import_cashflow_accepts_manual_work_schedule_without_cost_or_duration(app):
    payload = _payload()
    payload["cashflow"]["activities"] = [{
        "name": "Manual MEP work",
        "activity_type": "mep",
        "activity_mode": "work",
        "distribution_type": "manual",
        "cost_schedule_json": [200, 0, 500, 300],
        "start": 1,
        "advance": 0,
        "retention": 0,
        "release_retention_eop": 0,
        "dlp": 0,
        "duration_for_payment": 0,
        "work_in_excess": 0,
        "mobilization_period": 0,
        "subcontracted": 0,
        "skew": 0,
        "no_billing_period": 0,
    }]

    result = _import(app, payload)

    assert result.status_code == 201
    activity = result.get_json()["data"]["activities"][0]
    assert activity["activity_mode"] == "work"
    assert activity["distribution_type"] == "manual"
    assert activity["cost_schedule_json"] == [200.0, 0.0, 500.0, 300.0]
    assert activity["cost"] == 1000.0
    assert activity["duration"] == 4


def test_import_cashflow_accepts_scheduled_cost_and_keeps_it_out_of_work(app):
    payload = _payload()
    payload["cashflow"]["use_independent_inflow_curve"] = False
    payload["cashflow"]["activities"] = [
        {
            "name": "Work",
            "activity_type": "General",
            "activity_mode": "work",
            "distribution_type": "linear",
            "cost": 800,
            "duration": 2,
            "start": 0,
            "advance": 0,
            "retention": 0,
            "release_retention_eop": 0,
            "dlp": 0,
            "duration_for_payment": 0,
            "work_in_excess": 0,
            "mobilization_period": 0,
            "subcontracted": 0,
            "skew": 0,
            "no_billing_period": 0,
        },
        {
            "name": "Purchase",
            "activity_type": "mep",
            "activity_mode": "scheduled_cost",
            "distribution_type": "manual",
            "cost_schedule_json": [0, 200],
            "start": 0,
        },
    ]

    result = _import(app, payload)

    assert result.status_code == 201
    snapshot = result.get_json()["data"]
    purchase = snapshot["activities"][1]
    assert purchase["cost"] == 200.0
    assert purchase["duration"] == 2
    assert purchase["cash_flow_json"]["marginal_work"] == [0.0, 0.0]
    assert purchase["cash_flow_json"]["marginal_out_flow"] == [0.0, 200.0]
    assert snapshot["summary"]["direct_cost"] == 1000.0
    assert snapshot["duration"] == 2


def test_import_old_version_one_linear_activity_keeps_legacy_linear_distribution(app):
    payload = _payload()
    activity = payload["cashflow"]["activities"][0]
    activity["activity_type"] = "linear"
    activity["cost"] = 100
    activity["duration"] = 2
    activity["subcontracted"] = 0
    payload["cashflow"]["contract_value"] = 100
    payload["cashflow"]["use_independent_inflow_curve"] = False

    result = _import(app, payload)

    assert result.status_code == 201
    imported = result.get_json()["data"]["activities"][0]
    assert imported["activity_mode"] == "work"
    assert imported["distribution_type"] == "linear"
    assert imported["cash_flow_json"]["marginal_work"] == [50.0, 50.0]


def test_import_cashflow_rejects_invalid_activity_without_partial_rows(app):
    payload = _payload()
    payload["cashflow"]["activities"][0]["cost"] = 0

    result = _import(app, payload)

    assert result.status_code == 400
    with app.app_context():
        assert Cashflow.query.count() == 0
        assert Activity.query.count() == 0


def test_import_cashflow_rejects_unknown_format_version(app):
    payload = _payload()
    payload["version"] = 2

    result = _import(app, payload)

    assert result.status_code == 400
    with app.app_context():
        assert Cashflow.query.count() == 0
        assert Activity.query.count() == 0


def test_import_cashflow_rejects_non_text_name_without_partial_rows(app):
    payload = _payload()
    payload["cashflow"]["name"] = 123

    result = _import(app, payload)

    assert result.status_code == 400
    with app.app_context():
        assert Cashflow.query.count() == 0
        assert Activity.query.count() == 0


@pytest.mark.parametrize("legacy_type", [None, "linear"])
def test_real_export_of_legacy_null_activity_fields_can_be_imported(app, legacy_type):
    legacy_fields = ("activity_mode", "distribution_type", "duration_units")
    with app.app_context():
        cashflow = Cashflow(id="legacy-cf", unit_id="unit-1", name="Legacy",
                            contract_value=100, created_by="owner-1").commit()
        activity = Activity(id="legacy-work", cashflow_id=cashflow.id, name="Work",
                            cost=100, duration=2, created_by="owner-1").commit()
        # Persist genuine legacy nulls after insert so ORM insertion defaults
        # cannot replace them before the real export route is exercised.
        for field in legacy_fields:
            setattr(activity, field, None)
        activity.activity_type = legacy_type
        db.session.commit()
    with patch("q_flow.routes.cashflows.ensure_unit_permission", _permission()):
        original = app.test_client().get("/cashflow/legacy-cf", headers=_auth()).get_json()["data"]
        exported = app.test_client().get("/cashflow/legacy-cf/export", headers=_auth())
    assert exported.status_code == 200
    source = exported.get_json()
    assert source["cashflow"]["description"] is None
    for field in legacy_fields:
        assert source["cashflow"]["activities"][0][field] is None
    assert source["cashflow"]["activities"][0]["activity_type"] == legacy_type

    response = _import(app, source)

    assert response.status_code == 201, response.get_json()
    imported = response.get_json()["data"]
    for field in ("workflow", "inflow", "outflow", "netflow", "outflow_with_interest"):
        assert imported[field] == original[field]
    assert imported["activities"][0]["distribution_type"] == (
        "linear" if legacy_type == "linear" else "s_curve"
    )
    with app.app_context():
        saved_legacy = db.session.get(Activity, "legacy-work")
        assert saved_legacy.activity_mode is None
        assert saved_legacy.distribution_type is None


@pytest.mark.parametrize("field", [
    "activity_type", "activity_mode", "distribution_type", "duration_units",
])
def test_nullable_legacy_import_strings_still_reject_non_text_values(app, field):
    payload = _payload()
    payload["cashflow"]["activities"][0][field] = []
    assert _import(app, payload).status_code == 400
    with app.app_context():
        assert Cashflow.query.count() == 0
        assert Activity.query.count() == 0


def test_import_preserves_nullable_optional_description(app):
    payload = _payload()
    payload["cashflow"]["description"] = None
    response = _import(app, payload)
    assert response.status_code == 201
    assert response.get_json()["data"]["description"] is None


def test_import_still_rejects_non_text_optional_description(app):
    payload = _payload()
    payload["cashflow"]["description"] = []
    assert _import(app, payload).status_code == 400


def test_real_export_with_nullable_facilities_imports_as_empty_without_editing_source(app):
    created = _import(app, _payload()).get_json()["data"]
    with app.app_context():
        source = db.session.get(Cashflow, created["id"])
        source.financing_facilities = None
        db.session.commit()
    with patch("q_flow.routes.cashflows.ensure_unit_permission", _permission()):
        exported = app.test_client().get(f"/cashflow/{created['id']}/export", headers=_auth())
    assert exported.get_json()["cashflow"]["financing_facilities"] is None

    response = _import(app, exported.get_json())

    assert response.status_code == 201, response.get_json()
    assert response.get_json()["data"]["financing_facilities"] == []
    with app.app_context():
        assert db.session.get(Cashflow, created["id"]).financing_facilities is None
        assert db.session.get(Cashflow, response.get_json()["data"]["id"]).financing_facilities == []


def test_direct_new_cashflow_accepts_nullable_facility_list_as_empty(app):
    with patch("q_flow.routes.cashflows.ensure_unit_permission", _permission()):
        response = app.test_client().post(
            "/project/unit-1/cashflows", headers=_auth(),
            json={"name": "No facilities", "financing_facilities": None},
        )
    assert response.status_code == 201, response.get_json()
    assert response.get_json()["data"]["financing_facilities"] == []


@pytest.mark.parametrize("creation", ["new", "import"])
@pytest.mark.parametrize("settings", [
    {"use_independent_inflow_curve": None},
    {"inflow_curve_type": None},
    {"inflow_curve_skew": None},
    {"use_independent_inflow_curve": None, "inflow_curve_type": None, "inflow_curve_skew": None},
])
def test_explicit_nullable_curve_fields_are_preserved_at_creation(app, creation, settings):
    payload = _payload()
    payload["cashflow"].update(settings)
    if creation == "import":
        response = _import(app, payload)
    else:
        source = {key: value for key, value in payload["cashflow"].items() if key != "activities"}
        with patch("q_flow.routes.cashflows.ensure_unit_permission", _permission()):
            response = app.test_client().post(
                "/project/unit-1/cashflows", headers=_auth(), json=source,
            )
    assert response.status_code == 201, response.get_json()
    saved = response.get_json()["data"]
    with app.app_context():
        stored = db.session.get(Cashflow, saved["id"])
        for field in settings:
            assert saved[field] is None
            assert getattr(stored, field) is None
        defaults = {"use_independent_inflow_curve": True, "inflow_curve_type": "s_curve", "inflow_curve_skew": 0.0}
        for field, value in defaults.items():
            if field not in settings:
                assert saved[field] == value


@pytest.mark.parametrize("creation", ["new", "import"])
def test_real_legacy_null_curve_roundtrip_retains_activity_linked_calculation(app, creation):
    curve_fields = ("use_independent_inflow_curve", "inflow_curve_type", "inflow_curve_skew")
    with app.app_context():
        cashflow = Cashflow(id="legacy-linked", unit_id="unit-1", name="Legacy linked",
                            created_by="owner-1", contract_value=100, advance=0, retention=0,
                            dlp=0, duration_for_payment=0, interest_rate=0, wieb=0).commit()
        Activity(cashflow_id=cashflow.id, name="Delayed work", created_by="owner-1",
                 activity_type="linear", cost=100, duration=2, start=2, advance=0,
                 retention=0, dlp=0, duration_for_payment=0, work_in_excess=0,
                 mobilization_period=0, subcontracted=0, skew=0, no_billing_period=0).commit()
        independent = cashflow.as_dict_with_activities()
        for field in curve_fields:
            setattr(cashflow, field, None)
        db.session.commit()
        original = cashflow.as_dict_with_activities()
    # Delayed activity work starts in period 2; independent work spans the
    # entire four-period work horizon, so changing selector nulls is observable.
    assert original["inflow"][:2] == [0.0, 0.0]
    assert independent["inflow"] != original["inflow"]
    with patch("q_flow.routes.cashflows.ensure_unit_permission", _permission()):
        exported = app.test_client().get("/cashflow/legacy-linked/export", headers=_auth()).get_json()
    for field in curve_fields:
        assert exported["cashflow"][field] is None
    if creation == "import":
        response = _import(app, exported)
        assert response.status_code == 201, response.get_json()
        recreated = response.get_json()["data"]
    else:
        source = {key: value for key, value in exported["cashflow"].items() if key != "activities"}
        with patch("q_flow.routes.cashflows.ensure_unit_permission", _permission()):
            response = app.test_client().post("/project/unit-1/cashflows", headers=_auth(), json=source)
        assert response.status_code == 201, response.get_json()
        with patch("q_flow.routes.activities.ensure_unit_permission", _permission()):
            added = app.test_client().post(
                f"/new_activity/{response.get_json()['data']['id']}", headers=_auth(),
                json=exported["cashflow"]["activities"][0],
            )
        assert added.status_code == 201, added.get_json()
        recreated = added.get_json()["cashflow"]
    for field in curve_fields:
        assert recreated[field] is None
    for field in ("workflow", "inflow", "outflow", "netflow", "outflow_with_interest"):
        assert recreated[field] == original[field]
    with app.app_context():
        for field in curve_fields:
            assert getattr(db.session.get(Cashflow, "legacy-linked"), field) is None
