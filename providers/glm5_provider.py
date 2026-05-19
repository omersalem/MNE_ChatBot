import logging
from openai import OpenAI, APITimeoutError
from providers.base_provider import BaseProvider

logger = logging.getLogger(__name__)


class GLM5Provider(BaseProvider):
    def __init__(self, api_key, model='zai-org/GLM-5'):
        super().__init__(api_key, model or 'zai-org/GLM-5')
        self.client = OpenAI(
            api_key=api_key,
            base_url='https://inference.baseten.co/v1',
            timeout=60.0,
            max_retries=1,
        )

    def _ensure_model(self, model=None):
        return (model or self.model or 'zai-org/GLM-5').strip() or 'zai-org/GLM-5'

    def generate_response(self, messages, **kwargs):
        try:
            response = self.client.chat.completions.create(
                model=self._ensure_model(),
                messages=messages,
                timeout=60,
                **kwargs
            )
            return response.choices[0].message.content
        except APITimeoutError:
            logger.error("GLM-5 request timed out")
            raise TimeoutError("GLM-5 request timed out after 60s")
        except Exception as e:
            logger.error(f"GLM-5 error: {e}")
            raise

    def stream_response(self, messages, **kwargs):
        try:
            stream = self.client.chat.completions.create(
                model=self._ensure_model(),
                messages=messages,
                stream=True,
                stream_options={"include_usage": True, "continuous_usage_stats": True},
                timeout=60,
                **kwargs
            )
            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content is not None:
                    yield chunk.choices[0].delta.content
        except APITimeoutError:
            logger.error("GLM-5 stream timed out")
            raise TimeoutError("GLM-5 request timed out after 60s")
        except Exception as e:
            logger.error(f"GLM-5 stream error: {e}")
            raise

    def health_check(self):
        try:
            self.client.models.list(timeout=10)
            return {'status': 'connected', 'provider': 'glm5'}
        except Exception as e:
            return {'status': 'failed', 'provider': 'glm5', 'error': str(e)[:100]}

    def validate_key(self):
        try:
            self.client.models.list(timeout=10)
            return True
        except Exception:
            return False
