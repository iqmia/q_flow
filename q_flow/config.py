from os import path

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

    # Resolve application paths from the repository root so production does
    # not depend on the process working directory.
    BASE_DIR = path.dirname(path.dirname(path.abspath(__file__)))
    ENV_FILE = path.join(BASE_DIR, 'env.json')
    data = get_env(ENV_FILE)

    # Folders and Files
    STORAGE_PATH = data.get('STORAGE_PATH') or path.join(BASE_DIR, 'main_storage')
    PROJECT_PHOTOS = 'project_photos'
    ALLOWED_IMAGES = {
        'png', 'jpg', 'jpeg', 'gif', 'webp', 'tiff', 'bmp', 'svg', 'ico'
        }

    # Database settings. DATABASE_URL is authoritative when supplied; SQLite
    # remains the fallback for lightweight/local installations.
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    DATABASE_URL = data.get('DATABASE_URL', '')
    SQLALCHEMY_DATABASE_URI = DATABASE_URL or (
        f"sqlite:///{path.join(STORAGE_PATH, 'q_flow.db')}"
    )

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

    # Secret keys loaded from env.json
    SECRET_KEY = data.get('SECRET_KEY', '')
    MAIL_PASSWORD = data.get('MAIL_PASSWORD', '')
    APP_ID = data.get('APP_ID', '')
    APP_SECRET = data.get('APP_SECRET', '')
    APP_ALGO = data.get('APP_ALGO', '')
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
    ENV_FILE = path.join(Config.BASE_DIR, 'env_local.json')
    data = get_env(ENV_FILE) if path.exists(ENV_FILE) else {}

    STORAGE_PATH = data.get('STORAGE_PATH') or path.join(Config.BASE_DIR, 'main_storage')
    DATABASE_URL = data.get('DATABASE_URL', '')
    SQLALCHEMY_DATABASE_URI = DATABASE_URL or (
        f"sqlite:///{path.join(STORAGE_PATH, 'q_flow.db')}"
    )
    USER_API_URL = 'http://localhost:5000/user/'

    SECRET_KEY = data.get('SECRET_KEY', Config.SECRET_KEY)
    MAIL_PASSWORD = data.get('MAIL_PASSWORD', Config.MAIL_PASSWORD)
    APP_ID = data.get('APP_ID', Config.APP_ID)
    APP_SECRET = data.get('APP_SECRET', Config.APP_SECRET)
    APP_ALGO = data.get('APP_ALGO', Config.APP_ALGO)
    PUBLIC_KEY = data.get('PUBLIC_KEY', Config.PUBLIC_KEY)
    ALGO = data.get('ALGO', Config.ALGO)
    GOOGLE_CLIENT_ID = data.get('GOOGLE_CLIENT_ID', Config.GOOGLE_CLIENT_ID)
    GOOGLE_CLIENT_SECRET = data.get(
        'GOOGLE_CLIENT_SECRET', Config.GOOGLE_CLIENT_SECRET
    )


class TestConfig(Config):
    '''
    Test configurations
    '''
    TESTING = True
    STORAGE_PATH = path.join(Config.BASE_DIR, 'test_storage')
    DATABASE_URL = ''
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{path.join(STORAGE_PATH, 'q_flow.db')}"
    JWT_EXP_DELTA_SECONDS = 60

    USER_API_URL = 'http://localhost:5000/user'

    # Tests mock QAuth at the application boundary. Keep deterministic,
    # non-secret values here so app initialization never depends on a local
    # env_test.json file or a running QAuth service.
    SECRET_KEY = 'test-secret-key'
    MAIL_PASSWORD = ''
    APP_ID = 'cashflowpot-test'
    PUBLIC_KEY = 'test-public-key'
    ALGO = 'RS256'
    APP_SECRET = 'test-app-secret'
    APP_ALGO = 'HS256'
