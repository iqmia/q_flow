
from flask_testing import TestCase
from sqlalchemy import create_engine, inspect
from q_flow.extensions import u_api

from tests.base import Base

class Test_Decorators(Base, TestCase):
    def setUp(self):
        print("setting up decorators test")

    def test_user_required_fail(self):
        r = self.client.get("/qf/activities")
        print(r.data)
        self.assertEqual(r.status_code, 403)

    def test_user_required_success(self):
        print(u_api.url)
        r1 = u_api.post(
            "register",
            data={"email": "test@example.com", "password": "test"})
        print(r1.message)

        r = self.client.get("/activities",
                            headers={"Authorization": "Bearer test"})
        print(r.data)


class Test_db(Base, TestCase):
    def setUp(self):
        super().setUp()
        print("setting up db test")

    def test_db(self):
        print("testing db")
        engine = create_engine(self.app.config["SQLALCHEMY_DATABASE_URI"])
        print(self.app.config["SQLALCHEMY_DATABASE_URI"])
        inspector = inspect(engine)
        print(inspector.get_table_names())
