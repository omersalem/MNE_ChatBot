import logging
import anthropic
from providers.base_provider import BaseProvider

logger = logging.getLogger(__name__)


class AnthropicProvider(BaseProvider):
    def __init__(self, api_key, model='claude-sonnet-4-20250514'):
        super().__init__(api_key, model)
        self.client = anthropic.Anthropic(api_key=api_key)

    def generate_response(self, messages, **kwargs):
        try:
            system_msg = ''
            user_messages = []
            for msg in messages:
                if msg['role'] == 'system':
                    system_msg = msg['content']
                else:
                    user_messages.append(msg)

            response = self.client.messages.create(
                model=self.model,
                system=system_msg,
                messages=user_messages,
                max_tokens=4096,
                **kwargs
            )
            return response.content[0].text
        except Exception as e:
            logger.error(f"Anthropic error: {e}")
            raise

    def stream_response(self, messages, **kwargs):
        try:
            system_msg = ''
            user_messages = []
            for msg in messages:
                if msg['role'] == 'system':
                    system_msg = msg['content']
                else:
                    user_messages.append(msg)

            with self.client.messages.stream(
                model=self.model,
                system=system_msg,
                messages=user_messages,
                max_tokens=4096,
                **kwargs
            ) as stream:
                for text in stream.text_stream:
                    yield text
        except Exception as e:
            logger.error(f"Anthropic stream error: {e}")
            raise

    def health_check(self):
        try:
            self.client.messages.create(
                model=self.model,
                max_tokens=10,
                messages=[{'role': 'user', 'content': 'Hi'}]
            )
            return {'status': 'connected', 'provider': 'anthropic'}
        except Exception as e:
            return {'status': 'failed', 'provider': 'anthropic', 'error': str(e)}

    def validate_key(self):
        try:
            self.client.messages.create(
                model=self.model,
                max_tokens=10,
                messages=[{'role': 'user', 'content': 'Hi'}]
            )
            return True
        except Exception:
            return False
