from os import path
from flask import json


from q_flow.exceptions import Keys_Not_Found
from q_flow.services.utils import get_env


class Config(object):
    '''
    app configurations
    '''
    APP_NAME = 'QFLOW'

    # Flask settings
    DEBUG = False
    TESTING = False
    LOG_LEVEL = 'DEBUG'  # CRITICAL / ERROR / WARNING / INFO / DEBUG

    # Folders and Files
    STORAGE_PATH = '/home/iqmieeuk/q_flow/main_storage'  # full path to the storage directory
    PROJECT_PHOTOS = 'project_photos' # in the STORAGE_PATH (see file_sys.py)
    ALLOWED_IMAGES = {
        'png', 'jpg', 'jpeg', 'gif', 'webp', 'tiff', 'bmp', 'svg', 'ico'
        }

    # Database settings
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # the database uri is set in the file_sys.py so we comment it here
    # SQLALCHEMY_DATABASE_URI = f'sqlite:////q_auth.db'

    # Email settings
    MAIL_SERVER = 'premium106.web-hosting.com'
    MAIL_PORT = 465
    MAIL_USE_SSL = True
    MAIL_USERNAME = 'noreply@snaghere.com'
    MAIL_DEBUG = False
    MAIL_DEFAULT_SENDER = 'noreply@snaghere.com'
    MAIL_ALLOWED_RETRIES = 3
    MAIL_DOMAIN = 'snaghere.com'

    # JWT settings
    USER_API_URL = 'https://quollnet.com/api/user/'
    GOOGLE_DISCOVERY_URL = 'https://accounts.google.com/.well-known/openid-configuration'

    # Load secret keys from file
    ENV_FILE = 'env.json'
    data = get_env(ENV_FILE)
    SECRET_KEY = data.get('SECRET_KEY', '')
    MAIL_PASSWORD = data.get('MAIL_PASSWORD', '')
    APP_ID = data.get('APP_ID', '')
    PUBLIC_KEY = data.get('PUBLIC_KEY', '')
    ALGO = data.get('ALGO', '')
    GOOGLE_CLIENT_ID = data.get('GOOGLE_CLIENT_ID', '')
    GOOGLE_CLIENT_SECRET = data.get('GOOGLE_CLIENT_SECRET', '')

class LocalConfig(Config):
    '''
    Local configurations
    '''
    DEBUG = True
    TESTING = False
    STORAGE_PATH = 'c:/user/esaad/code/q_flow/main_storage'
    USER_API_URL = 'http://localhost:5000/user/'
    # USER_API_URL = 'https://quollnet.com/api/user'
    
    # Load secret keys from file
    # ENV_FILE = 'env_local.json'
    ENV_FILE = 'env_local.json'
    data = get_env(ENV_FILE)
    SECRET_KEY = data.get('SECRET_KEY', '')
    MAIL_PASSWORD = data.get('MAIL_PASSWORD', '')
    APP_ID = data.get('APP_ID', '')
    PUBLIC_KEY = data.get('PUBLIC_KEY', '')
    ALGO = data.get('ALGO', '')

class TestConfig(Config):
    '''
    Test configurations
    '''
    TESTING = True
    STORAGE_PATH = 'c:/user/esaad/code/q_flow/test_storage'
    JWT_EXP_DELTA_SECONDS = 60

    USER_API_URL = 'http://localhost:5000/user'

    # Load secret keys from file
    ENV_FILE = 'env_test.json'
    data = get_env(ENV_FILE)
    SECRET_KEY = data.get('SECRET_KEY', '')
    MAIL_PASSWORD = data.get('MAIL_PASSWORD', '')
    APP_ID = data.get('APP_ID', '')
    PUBLIC_KEY = data.get('PUBLIC_KEY', '')
    ALGO = data.get('ALGO', '')

