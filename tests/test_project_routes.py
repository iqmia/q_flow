
from io import BytesIO
import os
import re
from flask_testing import TestCase
from q_flow.models.project import Project
from tests.base import Base
from q_flow.extensions import fs


class Test_project_routes(Base, TestCase):
    '''
    Test the project routes
    '''
    def setUp(self):
        '''
        Set up the test client
        '''
        print("setting up test")
        super().setUp()

    def test_project_routes(self):
        '''
        Test the project routes
        '''
        resp = self.client.get('/projects',
            headers={'Authorization': 'Bearer test_token'})
        print(resp.data)
        self.assert200(resp)


    def test_new_project(self):
        '''
        Test the new project route
        '''
        resp = self.client.post('/new_project',
            headers={'Authorization': 'Bearer test_token'},
            json={'name': 'test_project', 'description': 'test description'})
        print(resp.json)
        assert resp.status_code == 201
        assert b'test_project' in resp.data
        assert b'test description' in resp.data

    def test_new_project_missing_data(self):
        '''
        Test the new project route with missing data
        '''
        resp = self.client.post('/new_project',
            headers={'Authorization': 'Bearer test_token'},
            json={'description': 'test_project'})
        print(resp.data)
        assert resp.status_code == 400
        assert b'Missing' in resp.data

    def test_new_project_with_photo(self):
        '''
        Test the new project route with photo
        '''
        file_path = "tests/test.jpg"
        with open(file_path, "rb") as file:
            img_data = BytesIO(file.read())
        resp = self.client.post('/new_project',
            headers={'Authorization': 'Bearer test_token'},
            data={'name': 'test_project', 'description': 'test description',
                'photo': [(img_data, "test_photo.jpg")]})
        print(resp.data)
        assert os.path.exists(os.path.join(fs.project_photos, "test_photo.jpg"))
        assert resp.status_code == 201
        assert b'test_project' in resp.data
        assert b'test description' in resp.data
        assert b'test_photo' in resp.data

    def test_new_project_no_auth(self):
        '''
        Test the new project route without auth
        '''
        resp = self.client.post('/new_project',
            json={'name': 'test_project', 'description': 'test description'})
        print(resp.data)
        assert resp.status_code == 403
        assert b'Missing' in resp.data

    def test_get_project(self):
        project = Project(
            name='test_project', description='test description',
            created_by = '1').commit()
        resp = self.client.get(f'/project/{project.id}',
                headers={'Authorization': 'Bearer test_token'})
        print(resp.data)
        assert resp.status_code == 200
        assert b'test_project' in resp.data
        assert b'test description' in resp.data

    def test_get_project_no_auth(self):
        project = Project(
            name='test_project', description='test description',
            created_by='2').commit()
        
        resp = self.client.get(f'/project/{project.id}')
        print(resp.data)
        assert resp.status_code == 403
        assert b'Missing' in resp.data

    def test_get_project_not_found(self):
        resp = self.client.get('/project/1',
            headers={'Authorization': 'Bearer test_token'})
        print(resp.data)
        assert resp.status_code == 404
        assert b'not found' in resp.data

    def test_get_project_permission_denied(self):
        project = Project(
            name='test_project', description='test description',
            created_by='2').commit()
        resp = self.client.get(f'/project/{project.id}',
            headers={'Authorization': 'Bearer test_token'})
        print(resp.data)
        assert resp.status_code == 403
        assert b'Permission' in resp.data

    def test_update_project(self):
        project = Project(
            name='test_project', description='test description',
            created_by='1').commit()
        resp = self.client.put(f'/update_project/{project.id}',
            headers={'Authorization': 'Bearer test_token'},
            json={'name': 'updated_project', 'description': 'updated description'})
        print(resp.data)
        assert resp.status_code == 200
        assert b'updated_project' in resp.data
        assert b'updated description' in resp.data

    def test_update_project_with_photo(self):
        project = Project(
            name='test_project', description='test description',
            created_by='1').commit()
        file_path = "tests/test.jpg"
        with open(file_path, "rb") as file:
            img_data = BytesIO(file.read())
        resp = self.client.put(f'/update_project/{project.id}',
            headers={'Authorization': 'Bearer test_token'},
            data={'name': 'updated_project', 'description': 'updated description',
                'photo': [(img_data, "test_photo.jpg")]})
        print(resp.data)
        assert os.path.exists(os.path.join(fs.project_photos, "test_photo.jpg"))
        assert resp.status_code == 200
        assert b'updated_project' in resp.data
        assert b'updated description' in resp.data
        assert b'test_photo' in resp.data

    def test_update_project_no_auth(self):
        project = Project(
            name='test_project', description='test description',
            created_by='2').commit()
        resp = self.client.put(f'/update_project/{project.id}',
            json={'name': 'updated_project', 'description': 'updated description'})
        print(resp.data)
        assert resp.status_code == 403
        assert b'Missing' in resp.data

    def test_update_project_not_found(self):
        resp = self.client.put('/update_project/1',
            headers={'Authorization': 'Bearer test_token'},
            json={'name': 'updated_project', 'description': 'updated description'})
        print(resp.data)
        assert resp.status_code == 404
        assert b'not found' in resp.data

    def test_delete_project(self):
        project = Project(
            name='test_project', description='test description',
            created_by='1').commit()
        resp = self.client.delete(f'/delete_project/{project.id}',
            headers={'Authorization': 'Bearer test_token'})
        print(resp.data)
        assert resp.status_code == 200
        assert b'deleted' in resp.data

    def test_delete_project_no_auth(self):
        project = Project(
            name='test_project', description='test description',
            created_by='2').commit()
        resp = self.client.delete(f'/delete_project/{project.id}')
        print(resp.data)
        assert resp.status_code == 403
        assert b'Missing' in resp.data

    def test_delete_project_not_found(self):
        resp = self.client.delete('/delete_project/1',
            headers={'Authorization': 'Bearer test_token'})
        print(resp.data)
        assert resp.status_code == 404
        assert b'not found' in resp.data

    def test_restore_project(self):
        project = Project(
            name='test_project', description='test description',
            created_by='1', is_deleted=True).commit()
        resp = self.client.put(f'/restore_project/{project.id}',
            headers={'Authorization': 'Bearer test_token'})
        print(resp.data)
        assert resp.status_code == 200
        assert b'restored' in resp.data

    def test_restore_project_no_auth(self):
        project = Project(
            name='test_project', description='test description',
            created_by='2', is_deleted=True).commit()
        resp = self.client.put(f'/restore_project/{project.id}')
        print(resp.data)
        assert resp.status_code == 403
        assert b'Missing' in resp.data

    def test_restore_project_not_found(self):
        resp = self.client.put('/restore_project/1',
            headers={'Authorization': 'Bearer test_token'})
        print(resp.data)
        assert resp.status_code == 404
        assert b'not found' in resp.data

    def test_restore_project_not_deleted(self):
        project = Project(
            name='test_project', description='test description',
            created_by='1').commit()
        resp = self.client.put(f'/restore_project/{project.id}',
            headers={'Authorization': 'Bearer test_token'})
        print(resp.data)
        assert resp.status_code == 400
        assert b'not deleted' in resp.data

    def test_hard_delete_project(self):
        project = Project(
            name='test_project', description='test description',
            created_by='1').commit()
        resp = self.client.delete(f'/hard_delete_project/{project.id}',
            headers={'Authorization': 'Bearer test_token'})
        print(resp.data)
        test_project = Project.query.get(project.id)
        assert test_project is None
        assert resp.status_code == 200
        assert b'hard deleted' in resp.data

    def test_hard_delete_project_no_auth(self):
        project = Project(
            name='test_project', description='test description',
            created_by='2').commit()
        resp = self.client.delete(f'/hard_delete_project/{project.id}')
        print(resp.data)
        assert resp.status_code == 403
        assert b'Missing' in resp.data

    def test_hard_delete_project_not_found(self):
        resp = self.client.delete('/hard_delete_project/1',
            headers={'Authorization': 'Bearer test_token'})
        print(resp.data)
        assert resp.status_code == 404
        assert b'not found' in resp.data

    def test_hard_delete_project_permission_denied(self):
        project = Project(
            name='test_project', description='test description',
            created_by='2').commit()
        resp = self.client.delete(f'/hard_delete_project/{project.id}',
            headers={'Authorization': 'Bearer test_token'})
        print(resp.data)
        assert resp.status_code == 403
        assert b'Permission' in resp.data

    def test_create_projects_pagination(self):
        '''
        Test creating 14 projects to test pagination
        '''
        for i in range(14):
            resp = self.client.post('/new_project',
                headers={'Authorization': 'Bearer test_token'},
                json={'name': f'test_project_{i}', 'description': f'test description {i}'})
            print(resp.data)
            assert resp.status_code == 201
            assert f'test_project_{i}'.encode() in resp.data
            assert f'test description {i}'.encode() in resp.data
        resp = self.client.get('/projects',
            headers={'Authorization': 'Bearer test_token'},
            query_string={'page': 1, 'per_page': 10})
        print(resp.data)
        assert resp.status_code == 200
        assert b'test_project_0' in resp.data
        assert b'test_project_9' in resp.data
        resp = self.client.get('/projects',
            headers={'Authorization': 'Bearer test_token'},
            query_string={'page': 2, 'per_page': 10})
        print(resp.data)
        assert resp.status_code == 200
        assert b'test_project_10' in resp.data
        assert b'test_project_13' in resp.data
        assert b'test_project_9' not in resp.data
        assert len(re.findall(b'test_project_', resp.data)) == 4


