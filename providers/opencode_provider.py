import logging
from openai import OpenAI, APIConnectionError
from providers.base_provider import BaseProvider

logger = logging.getLogger(__name__)


class OpenCodeProvider(BaseProvider):
    def __init__(self, api_key, model='opencode-model', base_url='http://localhost:8080/v1'):
        super().__init__(api_key, model)
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.base_url = base_url

    def generate_response(self, messages, **kwargs):
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                **kwargs
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"OpenCode error: {e}")
            raise

    def stream_response(self, messages, **kwargs):
        try:
            stream = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                stream=True,
                **kwargs
            )
            for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            logger.error(f"OpenCode stream error: {e}")
            raise

    def health_check(self):
        try:
            self.client.models.list()
            return {'status': 'connected', 'provider': 'opencode', 'base_url': self.base_url}
        except APIConnectionError as e:
            return {'status': 'failed', 'provider': 'opencode', 'error': f'Cannot reach {self.base_url}'}
        except Exception as e:
            return {'status': 'failed', 'provider': 'opencode', 'error': str(e)}

    def validate_key(self):
        try:
            self.client.models.list()
            return True
        except Exception:
            return False
