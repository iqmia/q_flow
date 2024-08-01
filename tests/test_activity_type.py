

from flask_testing import TestCase
from q_flow.models.activity import Activity, ActivityType
from q_flow.models.project import Project
from tests.base import Base


class Test_activity_type(Base, TestCase):
    def setUp(self):
        super().setUp()

    def test_new_activity_type(self):
        at = ActivityType.FACADE
        print(at)
        print(at.code)
        print(at.skew)
        at = ActivityType.STRUCTURE
        print(at.code)
        print(at.skew)
        print(type(at))
        
        pr = Project(name="p", created_by="1").commit()
        act = Activity(name="a", created_by="1", project_id=pr.id).commit()
        print(act.activity_type)
        
        