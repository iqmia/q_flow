
from shutil import rmtree
from flask_testing import TestCase
from q_flow import create_app
from q_flow.config import TestConfig
from q_flow.extensions import db, fs

class Base(TestCase):
    def create_app(self):
        print("setting up base test")

        app = create_app(TestConfig)
        print(TestConfig)
        return app

    def setUp(self):
        print("setting up creating db")
        self.app = self.create_app()

    def tearDown(self):
        '''
        Clean up after each test
        '''
        # empty database
        db.session.remove()
        db.drop_all()

        # delete storage
        rmtree(fs.storage_dir, ignore_errors=True)
