from flask import Blueprint, jsonify

system = Blueprint('system', __name__)


@system.route('/health', methods=['GET'])
def health():
    return jsonify(status='ok', service='CashflowPot API'), 200
