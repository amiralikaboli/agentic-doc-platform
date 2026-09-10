import logging
from abc import ABC, abstractmethod
from typing import Optional, Dict, List

from openai import APIError, APITimeoutError, OpenAI

from src.core.config import settings
from src.core.errors import ExternalServiceError

logger = logging.getLogger(__name__)


class BaseLLMClient(ABC):
    @abstractmethod
    def generate(
            self,
            messages: List[Dict[str, str]],
            max_tokens: Optional[int] = None,
            temperature: Optional[float] = None,
    ) -> str:
        raise NotImplementedError


class MockLLMClient(BaseLLMClient):
    def generate(
            self,
            messages: List[Dict[str, str]],
            max_tokens: Optional[int] = None,
            temperature: Optional[float] = None,
    ) -> str:
        return '\n'.join(f"{msg['role']}: {msg['content']}" for msg in messages)


class VLLMClient(BaseLLMClient):
    def __init__(self):
        self.client = OpenAI(
            base_url=settings.LLM_BASE_URL,
            api_key=settings.LLM_API_KEY,
            timeout=settings.LLM_REQUEST_TIMEOUT,
        )
        self._model = self._fetch_model_name()

    def _fetch_model_name(self) -> str:
        try:
            models = self.client.models.list()
            if not models.data:
                raise ExternalServiceError(
                    "LLM Service",
                    "No models available in /v1/models endpoint"
                )
            model_name = models.data[0].id
            logger.info(f"Fetched LLM model: {model_name}")
            return model_name
        except APIError as e:
            logger.error(f"Failed to fetch models from /v1/models: {e}")
            raise ExternalServiceError(
                "LLM Service",
                f"Could not fetch available models: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Unexpected error fetching models: {e}")
            raise ExternalServiceError(
                "LLM Service",
                f"Unexpected error fetching models: {str(e)}"
            )

    def generate(
            self,
            messages: list[dict[str, str]],
            max_tokens: Optional[int] = None,
            temperature: Optional[float] = None,
    ) -> str:
        try:
            response = self.client.chat.completions.create(
                model=self._model,
                messages=messages,
                max_tokens=max_tokens if max_tokens is not None else settings.LLM_MAX_TOKENS,
                temperature=temperature if temperature is not None else settings.LLM_TEMPERATURE,
            )
        except APITimeoutError as e:
            logger.error(f"vLLM request timed out: {e}")
            raise ExternalServiceError("LLM Service", "Request timed out")
        except APIError as e:
            logger.error(f"vLLM API error: {e}")
            raise ExternalServiceError("LLM Service", str(e))
        except Exception as e:
            logger.error(f"Unexpected error calling vLLM: {e}")
            raise ExternalServiceError("LLM Service", str(e))

        choice = response.choices[0]
        if not choice.message.content:
            raise ExternalServiceError("LLM Service", "Model returned an empty completion")
        return choice.message.content


_client: BaseLLMClient | None = None


def get_llm_client() -> BaseLLMClient:
    global _client
    if _client is None:
        if settings.LLM_BACKEND == "vllm":
            _client = VLLMClient()
        else:
            _client = MockLLMClient()
    return _client
