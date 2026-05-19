import anthropic

from app.ai.base import AIProvider, AIResponse
from app.config import settings


class ClaudeProvider(AIProvider):
    def __init__(self) -> None:
        self._client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    async def complete(
        self, system: str, messages: list, max_tokens: int, temperature: float
    ) -> AIResponse:
        response = await self._client.messages.create(
            model=settings.ANTHROPIC_MODEL,
            system=system,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return AIResponse(
            content=response.content[0].text,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            provider="claude",
            model=settings.ANTHROPIC_MODEL,
        )

    async def complete_with_search(
        self, system: str, messages: list
    ) -> AIResponse:
        response = await self._client.messages.create(
            model=settings.ANTHROPIC_MODEL,
            system=system,
            messages=messages,
            max_tokens=1000,
            temperature=0.1,
            tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": 3}],
        )
        # Extract first text block from potentially mixed content
        text = next(
            (block.text for block in response.content if hasattr(block, "text")),
            "",
        )
        return AIResponse(
            content=text,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            provider="claude",
            model=settings.ANTHROPIC_MODEL,
        )
