"""Local financial scenarios belonging to QAuth Unit projects."""

from q_flow.extensions import db
from q_flow.models.mixins import BaseMixin
from q_flow.services.utils import rnd_color


class Cashflow(db.Model, BaseMixin):
    """A complete, independent cashflow scenario.

    The physical table name stays ``project`` so existing installations can
    migrate without copying financial or activity rows.
    """

    __tablename__ = "project"

    unit_id = db.Column(db.String(64), index=True)
    name = db.Column(db.String(64))
    description = db.Column(db.String(256))
    # Legacy identity columns are retained until the old database format can
    # be retired; QAuth is authoritative for Unit photo and colour.
    photo = db.Column(db.String(64))
    show = db.Column(db.Boolean, default=True)
    color = db.Column(db.String(64), default=rnd_color)
    activities = db.relationship("Activity", backref="cashflow", lazy=True)

    advance = db.Column(db.Float, default=0.1)
    retention = db.Column(db.Float, default=0.1)
    release_retention_eop = db.Column(db.Float, default=0.5)
    dlp = db.Column(db.Integer, default=12)
    duration_for_payment = db.Column(db.Integer, default=1)
    interest_rate = db.Column(db.Float, default=0.005)
    contract_value = db.Column(db.Float, default=0)
    wieb = db.Column(db.Float, default=0.2)

    def compact_dict(self):
        return {
            "id": self.id,
            "unit_id": self.unit_id,
            "name": self.name,
            "description": self.description or "",
        }

    def as_dict_with_activities(self):
        from q_flow.cashflow import CashflowCalculator

        active_activities = [a for a in self.activities if not a.is_deleted]
        if active_activities:
            calculator = CashflowCalculator(self)
            inflow = calculator.inflow()
            outflow = calculator.outflow()
        else:
            inflow = [0.0]
            outflow = [0.0]
        data = super().as_dict()
        data.update({
            "activities": [activity.as_dict() for activity in active_activities],
            "inflow": inflow,
            "outflow": outflow,
        })
        return data
