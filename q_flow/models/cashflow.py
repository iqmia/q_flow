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

        active_activities = [
            activity for activity in self.activities if not activity.is_deleted
        ]
        calculator = CashflowCalculator(self)
        activities = []
        for activity in active_activities:
            data = activity.as_dict()
            data["cash_flow_json"] = calculator.activity_cashflows[activity.id]
            activities.append(data)

        snapshot = calculator.snapshot()
        direct_cost = sum(float(activity.cost or 0) for activity in active_activities)
        subcontracted_cost = sum(
            float(activity.cost or 0) * float(activity.subcontracted or 0)
            for activity in active_activities
        )
        self_performed_cost = direct_cost - subcontracted_cost
        total_inflow = round(sum(calculator.inflow()), 2) if active_activities else 0.0
        final_cash_balance = (
            snapshot["outflow_with_interest"][-1]
            if snapshot["outflow_with_interest"]
            else 0.0
        )
        financing_cost = max(
            0.0,
            round(total_inflow - direct_cost - final_cash_balance, 2),
        )
        total_cost = round(direct_cost + financing_cost, 2)
        summary = {
            "total_inflow": round(total_inflow, 2),
            "subcontracted_cost": round(subcontracted_cost, 2),
            "self_performed_cost": round(self_performed_cost, 2),
            "direct_cost": round(direct_cost, 2),
            "financing_cost": financing_cost,
            "total_cost": total_cost,
            "final_cash_balance": round(final_cash_balance, 2),
            "work_duration": snapshot["duration"],
            "dlp": self.dlp or 0,
            "financial_horizon": len(snapshot["outflow_with_interest"]),
        }

        data = super().as_dict()
        data.update({
            "activities": activities,
            **snapshot,
            "summary": summary,
        })
        return data
