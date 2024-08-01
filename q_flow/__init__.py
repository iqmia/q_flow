'''
This file is the entry point of the application. It creates the Flask app and
initializes the extensions.
The file env.json is used to store the secret keys
1. Secure-Key: This key is used to secure the application. It is used in the
    only_with_permission decorator to restrict access to certain routes.
2. SECRET_KEY: This key is used by flask to secure the session.
'''

from flask import Config, Flask
from q_flow.command import create_cf
from q_flow.extensions import db, fs, lg, u_api, mail, er, cors

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    fs.init_app(app)
    db.init_app(app)
    lg.init_app(app)
    u_api.init_app(app)
    mail.init_app(app)
    er.init_app(app)
    cors.init_app(app)
    app.cli.add_command(create_cf)


    from q_flow.routes.projects import projects
    from q_flow.routes.activities import activities
    from q_flow.routes.users import users
    app.register_blueprint(projects)
    app.register_blueprint(activities)
    app.register_blueprint(users)

    with app.app_context():
        db.create_all()

    return app