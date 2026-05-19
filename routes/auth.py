import logging
from flask import Blueprint, request, jsonify, session
from utils.auth import AuthManager

logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__)
auth_manager = AuthManager()


@auth_bp.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    password = data.get('password', '')

    if not password:
        return jsonify({'error': 'Password required'}), 400

    if auth_manager.verify_password(password):
        token = auth_manager.generate_session_token()
        auth_manager.save_session(token)
        session['admin_authenticated'] = True
        session['admin_token'] = token
        return jsonify({'status': 'ok', 'token': token})
    
    return jsonify({'error': 'Invalid password'}), 401


@auth_bp.route('/api/auth/logout', methods=['POST'])
def logout():
    auth_manager.clear_session()
    session.pop('admin_authenticated', None)
    session.pop('admin_token', None)
    return jsonify({'status': 'logged_out'})


@auth_bp.route('/api/auth/check', methods=['GET'])
def check_auth():
    token = request.headers.get('X-Admin-Token', '')
    if auth_manager.validate_session(token):
        return jsonify({'authenticated': True})
    return jsonify({'authenticated': False}), 401
