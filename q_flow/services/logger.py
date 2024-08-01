import os
import logging
from logging.handlers import RotatingFileHandler
import traceback
from q_flow.exceptions import Q_ERROR

from flask import Flask

class QLogger:
    '''
    This class is used to create log files for different log levels and log messages
    it also creates a custom error handler for the Q_Error exception
    '''
    def __init__(self):
        self.lg = logging.getLogger(__name__)

    def init_app(self, app: Flask):
        self.logFolder = app.config.get('LOG_FOLDER', 'logs')
        self.lg.setLevel(app.config.get('LOG_LEVEL', logging.DEBUG))
        self.formatter = logging.Formatter(
            '%(asctime)s - %(module)s - %(funcName)s - %(lineno)d - %(levelname)s - %(message)s')

        if not os.path.exists(self.logFolder):
            os.makedirs(self.logFolder)

        # Create rotating file handlers for each log level if they don't exist
        if "info handler" not in [h.name for h in self.lg.handlers]:
            self.create_handlers()
        
        # log all Q_ERROR exceptions to the error log file
        # Q_ERROR is a custom exception class
        app.register_error_handler(
        Q_ERROR,
        Q_ERROR.build_error_handler(
            lambda e: self.lg.error(self.format_error(e))),
    )

    @staticmethod
    def format_error(e: Q_ERROR):
        ''' this function is called by the logger when type Q_ERROR is raised'''
        tb_len = len(traceback.extract_tb(e.__traceback__))
        if tb_len > 2:
            tb = traceback.extract_tb(e.__traceback__)[2]
        elif tb_len == 2:
            tb = traceback.extract_tb(e.__traceback__)[1]
        else:
            tb = traceback.extract_tb(e.__traceback__)[0]

        filename = tb.filename
        function_name = tb.name
        line_number = tb.lineno
        error_message = f"Error: {str(e)}, Type: {type(e).__name__}"

        if hasattr(e, 'status_code'):
            error_message += f", Status Code: {e.status_code}"

        error_message += f", File: {filename}, Function: {function_name}, Line: {line_number}"

        return error_message

    def create_handlers(self):
        levels = ['debug', 'info', 'warning', 'error'] 
        for lvl in levels:
            log_file = os.path.join(self.logFolder, f'{lvl}.log')
            handler = RotatingFileHandler(
                log_file, maxBytes=1024*1024, backupCount=10)
            handler.setLevel(getattr(logging, lvl.upper()))
            handler.setFormatter(self.formatter)
            self.lg.addHandler(handler)

