
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from q_flow.services.err_handler import ErrHandler
from q_flow.services.file_sys import FileSys
from q_flow.services.logger import QLogger
from q_flow.services.user_api import User_API
from flask_mail import Mail

db = SQLAlchemy()
fs = FileSys()
lg = QLogger()
u_api = User_API()
mail = Mail()
er = ErrHandler()
cors = CORS()