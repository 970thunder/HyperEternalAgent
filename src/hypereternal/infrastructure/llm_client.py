"""
LLM client module for HyperEternalAgent framework.
"""

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from ..core.config import LLMConfig
from ..core.exceptions import (
    LLMAuthenticationError,
    LLMConnectionError,
    LLMError,
    LLMRateLimitError,
    LLMResponseError,
)
from ..infrastructure.logging import get_logger

logger = get_logger(__name__)


@dataclass
class LLMMessage:
    """LLM message."""

    role: str  # "system", "user", "assistant"
    content: str
    name: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        result = {"role": self.role, "content": self.content}
        if self.name:
            result["name"] = self.name
        return result


@dataclass
class LLMResponse:
    """LLM response."""

    content: str
    model: str
    provider: str
    usage: Dict[str, int] = field(default_factory=dict)
    finish_reason: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    latency_seconds: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseLLMClient(ABC):
    """Base class for LLM clients."""

    def __init__(self, config: LLMConfig):
        self.config = config
        self._is_initialized = False

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the client."""
        pass

    @abstractmethod
    async def generate(
        self,
        messages: List[LLMMessage],
        **kwargs: Any,
    ) -> LLMResponse:
        """Generate response from messages."""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close the client."""
        pass

    async def __aenter__(self) -> "BaseLLMClient":
        await self.initialize()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.close()


class OpenAIClient(BaseLLMClient):
    """OpenAI API client."""

    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self._client: Optional[Any] = None

    async def initialize(self) -> None:
        """Initialize OpenAI client."""
        try:
            from openai import AsyncOpenAI

            self._client = AsyncOpenAI(
                api_key=self.config.api_key,
                base_url=self.config.base_url,
            )
            self._is_initialized = True
            logger.info(
                "openai_client_initialized",
                model=self.config.model,
                base_url=self.config.base_url,
            )
        except ImportError:
            raise LLMError("openai package not installed. Run: pip install openai")
        except Exception as e:
            raise LLMConnectionError(f"Failed to initialize OpenAI client: {e}")

    async def generate(
        self,
        messages: List[LLMMessage],
        **kwargs: Any,
    ) -> LLMResponse:
        """Generate response using OpenAI API."""
        if not self._is_initialized or not self._client:
            raise LLMError("Client not initialized")

        start_time = datetime.now()

        try:
            response = await self._client.chat.completions.create(
                model=kwargs.get("model", self.config.model),
                messages=[m.to_dict() for m in messages],
                temperature=kwargs.get("temperature", self.config.temperature),
                max_tokens=kwargs.get("max_tokens", self.config.max_tokens),
                **{k: v for k, v in kwargs.items() if k not in ["model", "temperature", "max_tokens"]},
            )

            latency = (datetime.now() - start_time).total_seconds()

            return LLMResponse(
                content=response.choices[0].message.content or "",
                model=response.model,
                provider="openai",
                usage={
                    "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                    "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                    "total_tokens": response.usage.total_tokens if response.usage else 0,
                },
                finish_reason=response.choices[0].finish_reason,
                latency_seconds=latency,
            )

        except Exception as e:
            error_str = str(e).lower()
            if "rate limit" in error_str:
                raise LLMRateLimitError(f"OpenAI rate limit exceeded: {e}")
            elif "authentication" in error_str or "invalid api key" in error_str:
                raise LLMAuthenticationError(f"OpenAI authentication failed: {e}")
            elif "connection" in error_str or "timeout" in error_str:
                raise LLMConnectionError(f"OpenAI connection error: {e}")
            else:
                raise LLMResponseError(f"OpenAI response error: {e}")

    async def close(self) -> None:
        """Close the client."""
        if self._client:
            await self._client.close()
            self._is_initialized = False


class AnthropicClient(BaseLLMClient):
    """Anthropic API client."""

    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self._client: Optional[Any] = None

    async def initialize(self) -> None:
        """Initialize Anthropic client."""
        try:
            from anthropic import AsyncAnthropic

            self._client = AsyncAnthropic(api_key=self.config.api_key)
            self._is_initialized = True
            logger.info("anthropic_client_initialized", model=self.config.model)
        except ImportError:
            raise LLMError("anthropic package not installed. Run: pip install anthropic")
        except Exception as e:
            raise LLMConnectionError(f"Failed to initialize Anthropic client: {e}")

    async def generate(
        self,
        messages: List[LLMMessage],
        **kwargs: Any,
    ) -> LLMResponse:
        """Generate response using Anthropic API."""
        if not self._is_initialized or not self._client:
            raise LLMError("Client not initialized")

        start_time = datetime.now()

        try:
            # Separate system message from other messages
            system_message = ""
            chat_messages = []

            for msg in messages:
                if msg.role == "system":
                    system_message = msg.content
                else:
                    chat_messages.append(msg.to_dict())

            response = await self._client.messages.create(
                model=kwargs.get("model", self.config.model),
                max_tokens=kwargs.get("max_tokens", self.config.max_tokens),
                system=system_message if system_message else None,
                messages=chat_messages,
            )

            latency = (datetime.now() - start_time).total_seconds()

            # Extract text content
            content = ""
            if response.content:
                for block in response.content:
                    if hasattr(block, "text"):
                        content += block.text

            return LLMResponse(
                content=content,
                model=response.model,
                provider="anthropic",
                usage={
                    "prompt_tokens": response.usage.input_tokens,
                    "completion_tokens": response.usage.output_tokens,
                    "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
                },
                finish_reason=response.stop_reason,
                latency_seconds=latency,
            )

        except Exception as e:
            error_str = str(e).lower()
            if "rate limit" in error_str:
                raise LLMRateLimitError(f"Anthropic rate limit exceeded: {e}")
            elif "authentication" in error_str or "invalid api key" in error_str:
                raise LLMAuthenticationError(f"Anthropic authentication failed: {e}")
            elif "connection" in error_str or "timeout" in error_str:
                raise LLMConnectionError(f"Anthropic connection error: {e}")
            else:
                raise LLMResponseError(f"Anthropic response error: {e}")

    async def close(self) -> None:
        """Close the client."""
        if self._client:
            await self._client.close()
            self._is_initialized = False


class LLMClientFactory:
    """Factory for creating LLM clients."""

    _clients: Dict[str, BaseLLMClient] = {}

    @classmethod
    def create(cls, config: LLMConfig) -> BaseLLMClient:
        """Create an LLM client based on configuration."""
        provider = config.provider.lower()

        if provider == "openai":
            client = OpenAIClient(config)
        elif provider == "anthropic":
            client = AnthropicClient(config)
        else:
            raise LLMError(f"Unknown LLM provider: {provider}")

        return client

    @classmethod
    async def get_or_create(cls, config: LLMConfig) -> BaseLLMClient:
        """Get existing client or create a new one."""
        key = f"{config.provider}:{config.model}"
        if key not in cls._clients:
            client = cls.create(config)
            await client.initialize()
            cls._clients[key] = client
        return cls._clients[key]

    @classmethod
    async def close_all(cls) -> None:
        """Close all clients."""
        for client in cls._clients.values():
            await client.close()
        cls._clients.clear()


class LLMClientWrapper:
    """
    High-level LLM client wrapper with retry and caching support.
    """

    def __init__(
        self,
        config: LLMConfig,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ):
        self.config = config
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self._client: Optional[BaseLLMClient] = None

    async def initialize(self) -> None:
        """Initialize the client."""
        self._client = await LLMClientFactory.get_or_create(self.config)

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs: Any,
    ) -> str:
        """
        Generate response from a prompt.

        Args:
            prompt: User prompt
            system_prompt: System prompt (optional)
            **kwargs: Additional arguments for the LLM

        Returns:
            Generated text
        """
        messages = []
        if system_prompt:
            messages.append(LLMMessage(role="system", content=system_prompt))
        messages.append(LLMMessage(role="user", content=prompt))

        response = await self.generate_with_messages(messages, **kwargs)
        return response.content

    async def generate_with_messages(
        self,
        messages: List[LLMMessage],
        **kwargs: Any,
    ) -> LLMResponse:
        """
        Generate response from messages.

        Args:
            messages: List of messages
            **kwargs: Additional arguments for the LLM

        Returns:
            LLM response
        """
        if not self._client:
            await self.initialize()

        last_error: Optional[Exception] = None

        for attempt in range(self.max_retries):
            try:
                return await self._client.generate(messages, **kwargs)
            except LLMRateLimitError as e:
                last_error = e
                wait_time = self.retry_delay * (2**attempt)
                logger.warning(
                    "llm_rate_limit_retry",
                    attempt=attempt + 1,
                    wait_seconds=wait_time,
                )
                await asyncio.sleep(wait_time)
            except (LLMConnectionError, LLMResponseError) as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    wait_time = self.retry_delay * (2**attempt)
                    logger.warning(
                        "llm_error_retry",
                        attempt=attempt + 1,
                        error=str(e),
                        wait_seconds=wait_time,
                    )
                    await asyncio.sleep(wait_time)

        raise last_error or LLMError("Failed to generate response")

    async def close(self) -> None:
        """Close the client."""
        # Don't close factory-managed clients
        pass
