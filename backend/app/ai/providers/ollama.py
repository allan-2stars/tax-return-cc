from app.ai.base import AIProvider, AIResponse


class OllamaProvider(AIProvider):
    async def complete(
        self, system: str, messages: list, max_tokens: int, temperature: float
    ) -> AIResponse:
        raise NotImplementedError

    async def complete_with_search(
        self, system: str, messages: list
    ) -> AIResponse:
        raise NotImplementedError
