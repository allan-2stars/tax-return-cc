from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class AIResponse:
    content: str
    input_tokens: int
    output_tokens: int


class AIProvider(ABC):
    @abstractmethod
    async def complete(
        self, system: str, messages: list, max_tokens: int, temperature: float
    ) -> AIResponse: ...

    @abstractmethod
    async def complete_with_search(
        self, system: str, messages: list
    ) -> AIResponse: ...


class AIAdapter:
    def __init__(self, provider: AIProvider) -> None:
        self.provider = provider

    async def classify(self, text: str, fields: list, profile) -> dict:
        raise NotImplementedError

    async def extract_events(self, doc, classification: dict) -> list:
        raise NotImplementedError

    async def explain(self, event) -> str:
        raise NotImplementedError

    async def generate_inline_questions(self, event, profile) -> list:
        raise NotImplementedError

    async def ask(self, question: str, context: dict) -> str:
        raise NotImplementedError

    async def assess_risk(self, events: list, profile) -> list:
        raise NotImplementedError
