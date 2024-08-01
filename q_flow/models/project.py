'''
Project Model
'''
from q_flow.extensions import db
from q_flow.services.utils import rnd_color
from q_flow.models.mixins import BaseMixin


class Project(db.Model, BaseMixin):
    name = db.Column(db.String(64))
    description = db.Column(db.String(256))
    photo = db.Column(db.String(64))
    show = db.Column(db.Boolean, default=True)
    color = db.Column(db.String(64), default=rnd_color)
    activities = db.relationship('Activity', backref='project', lazy=True)

    advance = db.Column(db.Float, default=0.1)
    retention = db.Column(db.Float, default=0.1)
    release_retention_eop = db.Column(db.Float, default=0.5 )
    dlp = db.Column(db.Integer, default=12)
    duration_for_payment = db.Column(db.Integer, default=1)
    interest_rate = db.Column(db.Float, default=0.005)
    contract_value = db.Column(db.Float, default=0)
    wieb = db.Column(db.Float, default=0.2)

    def as_dict_with_activities(self):
        from q_flow.cashflow import Project_cf
        activities = self.activities
        if activities:
            cashflow = Project_cf(self)
            inflow = cashflow.inflow()
            outflow = cashflow.outflow()
        else:
            inflow = [0.0]
            outflow = [0.0]
        as_dict = super().as_dict()
        as_dict.update(
            {
                'activities': [a.as_dict() for a in activities if not a.is_deleted],
                'inflow': inflow,
                'outflow': outflow,
                }
            )
        return as_dict
    

