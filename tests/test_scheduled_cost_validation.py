from q_flow.models.activity import Activity, normalize_activity
from q_flow.routes.activities import _validate_activity


def test_scheduled_cost_validation_ignores_work_only_assumptions():
    activity = Activity(
        activity_mode="scheduled_cost",
        distribution_type="manual",
        cost_schedule_json=[100, 0, 200],
        start=0,
        # These fields are irrelevant to Scheduled Cost calculation.
        advance=2,
        retention=2,
        release_retention_eop=2,
        dlp=-1,
        duration_for_payment=-1,
        work_in_excess=2,
        mobilization_period=-1,
        subcontracted=2,
        skew=2,
        no_billing_period=-1,
    )

    normalize_activity(activity)
    _validate_activity(activity)
