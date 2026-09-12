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
        cashflow_id = r.json["data"]["cashflows"][0]["id"]
        self.project = Project.query.get(cashflow_id)

    def test_new_activity(self):
        '''Test the new activity route'''
        print(self.project.id)
        r = self.client.post(f"/new_activity/{self.project.id}",
                headers={"Authorization": "Bearer test"},
                json={"name": "activity 1", "cost": 1000, "duration": 4})
        print(r.data)
        assert r.status_code == 201
        assert r.json.get("data").get("name") == "activity 1"


    def test_new_missing_name_and_cost(self):
        '''Test case: Missing name and cost'''
        r = self.client.post(f"/new_activity/{self.project.id}",
                headers={"Authorization": "Bearer test"},
                json={})
        print(r.data)
        assert r.status_code == 400

    def test_new_missing_name(self):
        '''Test case: Missing name'''
        r = self.client.post(f"/new_activity/{self.project.id}",
                headers={"Authorization": "Bearer test"},
                json={"cost": 1000})
        print(r.data)
        assert r.status_code == 400

    def test_new_missing_cost(self):
        '''Test case: Missing cost'''
        r = self.client.post(f"/new_activity/{self.project.id}",
                headers={"Authorization": "Bearer test"},
                json={"name": "activity 1"})
        print(r.data)
        assert r.status_code == 400

    def test_new_invalid_project_id(self):
        '''Test case: Invalid project ID'''
        r = self.client.post("/new_activity/invalid_id",
                headers={"Authorization": "Bearer test"},
                json={"name": "activity 1", "cost": 1000, "duration": 4})
        print(r.data)
        assert r.status_code == 404

    def test_new_invalid_authorization_token(self):
        '''Test case: Invalid authorization token'''
        r = self.client.post(f"/new_activity/{self.project.id}",
                headers={"Auth": "Bearer "},
                json={"name": "activity 1", "cost": 1000, "duration": 4})
        print(r.data)
        assert r.status_code == 403

    def test_get_activity(self):
        '''Test the get activity route'''
        r = self.client.post(f"/new_activity/{self.project.id}",
                headers={"Authorization": "Bearer test"},
                json={"name": "activity 1", "cost": 1000, "duration": 4})
        activity_id = r.json.get("data").get("id")
        r = self.client.get(f"/activity/{activity_id}",
                headers={"Authorization": "Bearer test"})
        print(r.data)
        assert r.status_code == 200
        assert r.json.get("data").get("name") == "activity 1"

    def test_get_activity_invalid_activity_id(self):
        '''Test case: Invalid activity ID'''
        r = self.client.get("/activity/invalid_id",
                headers={"Authorization": "Bearer test"})
        print(r.data)
        assert r.status_code == 403

    def test_get_activity_missing_authorization_token(self):
        '''Test case: Missing authorization token'''
        r = self.client.get(f"/activity/activity_id")
        print(r.data)
        assert r.status_code == 403

    def test_get_activity_already_deleted(self):
        '''Test case: activity deleted'''
        r = self.client.post(f"/new_activity/{self.project.id}",
                headers={"Authorization": "Bearer test"},
                json={"name": "activity 1", "cost": 1000, "duration": 4})
        activity_id = r.json.get("data").get("id")
        Activity.query.get(activity_id).delete()
        r = self.client.get(f"/activity/{activity_id}",
                headers={"Authorization": "Bearer test"})
        print(r.data)
        assert r.status_code == 403

    def test_update_activity(self):
        '''
        Test the update activity route
        '''
        r = self.client.post(f"/new_activity/{self.project.id}",
                headers={"Authorization": "Bearer test"},
                json={"name": "activity 1", "cost": 1000, "duration": 4, "advance": 0.2})
        activity_id = r.json.get("data").get("id")
        r = self.client.put(f"/update_activity/{activity_id}",
                headers={"Authorization": "Bearer test"},
                json={"name": "activity 2", "cost": 2000, "duration": 4})
        print(r.data)
        assert r.status_code == 200
        assert r.json.get("data").get("name") == "activity 2"
        assert r.json.get("data").get("cost") == 2000
        assert r.json.get("data").get("advance") == 0.2

    def test_update_activity_invalid_activity_id(self):
        '''
        Test case: Invalid activity ID
        '''
        r = self.client.put("/update_activity/invalid_id",
                headers={"Authorization": "Bearer test"},
                json={"name": "activity 2", "cost": 2000, "duration": 4})
        print(r.data)
        assert r.status_code == 403

    def test_update_activity_invalid_data_type(self):
        r = self.client.post(f"/new_activity/{self.project.id}",
                headers={"Authorization": "Bearer test"},
                json={"name": "activity 1", "cost": 1000, "duration": 4, "advance": 0.2})
        activity_id = r.json.get("data").get("id")
        r = self.client.put(f"/update_activity/{activity_id}",
                headers={"Authorization": "Bearer test"},
                json={"name": "activity 2", "cost": "lalas", "duration": 4})
        print(r.data)
        print(r.status_code)
        assert r.status_code == 400

    def test_update_deleted_activity(self):
        '''Test case: Activity deleted'''
        r = self.client.post(f"/new_activity/{self.project.id}",
                headers={"Authorization": "Bearer test"},
                json={"name": "activity 1", "cost": 1000, "duration": 4})
        activity_id = r.json.get("data").get("id")
        Activity.query.get(activity_id).delete()
        r = self.client.put(f"/update_activity/{activity_id}",
                headers={"Authorization": "Bearer test"},
                json={"name": "activity 2", "cost": 2000, "duration": 4})
        print(r.data)
        assert r.status_code == 403

    def test_delete_activity(self):
        '''Test the delete activity route'''
        r = self.client.post(f"/new_activity/{self.project.id}",
                headers={"Authorization": "Bearer test"},
                json={"name": "activity 1", "cost": 1000, "duration": 4})
        activity_id = r.json.get("data").get("id")
        r = self.client.delete(f"/delete_activity/{activity_id}",
                headers={"Authorization": "Bearer test"})
        print(r.data)
        assert r.status_code == 200
        assert r.json.get("message") == "Activity deleted successfully"

    def test_hard_delete_activity(self):
        '''Test the hard delete activity route'''
        r = self.client.post(f"/new_activity/{self.project.id}",
                headers={"Authorization": "Bearer test"},
                json={"name": "activity 1", "cost": 1000, "duration": 4})
        activity_id = r.json.get("data").get("id")
        r = self.client.delete(f"/hard_delete_activity/{activity_id}",
                headers={"Authorization": "Bearer test"})
        print(r.data)
        del_activity = Activity.query.get(activity_id)
        assert r.status_code == 200
        assert del_activity is None

    def test_hard_delete_deleted_activity(self):
        '''Test case: Activity deleted'''
        r = self.client.post(f"/new_activity/{self.project.id}",
                headers={"Authorization": "Bearer test"},
                json={"name": "activity 1", "cost": 1000, "duration": 4})
        activity_id = r.json.get("data").get("id")
        Activity.query.get(activity_id).delete()
        r = self.client.delete(f"/hard_delete_activity/{activity_id}",
                headers={"Authorization": "Bearer test"})
        print(r.data)
        assert r.status_code == 200

    def test_restore_activity(self):
        '''Test the restore activity route'''
        r = self.client.post(f"/new_activity/{self.project.id}",
                headers={"Authorization": "Bearer test"},
                json={"name": "activity 1", "cost": 1000, "duration": 4})
        activity_id = r.json.get("data").get("id")
        Activity.query.get(activity_id).delete()
        r = self.client.put(f"/restore_activity/{activity_id}",
                headers={"Authorization": "Bearer test"})
        print(r.data)
        assert r.status_code == 200


    def _create_activity(self, **overrides):
        payload = {"name": "activity 1", "cost": 1000, "duration": 4}
        payload.update(overrides)
        return self.client.post(
            f"/new_activity/{self.project.id}",
            headers={"Authorization": "Bearer test"},
            json=payload,
        )

    def _assert_snapshot(self, response, activity_count):
        cashflow = response.json["cashflow"]
        assert len(cashflow["activities"]) == activity_count
        assert set((
            "workflow",
            "inflow",
            "outflow",
            "netflow",
            "outflow_with_interest",
            "duration",
        )).issubset(cashflow)

    def test_activity_mutations_return_authoritative_cashflow(self):
        created = self._create_activity(
            activity_type="linear",
            duration=2,
            mobilization_period=0,
            subcontracted=0,
        )
        assert created.status_code == 201
        self._assert_snapshot(created, 1)
        activity_id = created.json["data"]["id"]
        marginal = created.json["cashflow"]["activities"][0]["cash_flow_json"]
        assert marginal["marginal_work"] == [500.0, 500.0]
        assert marginal["marginal_out_flow"] == [500.0, 500.0, 0.0, 0.0]

        updated = self.client.put(
            f"/update_activity/{activity_id}",
            headers={"Authorization": "Bearer test"},
            json={
                "name": "updated",
                "cost": 2000,
                "duration": 2,
                "activity_type": "linear",
                "mobilization_period": 0,
                "subcontracted": 0,
            },
        )
        assert updated.status_code == 200
        self._assert_snapshot(updated, 1)
        assert updated.json["cashflow"]["workflow"] == [1000.0, 1000.0]

        deleted = self.client.delete(
            f"/delete_activity/{activity_id}",
            headers={"Authorization": "Bearer test"},
        )
        assert deleted.status_code == 200
        self._assert_snapshot(deleted, 0)
        assert deleted.json["cashflow"]["workflow"] == []

        restored = self.client.put(
            f"/restore_activity/{activity_id}",
            headers={"Authorization": "Bearer test"},
        )
        assert restored.status_code == 200
        self._assert_snapshot(restored, 1)

    def test_restore_activities_returns_affected_cashflow_snapshots(self):
        first = self._create_activity(name="first").json["data"]["id"]
        second = self._create_activity(name="second").json["data"]["id"]
        Activity.query.get(first).delete()
        Activity.query.get(second).delete()

        response = self.client.put(
            "/restore_activities",
            headers={"Authorization": "Bearer test"},
            json={"data": [first, second]},
        )

        assert response.status_code == 200
        assert len(response.json["cashflows"]) == 1
        assert len(response.json["cashflows"][0]["activities"]) == 2

    def test_invalid_activity_create_is_rolled_back(self):
        before = Activity.query.count()

        response = self._create_activity(skew=1)

        assert response.status_code == 400
        assert Activity.query.count() == before

    def test_invalid_activity_update_is_rolled_back(self):
        created = self._create_activity()
        activity_id = created.json["data"]["id"]

        response = self.client.put(
            f"/update_activity/{activity_id}",
            headers={"Authorization": "Bearer test"},
            json={
                "name": "should not persist",
                "cost": 2000,
                "duration": 4,
                "skew": -1,
            },
        )

        assert response.status_code == 400
        activity = Activity.query.get(activity_id)
        assert activity.name == "activity 1"
        assert activity.cost == 1000
        assert activity.skew == 0

    def test_negative_duration_is_rejected_without_persisting(self):
        before = Activity.query.count()

        response = self._create_activity(duration=-1)

        assert response.status_code == 400
        assert Activity.query.count() == before
