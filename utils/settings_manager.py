import json
import logging
from pathlib import Path
from config import Config

logger = logging.getLogger(__name__)


class SettingsManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self.settings_file = Config.CACHE_DIR / 'settings.json'
        self.keys_file = Config.CACHE_DIR / 'api_keys.json'
        Config.CACHE_DIR.mkdir(exist_ok=True)
        self._defaults = {
            'active_provider': 'openai',
            'active_model': '',
            'providers': {
                'openai': {'models': ['gpt-4o', 'gpt-4o-mini', 'gpt-5', 'gpt-5.5'], 'default': 'gpt-4o-mini'},
                'anthropic': {'models': ['claude-sonnet-4-20250514', 'claude-5-haiku'], 'default': 'claude-sonnet-4-20250514'},
                'openrouter': {'models': ['openai/gpt-4o', 'anthropic/claude-sonnet-4', 'meta-llama/llama-3-70b', 'deepseek/deepseek-v4-flash:free'], 'default': 'openai/gpt-4o'},
                'gemini': {'models': ['gemini-2.0-flash', 'gemini-2.0-pro'], 'default': 'gemini-2.0-flash'},
                'hapuppy': {
                    'models': [
                        'glm-4.7',
                        'gemini-2.5-flash',
                        'glm-5.1',
                    ],
                    'default': 'gemini-2.5-flash'
                },
                'ollama': {'models': ['llama3', 'mistral', 'mixtral'], 'default': 'llama3'},
                'litellm': {'models': ['gpt-4o', 'claude-sonnet-4'], 'default': 'gpt-4o'},
                'glm5': {'models': ['zai-org/GLM-5', 'deepseek-ai/DeepSeek-V4-Pro'], 'default': 'zai-org/GLM-5'},
            }
        }
        self._settings = self._load()
        self._api_keys = self._load_keys()
        self._initialized = True

    def _load(self):
        if self.settings_file.exists():
            try:
                with open(self.settings_file) as f:
                    data = json.load(f)
                    merged = dict(self._defaults)
                    for k, v in data.items():
                        if k == 'providers' and isinstance(v, dict):
                            merged['providers'] = {
                                name: {
                                    'models': list(dict.fromkeys(v.get(name, {}).get('models', []) + self._defaults.get('providers', {}).get(name, {}).get('models', []))),
                                    'default': v.get(name, {}).get('default', self._defaults.get('providers', {}).get(name, {}).get('default', '')),
                                }
                                for name in set(list(v.keys()) + list(self._defaults.get('providers', {}).keys()))
                            }
                        else:
                            merged[k] = v
                    return merged
            except Exception as e:
                logger.error(f"Error loading settings: {e}")
        return dict(self._defaults)

    def _save(self):
        try:
            with open(self.settings_file, 'w') as f:
                json.dump(self._settings, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving settings: {e}")

    def _load_keys(self):
        if self.keys_file.exists():
            try:
                with open(self.keys_file) as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save_keys(self):
        try:
            with open(self.keys_file, 'w') as f:
                json.dump(self._api_keys, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving API keys: {e}")

    def get_setting(self, key, default=None):
        return self._settings.get(key, default)

    def set_setting(self, key, value):
        self._settings[key] = value
        self._save()

    def get_active_provider(self):
        return self._settings.get('active_provider', 'openai')

    def set_active_provider(self, provider):
        self._settings['active_provider'] = provider
        if provider in self._settings.get('providers', {}):
            self._settings['active_model'] = self._settings['providers'][provider].get('default', '')
        self._save()

    def get_active_model(self):
        return self._settings.get('active_model', '')

    def set_active_model(self, model):
        self._settings['active_model'] = model
        self._save()

    def get_providers_config(self):
        return self._settings.get('providers', {})

    def get_models_for_provider(self, provider):
        providers = self._settings.get('providers', {})
        if provider in providers:
            return providers[provider].get('models', [])
        return []

    def get_api_key(self, provider):
        return self._api_keys.get(provider, '')

    def set_api_key(self, provider, key):
        self._api_keys[provider] = key
        self._save_keys()

    def has_api_keys(self):
        return any(v for v in self._api_keys.values())

    def get_public_config(self):
        providers = self._settings.get('providers', {})
        return {
            'active_provider': self.get_active_provider(),
            'active_model': self.get_active_model(),
            'providers': {
                name: {
                    'models': info.get('models', []),
                    'default': info.get('default', ''),
                }
                for name, info in providers.items()
            },
            'has_keys': {name: bool(self._api_keys.get(name)) for name in providers},
        }
