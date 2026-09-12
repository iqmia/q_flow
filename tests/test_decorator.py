from flask_testing import TestCase
from sqlalchemy import create_engine, inspect

from tests.base import Base


class Test_Decorators(Base, TestCase):
    def setUp(self):
        print("setting up decorators test")
        super().setUp()

    def test_user_required_fail(self):
        response = self.client.get("/activities/types")

        self.assertEqual(response.status_code, 403)
        self.verify_token_mock.assert_not_called()

    def test_user_required_success(self):
        response = self.client.get(
            "/activities/types",
            headers={"Authorization": "Bearer test"},
        )

        self.assertEqual(response.status_code, 200)
        self.verify_token_mock.assert_called_once_with("test")


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
