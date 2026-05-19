import logging
from flask import Blueprint, request, jsonify
from utils.settings_manager import SettingsManager
from utils.auth import AuthManager
from providers.provider_manager import ProviderManager

logger = logging.getLogger(__name__)

settings_bp = Blueprint('settings', __name__)
settings_manager = SettingsManager()
auth_manager = AuthManager()
provider_manager = ProviderManager()


def require_admin():
    token = request.headers.get('X-Admin-Token', '')
    if not auth_manager.validate_session(token):
        return {'error': 'Unauthorized'}, 401
    return None


@settings_bp.route('/api/config', methods=['GET'])
def get_config():
    return jsonify(settings_manager.get_public_config())


@settings_bp.route('/api/config/provider', methods=['POST'])
def set_provider():
    err = require_admin()
    if err:
        return err

    data = request.get_json()
    provider = data.get('provider', '')
    available = list(settings_manager.get_providers_config().keys())
    if provider not in available:
        return jsonify({'error': f'Invalid provider. Available: {available}'}), 400

    settings_manager.set_active_provider(provider)
    provider_manager.set_active(provider)
    return jsonify({'status': 'ok', 'provider': provider, 'model': settings_manager.get_active_model()})


@settings_bp.route('/api/config/model', methods=['POST'])
def set_model():
    err = require_admin()
    if err:
        return err

    data = request.get_json()
    model = data.get('model', '')
    provider = settings_manager.get_active_provider()
    models = settings_manager.get_models_for_provider(provider)
    
    if model not in models:
        return jsonify({'error': f'Invalid model for {provider}. Available: {models}'}), 400

    settings_manager.set_active_model(model)
    if provider in provider_manager.list_providers():
        provider_manager.get_provider(provider).model = model
    return jsonify({'status': 'ok', 'provider': provider, 'model': model})


@settings_bp.route('/api/config/models/<provider>', methods=['GET'])
def get_models(provider):
    models = settings_manager.get_models_for_provider(provider)
    return jsonify({'provider': provider, 'models': models})


@settings_bp.route('/api/config/api-keys', methods=['GET'])
def get_api_keys():
    err = require_admin()
    if err:
        return err

    providers = list(settings_manager.get_providers_config().keys())
    result = {}
    for p in providers:
        key = settings_manager.get_api_key(p)
        result[p] = {'configured': bool(key), 'key_preview': key[:8] + '...' if len(key) > 8 else ''}
    return jsonify({'keys': result})


@settings_bp.route('/api/config/api-keys', methods=['POST'])
def save_api_key():
    err = require_admin()
    if err:
        return err

    data = request.get_json()
    provider = data.get('provider', '')
    api_key = data.get('api_key', '')
    
    if not provider:
        return jsonify({'error': 'Provider required'}), 400
    if not api_key:
        return jsonify({'error': 'API key required'}), 400

    settings_manager.set_api_key(provider, api_key)
    provider_manager.refresh()
    return jsonify({'status': 'ok', 'provider': provider, 'configured': True})


@settings_bp.route('/api/config/refresh', methods=['POST'])
def refresh_config():
    err = require_admin()
    if err:
        return err
    provider_manager.refresh()
    return jsonify({'status': 'ok', 'providers': provider_manager.list_providers(), 'active': provider_manager.get_active_name()})
