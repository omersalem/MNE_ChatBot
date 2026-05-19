import logging
from openai import OpenAI, APITimeoutError, APIError
from providers.base_provider import BaseProvider

logger = logging.getLogger(__name__)


class OpenRouterProvider(BaseProvider):
    def __init__(self, api_key, model='openai/gpt-4o'):
        super().__init__(api_key, model or 'openai/gpt-4o')
        self.client = OpenAI(
            api_key=api_key,
            base_url='https://openrouter.ai/api/v1',
            timeout=30.0,
            max_retries=1,
        )

    def _ensure_model(self, model=None):
        return (model or self.model or 'openai/gpt-4o').strip() or 'openai/gpt-4o'

    def generate_response(self, messages, **kwargs):
        try:
            response = self.client.chat.completions.create(
                model=self._ensure_model(),
                messages=messages,
                timeout=30,
                **kwargs
            )
            return response.choices[0].message.content
        except APITimeoutError:
            logger.error("OpenRouter request timed out")
            raise TimeoutError("OpenRouter request timed out after 30s")
        except Exception as e:
            logger.error(f"OpenRouter error: {e}")
            raise

    def stream_response(self, messages, **kwargs):
        try:
            stream = self.client.chat.completions.create(
                model=self._ensure_model(),
                messages=messages,
                stream=True,
                timeout=30,
                **kwargs
            )
            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content is not None:
                    yield chunk.choices[0].delta.content
        except APITimeoutError:
            logger.error("OpenRouter stream timed out")
            raise TimeoutError("OpenRouter request timed out after 30s")
        except Exception as e:
            logger.error(f"OpenRouter stream error: {e}")
            raise

    def health_check(self):
        try:
            self.client.models.list(timeout=10)
            return {'status': 'connected', 'provider': 'openrouter'}
        except Exception as e:
            return {'status': 'failed', 'provider': 'openrouter', 'error': str(e)[:100]}

    def validate_key(self):
        try:
            self.client.models.list(timeout=10)
            return True
        except Exception:
            return False
