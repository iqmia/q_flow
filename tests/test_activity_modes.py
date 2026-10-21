from math import inf, nan

import pytest
from sqlalchemy import inspect, text

from q_flow import create_app
from q_flow.config import TestConfig
from q_flow.exceptions import InvalidData
from q_flow.extensions import db


def _app(tmp_path):
    class ActivityModeTestConfig(TestConfig):
        STORAGE_PATH = str(tmp_path)

    return create_app(ActivityModeTestConfig)


def _cashflow(**overrides):
    from q_flow.models.cashflow import Cashflow

    values = {
        "name": "Mode test",
        "unit_id": "unit-1",
        "created_by": "user-1",
        "contract_value": 1200,
        "advance": 0,
        "retention": 0,
        "release_retention_eop": 0,
        "dlp": 0,
        "duration_for_payment": 0,
        "interest_rate": 0,
        "wieb": 0,
        "use_independent_inflow_curve": False,
        "inflow_curve_type": "s_curve",
        "inflow_curve_skew": 0,
    }
    values.update(overrides)
    return Cashflow(**values).commit()


def _activity(cashflow, **overrides):
    from q_flow.models.activity import Activity

    values = {
        "name": "Activity",
        "cashflow_id": cashflow.id,
        "created_by": "user-1",
        "activity_type": "General",
        "activity_mode": "work",
        "distribution_type": "s_curve",
        "cost": 100,
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
    }
    values.update(overrides)
    return Activity(**values).commit()


def test_new_activity_defaults_to_work_s_curve(tmp_path):
    app = _app(tmp_path)
    from q_flow.models.activity import Activity

    with app.app_context():
        cashflow = _cashflow()
        activity = Activity(
            name="Default",
            cashflow_id=cashflow.id,
            created_by="user-1",
            cost=100,
            duration=2,
        ).commit()

        assert activity.activity_mode == "work"
        assert activity.distribution_type == "s_curve"
        assert activity.mobilization_period == 0
        assert activity.cost_schedule_json is None

        columns = set(Activity.__table__.columns.keys())
        assert "mobilization" not in columns
        assert "profit" not in columns
        assert "subcontractors_retention" not in columns
        assert "interest_rate" not in columns
        assert "compounding_period" not in columns


def test_activity_type_presets_have_no_implicit_prework_delay():
    import json
    from pathlib import Path

    presets_file = Path(__file__).resolve().parents[1] / "q_flow" / "static" / "activity_types.json"
    presets = json.loads(presets_file.read_text(encoding="utf-8"))
    assert presets
    assert all(preset.get("mobilization_period", 0) == 0 for preset in presets.values())


def test_legacy_linear_inference_when_new_fields_are_null():
    from q_flow.models.activity import (
        Activity,
        effective_activity_mode,
        effective_distribution_type,
    )

    activity = Activity(
        activity_type="linear",
        activity_mode=None,
        distribution_type=None,
    )

    assert effective_activity_mode(activity) == "work"
    assert effective_distribution_type(activity) == "linear"


def test_valid_manual_schedule_sets_cost_and_duration():
    from q_flow.models.activity import Activity, normalize_activity

    activity = Activity(
        activity_type="MEP",
        activity_mode="work",
        distribution_type="manual",
        cost=999,
        duration=99,
        cost_schedule_json=[200, 0, 500, 0, 200],
    )

    normalize_activity(activity)

    assert activity.cost == 900
    assert activity.duration == 5
    assert activity.cost_schedule_json == [200.0, 0.0, 500.0, 0.0, 200.0]


def test_scheduled_cost_normalizes_distribution_cost_and_duration():
    from q_flow.models.activity import Activity, normalize_activity

    activity = Activity(
        activity_mode="scheduled_cost",
        distribution_type="s_curve",
        cost=1,
        duration=1,
        cost_schedule_json=[0, 300, 700],
    )

    normalize_activity(activity)

    assert activity.distribution_type == "manual"
    assert activity.cost == 1000
    assert activity.duration == 3


@pytest.mark.parametrize(
    "mode,distribution,schedule",
    [
        ("work", "manual", None),
        ("work", "manual", []),
        ("scheduled_cost", "manual", None),
        ("scheduled_cost", "manual", []),
        ("work", "manual", [0, 0]),
        ("scheduled_cost", "manual", [0, 0]),
        ("work", "manual", [100, -1]),
        ("work", "manual", [100, True]),
        ("work", "manual", [100, nan]),
        ("work", "manual", [100, inf]),
    ],
)
def test_manual_and_scheduled_cost_reject_invalid_schedules(
    mode, distribution, schedule
):
    from q_flow.models.activity import Activity, normalize_activity

    activity = Activity(
        activity_mode=mode,
        distribution_type=distribution,
        cost=100,
        duration=2,
        cost_schedule_json=schedule,
    )

    with pytest.raises(InvalidData):
        normalize_activity(activity)


def test_generated_work_allows_empty_schedule():
    from q_flow.models.activity import Activity, normalize_activity

    activity = Activity(
        activity_mode="work",
        distribution_type="linear",
        cost=100,
        duration=2,
        cost_schedule_json=[],
    )

    normalize_activity(activity)

    assert activity.cost == 100
    assert activity.duration == 2


def test_activity_schema_upgrade_adds_nullable_columns_without_backfill(tmp_path):
    app = _app(tmp_path)
    with app.app_context():
        db.drop_all()
        db.session.execute(text(
            "CREATE TABLE activity ("
            "id VARCHAR(64) PRIMARY KEY, "
            "name VARCHAR(64), "
            "activity_type VARCHAR(64)"
            ")"
        ))
        db.session.execute(text(
            "INSERT INTO activity (id, name, activity_type) "
            "VALUES ('legacy-1', 'Legacy', 'linear')"
        ))
        db.session.commit()

    runner = app.test_cli_runner()
    first = runner.invoke(args=["add-activity-mode-columns"])
    second = runner.invoke(args=["add-activity-mode-columns"])

    assert first.exit_code == 0, first.output
    assert second.exit_code == 0, second.output

    with app.app_context():
        columns = {column["name"] for column in inspect(db.engine).get_columns("activity")}
        assert {
            "activity_mode",
            "distribution_type",
            "cost_schedule_json",
        }.issubset(columns)
        row = db.session.execute(text(
            "SELECT activity_mode, distribution_type, cost_schedule_json "
            "FROM activity WHERE id = 'legacy-1'"
        )).one()
        assert tuple(row) == (None, None, None)


def test_manual_work_replaces_curve_but_keeps_payment_pipeline(tmp_path):
    app = _app(tmp_path)
    from q_flow.cashflow import Activity_cf
    from q_flow.models.activity import normalize_activity

    with app.app_context():
        cashflow = _cashflow(contract_value=100)
        activity = _activity(
            cashflow,
            activity_mode="work",
            distribution_type="manual",
            cost_schedule_json=[40, 60],
            subcontracted=1,
            duration_for_payment=1,
        )
        normalize_activity(activity)
        cf = Activity_cf(activity)

        assert cf.marginal_work_as_json()["marginal_work"] == [40.0, 60.0]
        assert cf.out_flow_as_json()["marginal_out_flow"] == [0.0, 40.0, 60.0, 0.0]


def test_scheduled_cost_has_zero_work_direct_outflow_and_start_offset(tmp_path):
    app = _app(tmp_path)
    from q_flow.cashflow import Activity_cf
    from q_flow.models.activity import normalize_activity

    with app.app_context():
        cashflow = _cashflow()
        activity = _activity(
            cashflow,
            activity_mode="scheduled_cost",
            distribution_type="manual",
            cost_schedule_json=[200, 0, 500],
            start=2,
        )
        normalize_activity(activity)
        cf = Activity_cf(activity)

        assert cf.marginal_work_as_json()["marginal_work"] == [0.0, 0.0, 0.0, 0.0, 0.0]
        assert cf.out_flow_as_json()["marginal_out_flow"] == [0.0, 0.0, 200.0, 0.0, 500.0]


def test_late_scheduled_cost_extends_outflow_not_work_duration(tmp_path):
    app = _app(tmp_path)
    from q_flow.cashflow import CashflowCalculator
    from q_flow.models.activity import normalize_activity

    with app.app_context():
        cashflow = _cashflow(
            contract_value=100,
            use_independent_inflow_curve=True,
            inflow_curve_type="linear",
        )
        _activity(
            cashflow,
            activity_mode="work",
            distribution_type="linear",
            cost=100,
            duration=2,
        )
        scheduled = _activity(
            cashflow,
            name="Late purchase",
            activity_mode="scheduled_cost",
            distribution_type="manual",
            cost_schedule_json=[100],
            start=4,
        )
        normalize_activity(scheduled)
        calculator = CashflowCalculator(cashflow)
        snapshot = calculator.snapshot()

        assert snapshot["duration"] == 2
        assert snapshot["workflow"] == [50.0, 50.0]
        assert calculator.contract_work() == [50.0, 50.0]
        assert snapshot["outflow"][4] == 100.0


def test_scheduled_cost_only_snapshot_keeps_outflow_with_zero_work_duration(tmp_path):
    app = _app(tmp_path)
    from q_flow.cashflow import CashflowCalculator
    from q_flow.models.activity import normalize_activity

    with app.app_context():
        cashflow = _cashflow(contract_value=0, interest_rate=0)
        scheduled = _activity(
            cashflow,
            activity_mode="scheduled_cost",
            distribution_type="manual",
            cost_schedule_json=[0, 250],
        )
        normalize_activity(scheduled)
        snapshot = CashflowCalculator(cashflow).snapshot()

        assert snapshot["duration"] == 0
        assert snapshot["workflow"] == []
        assert snapshot["inflow"] == []
        assert snapshot["outflow"] == [0.0, 250.0]
        assert snapshot["netflow"] == [0.0, -250.0]
        assert snapshot["outflow_with_interest"] == [0.0, -250.0]


def test_activity_linked_inflow_scales_only_work_cost_and_summary_keeps_cost_classes(tmp_path):
    app = _app(tmp_path)
    from q_flow.cashflow import CashflowCalculator
    from q_flow.models.activity import normalize_activity

    with app.app_context():
        cashflow = _cashflow(contract_value=1200)
        work = _activity(
            cashflow,
            name="Manual work",
            activity_mode="work",
            distribution_type="manual",
            cost_schedule_json=[300, 500],
        )
        purchase = _activity(
            cashflow,
            name="Purchase",
            activity_mode="scheduled_cost",
            distribution_type="manual",
            cost_schedule_json=[0, 200],
            subcontracted=1,
        )
        normalize_activity(work)
        normalize_activity(purchase)

        calculator = CashflowCalculator(cashflow)
        data = cashflow.as_dict_with_activities()

        assert calculator.workflow() == [300.0, 500.0]
        assert calculator.contract_work() == [450.0, 750.0]
        assert data["summary"]["direct_cost"] == 1000.0
        assert data["summary"]["work_cost"] == 800.0
        assert data["summary"]["scheduled_cost"] == 200.0
        assert data["summary"]["subcontracted_cost"] == 0.0
        assert data["summary"]["self_performed_cost"] == 800.0
