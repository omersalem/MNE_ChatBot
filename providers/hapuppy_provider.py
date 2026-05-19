import logging
from openai import OpenAI, APITimeoutError, RateLimitError, APIStatusError
from providers.base_provider import BaseProvider

logger = logging.getLogger(__name__)


class HapuppyProvider(BaseProvider):
    def __init__(self, api_key, model='gemini-2.5-flash', base_url='https://beta.hapuppy.com/v1'):
        super().__init__(api_key, model or 'gemini-2.5-flash')
        self.base_url = (base_url or 'https://beta.hapuppy.com/v1').rstrip('/')
        self.client = OpenAI(
            api_key=api_key,
            base_url=self.base_url,
            timeout=30.0,
            max_retries=0,
        )

    def _ensure_model(self, model=None):
        return (model or self.model or 'gemini-2.5-flash').strip() or 'gemini-2.5-flash'

    def generate_response(self, messages, **kwargs):
        try:
            response = self.client.chat.completions.create(
                model=self._ensure_model(),
                messages=messages,
                timeout=30,
                **kwargs
            )
            return response.choices[0].message.content
        except RateLimitError as e:
            logger.error("Hapuppy quota/rate limit: %s", e)
            raise RuntimeError("Hapuppy quota exceeded or rate-limited. Please retry.")
        except APIStatusError as e:
            logger.error("Hapuppy API status error: %s", e)
            raise RuntimeError(f"Hapuppy API error: {e.status_code}")
        except APITimeoutError:
            logger.error("Hapuppy request timed out")
            raise TimeoutError("Hapuppy request timed out after 30s")
        except Exception as e:
            logger.error(f"Hapuppy error: {e}")
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
        except RateLimitError as e:
            logger.error("Hapuppy stream quota/rate limit: %s", e)
            raise RuntimeError("Hapuppy quota exceeded or rate-limited. Please retry.")
        except APIStatusError as e:
            logger.error("Hapuppy stream API status error: %s", e)
            raise RuntimeError(f"Hapuppy API error: {e.status_code}")
        except APITimeoutError:
            logger.error("Hapuppy stream timed out")
            raise TimeoutError("Hapuppy request timed out after 30s")
        except Exception as e:
            logger.error(f"Hapuppy stream error: {e}")
            raise

    def health_check(self):
        try:
            self.client.models.list(timeout=10)
            return {'status': 'connected', 'provider': 'hapuppy'}
        except Exception as e:
            return {'status': 'failed', 'provider': 'hapuppy', 'error': str(e)[:100]}

    def validate_key(self):
        try:
            self.client.models.list(timeout=10)
            return True
        except Exception:
            return False
