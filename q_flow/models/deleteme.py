
    # @staticmethod
    # def from_dict(data, user_id):
    #     '''
    #     Creates a new Activity object from a dictionary
    #     '''
    #     activity = Activity()
    #     activity.id = gen_id()
    #     activity.name = data.get("name", "")
    #     activity.created_by = data.get("created_by", user_id)
    #     activity.updated_by = data.get("updated_by", user_id)
    #     activity.project_id = data.get("project_id", "")
    #     activity.activity_type = data.get("activity_type", ActivityType.GENERAL)
    #     activity.cost = data.get("cost", 0.0)
    #     activity.duration_units = data.get("duration_units", "Months")
    #     activity.duration = data.get("duration", 1)
    #     activity.start = data.get("start", 0)
    #     activity.advance = data.get("advance", 0.1)
    #     activity.retention = data.get("retention", 0.1)
    #     activity.dlp = data.get("dlp", 0)
    #     activity.duration_for_payment = data.get("duration_for_payment", 1)
    #     activity.work_in_excess = data.get("work_in_excess", 0.1)
    #     activity.mobilization = data.get("mobilization", 0.01)
    #     activity.mobilization_period = data.get("mobilization_period", 1)
    #     activity.profit = data.get("profit", 0.1)
    #     activity.subcontracted = data.get("subcontracted", 0.7)
    #     activity.subcontractors_retention = data.get("subcontractors_retention", 0.1)
    #     activity.interest_rate = data.get("interest_rate", 0.005)
    #     activity.compounding_period = data.get("compounding_period", 1)
    #     activity.skew = data.get("skew", 0.0)
    #     activity.no_billing_period = data.get("no_billing_period", 0)
    #     activity.cashflowJson = data.get("cashflowJson", "")
    #     return activity

    # def fromDictUpdate(self, data):
    #     '''
    #     Updates an existing Activity object from a dictionary
    #     '''
    #     self.name = data.get("name", "")
    #     self.project_id = data.get("project_id", "")
    #     self.activity_type = data.get("activity_type", ActivityType.GENERAL.value)
    #     self.cost = data.get("cost", 0.0)
    #     self.duration_units = data.get("duration_units", "Months")
    #     self.duration = data.get("duration", 1)
    #     self.start = data.get("start", 0)
    #     self.advance = data.get("advance", 0.1)
    #     self.retention = data.get("retention", 0.1)
    #     self.dlp = data.get("dlp", 0)
    #     self.duration_for_payment = data.get("duration_for_payment", 1)
    #     self.work_in_excess = data.get("work_in_excess", 0.1)
    #     self.mobilization = data.get("mobilization", 0.01)
    #     self.mobilization_period = data.get("mobilization_period", 1)
    #     self.profit = data.get("profit", 0.1)
    #     self.subcontracted = data.get("subcontracted", 0.7)
    #     self.subcontractors_retention = data.get("subcontractors_retention", 0.1)
    #     self.interest_rate = data.get("interest_rate", 0.005)
    #     self.compounding_period = data.get("compounding_period", 1)
    #     self.skew = data.get("skew", 0.0)
    #     self.no_billing_period = data.get("no_billing_period", 0)
    #     self.cashflowJson = data.get("cashflowJson", "")
    #     return self

    # def as_dict_hard(self):
    #     return {
    #         'id': self.id,
    #         'name': self.name,
    #         'created_on': self.created_on,
    #         'created_by': self.created_by,
    #         'project_id': self.project_id,
    #         'activity_type': self.activity_type,
    #         'cost': self.cost,
    #         'duration_units': self.duration_units,
    #         'duration': self.duration,
    #         'start': self.start,
    #         'advance': self.advance,
    #         'retention': self.retention,
    #         'dlp': self.dlp,
    #         'duration_for_payment': self.duration_for_payment,
    #         'work_in_excess': self.work_in_excess,
    #         'mobilization': self.mobilization,
    #         'mobilization_period': self.mobilization_period,
    #         'profit': self.profit,
    #         'subcontracted': self.subcontracted,
    #         'subcontractors_retention': self.subcontractors_retention,
    #         'interest_rate': self.interest_rate,
    #         'compounding_period': self.compounding_period,
    #         'skew': self.skew,
    #         'no_billing_period': self.no_billing_period,
    #         'cashflowJson': self.cashflowJson
    #         }