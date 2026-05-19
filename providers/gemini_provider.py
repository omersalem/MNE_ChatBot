import logging
from openai import OpenAI, APITimeoutError, RateLimitError, APIStatusError
from providers.base_provider import BaseProvider

logger = logging.getLogger(__name__)


class GeminiProvider(BaseProvider):
    def __init__(self, api_key, model='gemini-2.0-flash'):
        super().__init__(api_key, model or 'gemini-2.0-flash')
        # Gemini offers an OpenAI-compatible endpoint for chat completions.
        self.client = OpenAI(
            api_key=api_key,
            base_url='https://generativelanguage.googleapis.com/v1beta/openai/',
            timeout=30.0,
            max_retries=1,
        )

    def _ensure_model(self, model=None):
        return (model or self.model or 'gemini-2.0-flash').strip() or 'gemini-2.0-flash'

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
            logger.error("Gemini quota/rate limit: %s", e)
            raise RuntimeError("Gemini quota exceeded or rate-limited. Check billing/quota and retry.")
        except APIStatusError as e:
            logger.error("Gemini API status error: %s", e)
            raise RuntimeError(f"Gemini API error: {e.status_code}")
        except APITimeoutError:
            logger.error("Gemini request timed out")
            raise TimeoutError("Gemini request timed out after 30s")
        except Exception as e:
            logger.error(f"Gemini error: {e}")
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
            logger.error("Gemini stream quota/rate limit: %s", e)
            raise RuntimeError("Gemini quota exceeded or rate-limited. Check billing/quota and retry.")
        except APIStatusError as e:
            logger.error("Gemini stream API status error: %s", e)
            raise RuntimeError(f"Gemini API error: {e.status_code}")
        except APITimeoutError:
            logger.error("Gemini stream timed out")
            raise TimeoutError("Gemini request timed out after 30s")
        except Exception as e:
            logger.error(f"Gemini stream error: {e}")
            raise

    def health_check(self):
        try:
            self.client.models.list(timeout=10)
            return {'status': 'connected', 'provider': 'gemini'}
        except Exception as e:
            return {'status': 'failed', 'provider': 'gemini', 'error': str(e)[:100]}

    def validate_key(self):
        try:
            self.client.models.list(timeout=10)
            return True
        except Exception:
            return False
