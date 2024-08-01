
from enum import Enum
from typing_extensions import deprecated
from q_flow.extensions import db
from q_flow.models.mixins import BaseMixin

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


class Activity(db.Model, BaseMixin):
    name = db.Column(db.String(64))
    cash_flow_json = db.Column(db.JSON)

    project_id = db.Column(
        db.String(64),
        db.ForeignKey('project.id'),
        nullable=False,
        )

    # The type of activity. e.g. Structure, MEP, Facade, etc.
    activity_type = db.Column(db.String(64), default=ActivityType.GENERAL.code)

    # The total selling cost of the activity.
    cost = db.Column(db.Float, default=0.0)

    # Duration Units
    duration_units = db.Column(db.String(64), default="Months")

    # time to complete the project
    duration = db.Column(db.Integer, default=4)

    # A time after the start of the project where the activity starts.
    # zero means the activity starts at the start of the project.
    start = db.Column(db.Integer, default=0)

    # A percentage of the Project Cost issued to the contractor prior to the start of work.
    advance = db.Column(db.Float, default=0.1)

    # The percent deduction applied to each invoice issued by the contractor and
    # repaid partially at the end of the project. The second part is repaid at
    # the end of the defect liability period (dlp).
    retention = db.Column(db.Float, default=0.1)

    # The percentage of the contract value retained by the client until the
    # completion of the project. the remaining amount is paid at the end of the
    # project. (eop) the remaining acount (1-eop) is paid at the end of the dlp.
    release_retention_eop = db.Column(db.Float, default=0.5)

    # The period of time after the completion of the project during which the
    # contractor is liable for any defects in the work.
    dlp = db.Column(db.Integer, default=0)

    # The period required to process the contractor's invoice and issue payment.
    duration_for_payment = db.Column(db.Integer, default=1)

    # The percentage of work completed in excess of the billed amount.
    work_in_excess = db.Column(db.Float, default=0.1)

    # Percentage of the project cost required at the start for mobilization,
    # equipment, materials and advances to subcontractors.
    mobilization = db.Column(db.Float, default=0.01)

    # The period of mobilization. The mobilization cost is distributed over
    # this period in addition total cost of  the activity.
    mobilization_period = db.Column(db.Integer, default=1)

    # Percent profit on the project.
    profit = db.Column(db.Float, default=0.1)

    # percent subcontracted
    subcontracted = db.Column(db.Float, default=0.7)

    # subcontractors' retention
    # deprecated, use retention instead
    subcontractors_retention = db.Column(db.Float, default=0.1)

    # Interest Rate per period
    # deprecated
    interest_rate = db.Column(db.Float, default=0.005)
    
    # compounding period
    # if the duration is in months, then the compounding period is in months
    # then the default default compounding_period = 1 is monthly
    # to change it to years, compounding_period = 12
    # to change it to semi-annually, compounding_period = 6
    # deprecated
    compounding_period = db.Column(db.Integer, default=1)
    
    # skew,  Skewing factor between -0.9 and +0.9
    skew = db.Column(db.Float, default=0.0)

    # no billing period. This is the period of time after the start of the
    # activity during which no billing is issued.
    no_billing_period = db.Column(db.Integer, default=0)

