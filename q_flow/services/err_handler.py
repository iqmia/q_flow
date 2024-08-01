from sqlalchemy.exc import StatementError
from flask import Flask, jsonify
from q_flow.exceptions import Q_ERROR

class ErrHandler:
    def __init__(self):
        pass

    def init_app(self, app: Flask):
        @app.errorhandler(StatementError)
        def handle_statement_error(error):
            response = {
                'error': 'Invalid data type',
                'message': str(error.orig)
            }
            return jsonify(response), 400

