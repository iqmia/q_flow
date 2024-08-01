
from tracemalloc import start
from flask_testing import TestCase
from q_flow.models.activity import Activity
from q_flow.models.project import Project
from q_flow.cashflow import Activity_cf, Project_cf
from tests.base import Base
from q_flow.extensions import fs


class Test_cashflow(Base, TestCase):
    def setUp(self):
        self.project = Project(
            name="project 1",
            created_by=1,
            advance=0.1,
            retention=0.1,
            release_retention_eop=0.5,
            dlp=12,
            duration_for_payment=3,
            contract_value=1100000,
            wieb = 0.0,
        ).commit()

        # create 5 activities
        a_costs = [100000, 150000, 250000, 300000, 200000]
        for i in range(5):
            print(f"activity {i}")
            Activity(
                project_id=self.project.id,
                name=f"activity {i}",
                created_by="1",
                cost=a_costs[i],
                start=i,
                duration=5 + 1,
                advance=0.1,
                retention=0.1,
                release_retention_eop=0.5,
                dlp=12,
                duration_for_payment=3,
                interest_rate=0.005,
                subcontracted=0.7
            ).commit()

        # generate work_flow and out_flow for each activity
        activity: Activity
        for activity in self.project.activities:
            cf: Activity_cf = Activity_cf(activity)
            cf.set_cashflow()
            activity.commit()

    def test_cashflow(self):
        project_cf = Project_cf(self.project)
        inflow = project_cf.inflow()
        outflow = project_cf.outflow()
        project_cf.printProject()
        project_cf.print_project_cashflow()
        project_cf.print_gantt()
        