from enum import Enum
from math import isfinite

from q_flow.exceptions import InvalidData
from q_flow.extensions import db
from q_flow.models.mixins import BaseMixin
from sqlalchemy.orm import synonym


ACTIVITY_MODES = {"work", "scheduled_cost"}
DISTRIBUTION_TYPES = {"s_curve", "linear", "manual"}


class ActivityType(Enum):
    GENERAL = ("General", 0)
    STRUCTURE = ("Structure", -0.5)
    MEP = ("MEP", 0.9)
    FACADE = ("Facade", 0)
    FINISHES = ("Finishes", -0.2)
    LANDSCAPE = ("Landscape", 0)
    INFRASTRUCTURE = ("Infrastructure", -0.8)
    OTHER = ("Other", 0)
    LINEAR = ("Linear", 0)

    def __str__(self):
        return self.code

    def __init__(self, code, skew):
        self.code = code
        self.skew = skew
        self.type_name = self.name.replace('_', ' ').title()

    @classmethod
    def by_code(cls, code):
        for at in cls:
            if at.code == code:
                return at
        raise ValueError(f'ActivityType code {code} not found')

    @classmethod
    def skew_by_code(cls, code):
        for at in cls:
            if at.code == code:
                return at.skew
        return 0


def effective_activity_mode(activity) -> str:
    """Return the calculation mode while preserving legacy nullable rows."""
    return activity.activity_mode or "work"


def effective_distribution_type(activity) -> str:
    """Return the calculation distribution for new and legacy activities."""
    if effective_activity_mode(activity) == "scheduled_cost":
        return "manual"
    if activity.distribution_type:
        return activity.distribution_type
    if str(activity.activity_type or "").casefold() == "linear":
        return "linear"
    return "s_curve"


def _normalized_schedule(schedule):
    InvalidData.require_condition(
        isinstance(schedule, list) and len(schedule) > 0,
        "Activity cost schedule must be a non-empty list",
    )
    normalized = []
    for value in schedule:
        InvalidData.require_condition(
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and isfinite(value)
            and value >= 0,
            "Activity cost schedule values must be finite non-negative numbers",
        )
        normalized.append(float(value))
    InvalidData.require_condition(
        sum(normalized) > 0,
        "Activity cost schedule total must be greater than zero",
    )
    return normalized


def normalize_activity(activity):
    """Normalize calculation source fields before validation/calculation.

    Existing rows added before activity modes may keep the new columns NULL.
    Legacy ``activity_type='linear'`` therefore still infers a linear work
    distribution until the row is explicitly saved with the new fields.
    """
    mode = effective_activity_mode(activity)
    InvalidData.require_condition(
        mode in ACTIVITY_MODES,
        "Activity mode must be work or scheduled_cost",
    )

    distribution = effective_distribution_type(activity)
    InvalidData.require_condition(
        distribution in DISTRIBUTION_TYPES,
        "Activity distribution_type must be s_curve, linear, or manual",
    )

    activity.activity_mode = mode
    activity.distribution_type = (
        "manual" if mode == "scheduled_cost" else distribution
    )

    uses_schedule = (
        mode == "scheduled_cost" or activity.distribution_type == "manual"
    )
    if uses_schedule:
        schedule = _normalized_schedule(activity.cost_schedule_json)
        activity.cost_schedule_json = schedule
        activity.cost = sum(schedule)
        activity.duration = len(schedule)

    return activity


class Activity(db.Model, BaseMixin):
    name = db.Column(db.String(64))
    cash_flow_json = db.Column(db.JSON)

    cashflow_id = db.Column(
        'project_id',
        db.String(64),
        db.ForeignKey('project.id'),
        nullable=False,
    )
    project_id = synonym('cashflow_id')

    def as_dict(self):
        data = super().as_dict()
        data['cashflow_id'] = data.pop('project_id')
        return data

    # Creation-time template/category such as Structure, MEP, Facade, etc.
    activity_type = db.Column(db.String(64), default=ActivityType.GENERAL.code)

    # Calculation semantics. Columns remain nullable for legacy rows created
    # before this schema existed; helpers above provide runtime compatibility.
    activity_mode = db.Column(db.String(32), nullable=True, default="work")
    distribution_type = db.Column(db.String(32), nullable=True, default="s_curve")
    cost_schedule_json = db.Column(db.JSON, nullable=True)

    # Contractor's estimated cost of the activity. For manual work and
    # scheduled cost this is derived from cost_schedule_json.
    cost = db.Column(db.Float, default=0.0)

    # Duration Units
    duration_units = db.Column(db.String(64), default="Months")

    # Time to complete the activity. For manual work and scheduled cost this
    # is derived from the dense schedule length.
    duration = db.Column(db.Integer, default=4)

    # A time after the start of the project where the activity starts.
    # zero means the activity starts at the start of the project.
    start = db.Column(db.Integer, default=0)

    # A percentage of the activity cost issued to the subcontractor prior to
    # the start of work.
    advance = db.Column(db.Float, default=0.1)

    # The percent deduction applied to each subcontract invoice and released
    # at the end of progress / DLP according to release_retention_eop.
    retention = db.Column(db.Float, default=0.1)

    # Fraction of subcontract retention released at the first release point.
    release_retention_eop = db.Column(db.Float, default=0.5)

    # Defects liability period between first and final retention releases.
    dlp = db.Column(db.Integer, default=0)

    # Period required to process a subcontract invoice and issue payment.
    duration_for_payment = db.Column(db.Integer, default=1)

    # Percentage of subcontract work carried into the following billing period.
    work_in_excess = db.Column(db.Float, default=0.1)

    # Legacy name retained because the calculation actively uses this as the
    # initial pre-work/no-work period.
    mobilization_period = db.Column(db.Integer, default=1)

    # Percent subcontracted.
    subcontracted = db.Column(db.Float, default=0.7)

    # Skewing factor between -1 and +1 for generated S-curves.
    skew = db.Column(db.Float, default=0.0)

    # Initial subcontract billing window during which work accumulates before
    # the first bill is issued.
    no_billing_period = db.Column(db.Integer, default=0)
