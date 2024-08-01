from flask import current_app
from flask_testing import TestCase

from q_flow.models.activity import Activity
from q_flow.models.project import Project
from tests.base import Base


class Test_activity_routes(Base, TestCase):
    '''Test the activity routes'''
    def setUp(self):
        '''Set up the test client and test data'''
        print("setting up test")
        super().setUp()
        r = self.client.post('/new_project',
            headers={'Authorization': 'Bearer test'},
            json={"name": "project 1"})
        self.project = Project.query.filter(Project.id==r.json.get("data").get("id")).first()

    def test_new_activity(self):
        '''Test the new activity route'''
        print(self.project.id)
        r = self.client.post(f"/qf/new_activity/{self.project.id}",
                headers={"Authorization": "Bearer test"},
                json={"name": "activity 1", "cost": 1000})
        print(r.data)
        assert r.status_code == 201
        assert r.json.get("data").get("name") == "activity 1"


    def test_new_missing_name_and_cost(self):
        '''Test case: Missing name and cost'''
        r = self.client.post(f"/qf/new_activity/{self.project.id}",
                headers={"Authorization": "Bearer test"},
                json={})
        print(r.data)
        assert r.status_code == 400

    def test_new_missing_name(self):
        '''Test case: Missing name'''
        r = self.client.post(f"/qf/new_activity/{self.project.id}",
                headers={"Authorization": "Bearer test"},
                json={"cost": 1000})
        print(r.data)
        assert r.status_code == 400

    def test_new_missing_cost(self):
        '''Test case: Missing cost'''
        r = self.client.post(f"/qf/new_activity/{self.project.id}",
                headers={"Authorization": "Bearer test"},
                json={"name": "activity 1"})
        print(r.data)
        assert r.status_code == 400

    def test_new_invalid_project_id(self):
        '''Test case: Invalid project ID'''
        r = self.client.post("/qf/new_activity/invalid_id",
                headers={"Authorization": "Bearer test"},
                json={"name": "activity 1", "cost": 1000})
        print(r.data)
        assert r.status_code == 404

    def test_new_invalid_authorization_token(self):
        '''Test case: Invalid authorization token'''
        r = self.client.post(f"/qf/new_activity/{self.project.id}",
                headers={"Auth": "Bearer "},
                json={"name": "activity 1", "cost": 1000})
        print(r.data)
        assert r.status_code == 403

    def test_get_activity(self):
        '''Test the get activity route'''
        r = self.client.post(f"/qf/new_activity/{self.project.id}",
                headers={"Authorization": "Bearer test"},
                json={"name": "activity 1", "cost": 1000})
        activity_id = r.json.get("data").get("id")
        r = self.client.get(f"/qf/activity/{activity_id}",
                headers={"Authorization": "Bearer test"})
        print(r.data)
        assert r.status_code == 200
        assert r.json.get("data").get("name") == "activity 1"

    def test_get_activity_invalid_activity_id(self):
        '''Test case: Invalid activity ID'''
        r = self.client.get("/qf/activity/invalid_id",
                headers={"Authorization": "Bearer test"})
        print(r.data)
        assert r.status_code == 403

    def test_get_activity_missing_authorization_token(self):
        '''Test case: Missing authorization token'''
        r = self.client.get(f"/qf/activity/activity_id")
        print(r.data)
        assert r.status_code == 403

    def test_get_activity_already_deleted(self):
        '''Test case: activity deleted'''
        r = self.client.post(f"/qf/new_activity/{self.project.id}",
                headers={"Authorization": "Bearer test"},
                json={"name": "activity 1", "cost": 1000})
        activity_id = r.json.get("data").get("id")
        Activity.query.get(activity_id).delete()
        r = self.client.get(f"/qf/activity/{activity_id}",
                headers={"Authorization": "Bearer test"})
        print(r.data)
        assert r.status_code == 403

    def test_update_activity(self):
        '''
        Test the update activity route
        '''
        r = self.client.post(f"/qf/new_activity/{self.project.id}",
                headers={"Authorization": "Bearer test"},
                json={"name": "activity 1", "cost": 1000, "advance": 0.2})
        activity_id = r.json.get("data").get("id")
        r = self.client.put(f"/qf/update_activity/{activity_id}",
                headers={"Authorization": "Bearer test"},
                json={"name": "activity 2", "cost": 2000})
        print(r.data)
        assert r.status_code == 200
        assert r.json.get("data").get("name") == "activity 2"
        assert r.json.get("data").get("cost") == 2000
        assert r.json.get("data").get("advance") == 0.2

    def test_update_activity_invalid_activity_id(self):
        '''
        Test case: Invalid activity ID
        '''
        r = self.client.put("/qf/update_activity/invalid_id",
                headers={"Authorization": "Bearer test"},
                json={"name": "activity 2", "cost": 2000})
        print(r.data)
        assert r.status_code == 403

    def test_update_activity_invalid_data_type(self):
        r = self.client.post(f"/qf/new_activity/{self.project.id}",
                headers={"Authorization": "Bearer test"},
                json={"name": "activity 1", "cost": 1000, "advance": 0.2})
        activity_id = r.json.get("data").get("id")
        r = self.client.put(f"/qf/update_activity/{activity_id}",
                headers={"Authorization": "Bearer test"},
                json={"name": "activity 2", "cost": "lalas"})
        print(r.data)
        print(r.status_code)
        assert r.status_code == 400

    def test_update_deleted_activity(self):
        '''Test case: Activity deleted'''
        r = self.client.post(f"/qf/new_activity/{self.project.id}",
                headers={"Authorization": "Bearer test"},
                json={"name": "activity 1", "cost": 1000})
        activity_id = r.json.get("data").get("id")
        Activity.query.get(activity_id).delete()
        r = self.client.put(f"/qf/update_activity/{activity_id}",
                headers={"Authorization": "Bearer test"},
                json={"name": "activity 2", "cost": 2000})
        print(r.data)
        assert r.status_code == 403

    def test_delete_activity(self):
        '''Test the delete activity route'''
        r = self.client.post(f"/qf/new_activity/{self.project.id}",
                headers={"Authorization": "Bearer test"},
                json={"name": "activity 1", "cost": 1000})
        activity_id = r.json.get("data").get("id")
        r = self.client.delete(f"/qf/delete_activity/{activity_id}",
                headers={"Authorization": "Bearer test"})
        print(r.data)
        assert r.status_code == 200
        assert r.json.get("message") == "Activity deleted successfully"

    def test_hard_delete_activity(self):
        '''Test the hard delete activity route'''
        r = self.client.post(f"/qf/new_activity/{self.project.id}",
                headers={"Authorization": "Bearer test"},
                json={"name": "activity 1", "cost": 1000})
        activity_id = r.json.get("data").get("id")
        r = self.client.delete(f"/qf/hard_delete_activity/{activity_id}",
                headers={"Authorization": "Bearer test"})
        print(r.data)
        del_activity = Activity.query.get(activity_id)
        assert r.status_code == 200
        assert del_activity is None

    def test_hard_delete_deleted_activity(self):
        '''Test case: Activity deleted'''
        r = self.client.post(f"/qf/new_activity/{self.project.id}",
                headers={"Authorization": "Bearer test"},
                json={"name": "activity 1", "cost": 1000})
        activity_id = r.json.get("data").get("id")
        Activity.query.get(activity_id).delete()
        r = self.client.delete(f"/qf/hard_delete_activity/{activity_id}",
                headers={"Authorization": "Bearer test"})
        print(r.data)
        assert r.status_code == 200

    def test_restore_activity(self):
        '''Test the restore activity route'''
        r = self.client.post(f"/qf/new_activity/{self.project.id}",
                headers={"Authorization": "Bearer test"},
                json={"name": "activity 1", "cost": 1000})
        activity_id = r.json.get("data").get("id")
        Activity.query.get(activity_id).delete()
        r = self.client.put(f"/qf/restore_activity/{activity_id}",
                headers={"Authorization": "Bearer test"})
        print(r.data)
        assert r.status_code == 200