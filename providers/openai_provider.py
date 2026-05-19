import logging
from openai import OpenAI
from providers.base_provider import BaseProvider

logger = logging.getLogger(__name__)


class OpenAIProvider(BaseProvider):
    def __init__(self, api_key, model='gpt-4o-mini'):
        super().__init__(api_key, model)
        self.client = OpenAI(api_key=api_key)

    def generate_response(self, messages, **kwargs):
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                **kwargs
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"OpenAI error: {e}")
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
            logger.error(f"OpenAI stream error: {e}")
            raise

    def health_check(self):
        try:
            self.client.models.list()
            return {'status': 'connected', 'provider': 'openai'}
        except Exception as e:
            return {'status': 'failed', 'provider': 'openai', 'error': str(e)}

    def validate_key(self):
        try:
            self.client.models.list()
            return True
        except Exception:
            return False
