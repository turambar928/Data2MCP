import logging
from functools import partial

from backoff import expo, on_exception
from openai import OpenAI

logger = logging.getLogger(__name__)


# Doesn't for some data tools
class ChatModel:
    def __init__(
        self,
        model_name,
        model_url,
        api_key,
        **kwargs,
    ):
        self.model_name = model_name
        self.model_url = model_url
        self.client = OpenAI(
            api_key=api_key,
            base_url=model_url,
        )
        self.kwargs = kwargs
        self.extra_body = kwargs.pop("extra_body", {})
        self.init_extra_body()
        self.chat = partial(
            self.client.chat.completions.create,
            model=model_name,
            extra_body=self.extra_body,
            **self.kwargs,
        )

    def init_extra_body(self):
        pass

    def chat_with_retry(self, message, retry=3, **kwargs):
        @on_exception(expo, Exception, max_tries=retry)
        def _chat_with_retry(message, **kwargs):
            return self.chat(messages=message, **kwargs)

        try:
            response = _chat_with_retry(message, **kwargs)
            return response
        except Exception as e:
            logger.error(f"Chat completion failed: {e}")
            raise e

    def list_models(self):
        try:
            models = self.client.models.list()
            return [model.id for model in models.data]
        except Exception as e:
            logger.error(f"Failed to list models: {e}")
            raise e
