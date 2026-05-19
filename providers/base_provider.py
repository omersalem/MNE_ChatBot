from abc import ABC, abstractmethod


class BaseProvider(ABC):
    def __init__(self, api_key, model=None):
        self.api_key = api_key
        self.model = model

    @abstractmethod
    def generate_response(self, messages, **kwargs):
        pass

    @abstractmethod
    def stream_response(self, messages, **kwargs):
        pass

    @abstractmethod
    def health_check(self):
        pass

    @abstractmethod
    def validate_key(self):
        pass
