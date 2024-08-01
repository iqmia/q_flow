'''
the init_app method is called in the __init__.py file of this package
before running the init_app of the other extensions. This is because the other
extensions depend on the storage directory.

This module contains the FileSys class which is responsible for saving files to
the storage directory.

in the init_app method, the storage directory is created if it doesn't exist and
loads the secret keys from the env.q file in the storage directory.
'''

from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename
import os
from flask import Flask, json

from q_flow.exceptions import InvalidData, Keys_Not_Found
from q_flow.services.utils import gen_id

class FileSys:
    def __init__(self):
        self.app = None
        self.storage_dir = None
        self.private_key_path = None

    def init_app(self, app: Flask):
        '''
        Initialize the FileSys class with the app instance. Create the storage
        directory if it doesn't exist and sets the database uri.
        IMPORTANT: This method should be called before any other extension is
        initialized in the __init__.py file of the package
        '''
        self.app = app

        # create the storage directory if it doesn't exist
        self.storage_dir = app.config.get("STORAGE_PATH")
        print(self.storage_dir)
        if not os.path.exists(self.storage_dir):
            os.makedirs(self.storage_dir)

        self.project_photos = os.path.join(
            self.storage_dir, app.config.get("PROJECT_PHOTOS"))
        if not os.path.exists(self.project_photos):
            os.makedirs(self.project_photos)

        # set the database uri
        app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{self.storage_dir}/q_flow.db'

    def allowed_image(self, filename: str):
        return '.' in filename and \
            filename.rsplit('.', 1)[1].lower() in \
                self.app.config.get("ALLOWED_IMAGES")

    def save_project_photo(self, image: FileStorage, project) -> str:
        '''
        Delete the current photo if it exists and save the new logo
        '''
        # check if the file is an image of acceptable type
        if not image:
            return None

        InvalidData.require_condition(
            self.allowed_image(image.filename),
            "Invalid file type"
        )

        if project.photo:
            photo_path = os.path.join(self.project_photos, project.photo)
            if os.path.exists(photo_path):
                os.remove(photo_path)
        new_photo_name = secure_filename(image.filename)
        new_photo_path = os.path.join(self.project_photos, new_photo_name)

        while os.path.exists(new_photo_path):
            new_photo_name = self.__update_filename(new_photo_name)
            new_photo_path = os.path.join(self.project_photos, new_photo_name)
        image.save(new_photo_path)
        return new_photo_name

    def __update_filename(self, file_name: str):
        '''
        Update the name of the file by adding a unique id to the name
        '''
        filename, file_extension = os.path.splitext(file_name)
        return f"{filename}_{gen_id()[:5]}{file_extension}"