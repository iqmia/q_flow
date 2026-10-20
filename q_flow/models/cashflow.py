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
    description = db.Column(db.Text)
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

    # Main-contract value-of-work generation. Existing database rows may keep
    # these columns NULL; the calculator treats a NULL curve type as the
    # activity-linked legacy method. New scenarios receive the independent
    # S-curve defaults below.
    use_independent_inflow_curve = db.Column(db.Boolean, nullable=True, default=True)
    inflow_curve_type = db.Column(db.String(16), nullable=True, default="s_curve")
    inflow_curve_skew = db.Column(db.Float, nullable=True, default=0.0)
    financing_facilities = db.Column(db.JSON, nullable=True, default=list)

    def compact_dict(self):
        return {
            "id": self.id,
            "unit_id": self.unit_id,
            "name": self.name,
            "description": self.description or "",
        }

    def as_dict_with_activities(self, *, include_details=True):
        from q_flow.cashflow import CashflowCalculator
        from q_flow.models.activity import effective_activity_mode

        active_activities = [
            activity for activity in self.activities if not activity.is_deleted
        ]
        calculator = CashflowCalculator(self)
        snapshot = calculator.snapshot()
        work_activities = [
            activity
            for activity in active_activities
            if effective_activity_mode(activity) == "work"
        ]
        scheduled_cost_activities = [
            activity
            for activity in active_activities
            if effective_activity_mode(activity) == "scheduled_cost"
        ]
        work_cost = sum(float(activity.cost or 0) for activity in work_activities)
        scheduled_cost = sum(
            float(activity.cost or 0) for activity in scheduled_cost_activities
        )
        direct_cost = work_cost + scheduled_cost
        subcontracted_cost = sum(
            float(activity.cost or 0) * float(activity.subcontracted or 0)
            for activity in work_activities
        )
        self_performed_cost = work_cost - subcontracted_cost
        total_inflow = round(sum(calculator.inflow()), 2) if active_activities else 0.0
        final_cash_balance = (
            snapshot["outflow_with_interest"][-1]
            if snapshot["outflow_with_interest"]
            else 0.0
        )

        facility_rows = snapshot.get("facility_rows", [])
        total_facility_interest = round(sum(snapshot.get("facility_interest", [])), 2)
        total_facility_fees = round(sum(snapshot.get("facility_fees", [])), 2)
        financing_cost = round(total_facility_interest + total_facility_fees, 2)
        total_cost = round(direct_cost + financing_cost, 2)

        pre_finance = snapshot.get("pre_financing_balance")
        if pre_finance is None:
            running = 0.0
            pre_finance = []
            for value in snapshot.get("netflow", []):
                running += float(value or 0)
                pre_finance.append(round(running, 2))
        lowest_balance = min(pre_finance, default=0.0)
        lowest_period = pre_finance.index(lowest_balance) if pre_finance else None

        combined_outstanding = []
        if facility_rows:
            horizon = max(
                (len(row.get("outstanding", [])) for row in facility_rows),
                default=0,
            )
            for period in range(horizon):
                combined_outstanding.append(sum(
                    float(row.get("outstanding", [])[period])
                    if period < len(row.get("outstanding", []))
                    else 0.0
                    for row in facility_rows
                ))
        peak_facility_outstanding = max(combined_outstanding, default=0.0)
        final_facility_outstanding = (
            combined_outstanding[-1] if combined_outstanding else 0.0
        )
        cash_after_debt_settlement = (
            float(final_cash_balance) - final_facility_outstanding
        )

        summary = {
            "total_inflow": round(total_inflow, 2),
            "work_cost": round(work_cost, 2),
            "scheduled_cost": round(scheduled_cost, 2),
            "subcontracted_cost": round(subcontracted_cost, 2),
            "self_performed_cost": round(self_performed_cost, 2),
            "direct_cost": round(direct_cost, 2),
            "financing_cost": financing_cost,
            "total_cost": total_cost,
            "total_facility_interest": total_facility_interest,
            "total_facility_fees": total_facility_fees,
            "minimum_pre_financing_balance": round(lowest_balance, 2),
            "minimum_pre_financing_period": lowest_period,
            "peak_pre_financing_need": round(max(0.0, -lowest_balance), 2),
            "peak_pre_financing_period": lowest_period,
            "peak_facility_outstanding": round(peak_facility_outstanding, 2),
            "final_facility_outstanding": round(final_facility_outstanding, 2),
            "final_cash_balance": round(final_cash_balance, 2),
            "cash_after_debt_settlement": round(cash_after_debt_settlement, 2),
            "work_duration": snapshot["duration"],
            "dlp": self.dlp or 0,
            "financial_horizon": len(snapshot["outflow_with_interest"]),
            "contractor_contribution": 0.0,
            "peak_unfunded_shortfall": round(max(
                0.0, -min(snapshot["outflow_with_interest"], default=0.0)
            ), 2),
        }
        if facility_rows:
            unfunded = snapshot.get("unfunded_shortfall", [])
            summary.update({
                "contractor_contribution": round(sum(
                    sum(row["draw"])
                    for row in facility_rows
                    if row["type"].casefold() in {
                        "owner's injection",
                        "contractor contribution",
                    }
                ), 2),
                "peak_unfunded_shortfall": round(max(unfunded, default=0.0), 2),
            })

        if not include_details:
            contract_fields = (
                "contract_value", "advance", "retention", "release_retention_eop",
                "dlp", "duration_for_payment",
            )
            forecast_fields = (
                "wieb", "interest_rate", "use_independent_inflow_curve",
                "inflow_curve_type", "inflow_curve_skew",
            )
            facility_fields = (
                "id", "name", "type", "limit", "interest_rate", "fees",
                "draw_method", "repayment_method", "advance_portion",
                "repayment_percent", "revolving", "start", "end",
                "sweep_priority", "installment_start", "installment_interval",
                "installment_count",
            )
            return {
                "id": self.id, "unit_id": self.unit_id, "name": self.name,
                "summary": summary,
                "properties": {
                    "contract": {key: getattr(self, key) for key in contract_fields},
                    "forecast": {key: getattr(self, key) for key in forecast_fields},
                    "activity_counts": {
                        "total": len(active_activities), "work": len(work_activities),
                        "scheduled_cost": len(scheduled_cost_activities),
                    },
                    "financing": [
                        {key: facility[key] for key in facility_fields if key in facility}
                        for facility in (self.financing_facilities or [])
                    ],
                    "units": {
                        "percentages": "fraction", "period_index_base": 0,
                        "period_unit": "model_period", "amount_unit": "project_currency",
                        "interest_rate_basis": "per_model_period",
                        "periods_per_year": None,
                    },
                },
            }

        activities = []
        for activity in active_activities:
            data = activity.as_dict()
            data["cash_flow_json"] = calculator.activity_cashflows[activity.id]
            activities.append(data)
        data = super().as_dict()
        data.update({
            "activities": activities,
            **snapshot,
            "summary": summary,
        })
        return data
