import logging
from config import Config
from providers.openai_provider import OpenAIProvider
from providers.anthropic_provider import AnthropicProvider
from providers.opencode_provider import OpenCodeProvider
from providers.openrouter_provider import OpenRouterProvider
from providers.glm5_provider import GLM5Provider
from providers.gemini_provider import GeminiProvider
from providers.hapuppy_provider import HapuppyProvider
from utils.settings_manager import SettingsManager

logger = logging.getLogger(__name__)


class ProviderManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._settings = SettingsManager()
        self._providers = {}
        self._active = self._settings.get_active_provider()
        self._init_providers()
        self._initialized = True

    def _init_providers(self):
        for name in self._all_provider_names():
            self._try_init_provider(name)

    def _all_provider_names(self):
        return ['openai', 'anthropic', 'opencode', 'openrouter', 'gemini', 'hapuppy', 'glm5']

    def _provider_class_and_kwargs(self, name):
        mapping = {
            'openai': (OpenAIProvider, {}),
            'anthropic': (AnthropicProvider, {}),
            'opencode': (OpenCodeProvider, {'base_url': Config.OPENCODE_API_BASE_URL}),
            'openrouter': (OpenRouterProvider, {}),
            'gemini': (GeminiProvider, {}),
            'hapuppy': (HapuppyProvider, {'base_url': Config.HAPUPPY_BASE_URL}),
            'glm5': (GLM5Provider, {}),
        }
        return mapping.get(name, (None, {}))

    def _try_init_provider(self, name):
        cls, extra_kwargs = self._provider_class_and_kwargs(name)
        if cls is None:
            return None
        api_key = self._settings.get_api_key(name) or Config.API_KEYS.get(name, '')
        if not api_key:
            return None
        model = self._settings.get_active_model() if name == self._active else Config.DEFAULT_MODEL.get(name, '')
        if not model:
            defaults = {
                'openai': 'gpt-4o-mini',
                'anthropic': 'claude-sonnet-4-20250514',
                'opencode': 'opencode-model',
                'openrouter': 'openai/gpt-4o',
                'gemini': 'gemini-2.0-flash',
                'hapuppy': 'gemini-2.5-flash',
                'glm5': 'zai-org/GLM-5',  # also supports deepseek-ai/DeepSeek-V4-Pro
            }
            model = defaults.get(name, '')
        try:
            self._providers[name] = cls(api_key, model=model, **dict(extra_kwargs))
            logger.info(f"Initialized provider: {name} with model: {model}")
            return self._providers[name]
        except Exception as e:
            logger.error(f"Failed to init provider {name}: {e}")
            return None

    def get_provider(self, name=None):
        provider_name = name or self._active
        if provider_name not in self._providers:
            self._try_init_provider(provider_name)
        if provider_name not in self._providers:
            raise ValueError(f"Provider '{provider_name}' not configured or unavailable")
        return self._providers[provider_name]

    def set_active(self, name):
        changed = name != self._active
        self._active = name
        self._settings.set_active_provider(name)
        if name not in self._providers:
            self._try_init_provider(name)
        logger.info(f"Active provider set to: {name}")
        if changed:
            model = self._settings.get_active_model()
            if model and name in self._providers:
                self._providers[name].model = model
        return name in self._providers

    def refresh(self):
        self._settings = SettingsManager()
        self._active = self._settings.get_active_provider()
        for name in list(self._providers.keys()):
            del self._providers[name]
        self._init_providers()

    def get_active_name(self):
        return self._active

    def list_providers(self):
        return list(self._providers.keys())

    def health_check_all(self):
        results = {}
        for name in self._all_provider_names():
            provider = self._providers.get(name)
            if provider:
                try:
                    results[name] = provider.health_check()
                except Exception as e:
                    results[name] = {'status': 'error', 'provider': name, 'error': str(e)}
            else:
                api_key = self._settings.get_api_key(name) or Config.API_KEYS.get(name, '')
                results[name] = {'status': 'no_key' if not api_key else 'uninitialized', 'provider': name}
        return results
