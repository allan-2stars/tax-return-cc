from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from app.engines.sanitize import sanitize_for_ai  # noqa: F401 — module-level so tests can patch it


@dataclass
class AIResponse:
    content: str
    input_tokens: int
    output_tokens: int
    provider: str = ""
    model: str = ""


@dataclass
class ClassificationResult:
    document_type: str           # payg_summary | bank_statement | receipt | csv | unknown
    confidence: float            # 0.0 – 1.0
    skill_id: str | None = None
    suggested_category: str | None = None
    extracted_amounts: list[dict] = field(default_factory=list)
    notes: str = ""


@dataclass
class EventCandidate:
    event_type: str              # income | deduction | investment | wfh
    category: str
    description: str
    amount: float | None = None
    date: str | None = None
    confidence: float = 0.0
    ai_reasoning: str = ""


@dataclass
class InlineQuestion:
    question_id: str
    text: str
    input_type: str = "text"     # text | select | number
    options: list[str] | None = None


@dataclass
class RiskAssessment:
    risk_level: str              # low | medium | high
    risk_flags: list[str] = field(default_factory=list)
    ai_reasoning: str = ""


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
    _TEMPERATURE = 0.1
    _MAX_TOKENS = 1000
    _MAX_RETRIES = 3

    def __init__(self, provider: AIProvider, workspace_id: str = "") -> None:
        self.provider = provider
        self._workspace_id = workspace_id

    # ── core retry/fallback helper ────────────────────────────────────────────

    async def _call_with_retry(
        self, system: str, messages: list
    ) -> AIResponse | None:
        """
        Call the provider up to _MAX_RETRIES times, retrying on JSON parse errors.
        Returns None on timeout or exhausted retries so callers can return a fallback.
        """
        import asyncio
        import json
        from app.config import settings

        for _ in range(self._MAX_RETRIES):
            try:
                response = await asyncio.wait_for(
                    self.provider.complete(
                        system, messages, self._MAX_TOKENS, self._TEMPERATURE
                    ),
                    timeout=settings.AI_TIMEOUT_SECONDS,
                )
                json.loads(response.content)  # validate — raises JSONDecodeError if bad
                return response
            except asyncio.TimeoutError:
                return None
            except Exception:  # JSONDecodeError, API errors, etc.
                continue
        return None

    def _fire_audit(self, operation: str, response: AIResponse, duration_ms: int, success: bool) -> None:
        """Schedule an audit log write without blocking the caller."""
        import asyncio

        if not self._workspace_id:
            return

        async def _write():
            import app.db.base as db_base
            from app.repositories import audit as audit_repo
            try:
                async with db_base.AsyncSessionLocal() as db:
                    await audit_repo.log_ai_call(
                        db=db,
                        workspace_id=self._workspace_id,
                        operation=operation,
                        response=response,
                        duration_ms=duration_ms,
                        success=success,
                    )
            except Exception:
                pass  # never block caller on audit failure

        asyncio.create_task(_write())

    # ── domain methods ────────────────────────────────────────────────────────

    async def classify(
        self, text: str, fields: dict | None, profile: dict | None
    ) -> ClassificationResult:
        import json
        import time
        from app.ai.prompts import CLASSIFY_SYSTEM

        clean_text, clean_fields = sanitize_for_ai(text, fields)
        messages = [{"role": "user", "content": clean_text or ""}]

        t0 = time.monotonic()
        response = await self._call_with_retry(CLASSIFY_SYSTEM, messages)
        duration_ms = int((time.monotonic() - t0) * 1000)

        if response is None:
            fallback = AIResponse("", 0, 0, provider="", model="")
            self._fire_audit("classify", fallback, duration_ms, False)
            return ClassificationResult(document_type="unknown", confidence=0.0)

        self._fire_audit("classify", response, duration_ms, True)
        data = json.loads(response.content)
        return ClassificationResult(
            document_type=data.get("document_type", "unknown"),
            confidence=float(data.get("confidence", 0.0)),
            skill_id=data.get("skill_id"),
            suggested_category=data.get("suggested_category"),
            extracted_amounts=data.get("extracted_amounts", []),
            notes=data.get("notes", ""),
        )

    async def extract_events(
        self, text: str, document_type: str, skill_context: dict | None
    ) -> list[EventCandidate]:
        import json
        import time
        from app.ai.prompts import EXTRACT_EVENTS_SYSTEM
        from app.engines.sanitize import sanitize_for_ai

        clean_text, _ = sanitize_for_ai(text, None)
        system = EXTRACT_EVENTS_SYSTEM.format(
            document_type=document_type,
            skill_context=json.dumps(skill_context or {}),
            employment_type=(skill_context or {}).get("employment_type", "unknown"),
            financial_year=(skill_context or {}).get("financial_year", "2024-25"),
        )
        messages = [{"role": "user", "content": clean_text or ""}]

        t0 = time.monotonic()
        response = await self._call_with_retry(system, messages)
        duration_ms = int((time.monotonic() - t0) * 1000)

        if response is None:
            fallback = AIResponse("", 0, 0, provider="", model="")
            self._fire_audit("extract_events", fallback, duration_ms, False)
            return []

        self._fire_audit("extract_events", response, duration_ms, True)
        data = json.loads(response.content)
        return [
            EventCandidate(
                event_type=e.get("event_type", "deduction"),
                category=e.get("category", ""),
                description=e.get("description", ""),
                amount=e.get("amount"),
                date=e.get("date"),
                confidence=float(e.get("confidence", 0.0)),
                ai_reasoning=e.get("ai_reasoning", ""),
            )
            for e in data.get("events", [])
        ]

    async def explain(self, event: dict, profile: dict | None) -> str:
        import json
        import time
        from app.ai.prompts import EXPLAIN_SYSTEM, _DISCLAIMER

        system = EXPLAIN_SYSTEM.format(
            event_description=event.get("description", ""),
            amount=event.get("amount", ""),
            date=event.get("date", ""),
            category=event.get("category", ""),
            confidence=event.get("confidence", ""),
            ai_reasoning=event.get("ai_reasoning", ""),
            employment_type=(profile or {}).get("employment_type", "unknown"),
            financial_year=(profile or {}).get("financial_year", "2024-25"),
            disclaimer=_DISCLAIMER,
        )
        messages = [{"role": "user", "content": "Explain this tax item."}]

        t0 = time.monotonic()
        response = await self._call_with_retry(system, messages)
        duration_ms = int((time.monotonic() - t0) * 1000)

        if response is None:
            fallback = AIResponse("", 0, 0, provider="", model="")
            self._fire_audit("explain", fallback, duration_ms, False)
            return _DISCLAIMER

        self._fire_audit("explain", response, duration_ms, True)
        data = json.loads(response.content)
        return data.get("explanation", _DISCLAIMER)

    async def generate_inline_questions(
        self, event: dict, existing_answers: dict | None
    ) -> list[InlineQuestion]:
        import json
        import time
        from app.ai.prompts import INLINE_QUESTIONS_SYSTEM

        system = INLINE_QUESTIONS_SYSTEM.format(
            event_description=event.get("description", ""),
            amount=event.get("amount", ""),
            date=event.get("date", ""),
            category=event.get("category", ""),
            risk_level=event.get("risk_level", "low"),
            ai_reasoning=event.get("ai_reasoning", ""),
        )
        messages = [{"role": "user", "content": "Generate follow-up questions."}]

        t0 = time.monotonic()
        response = await self._call_with_retry(system, messages)
        duration_ms = int((time.monotonic() - t0) * 1000)

        if response is None:
            fallback = AIResponse("", 0, 0, provider="", model="")
            self._fire_audit("generate_inline_questions", fallback, duration_ms, False)
            return []

        self._fire_audit("generate_inline_questions", response, duration_ms, True)
        data = json.loads(response.content)
        return [
            InlineQuestion(
                question_id=q.get("question_id", ""),
                text=q.get("text", ""),
                input_type=q.get("input_type", "text"),
                options=q.get("options"),
            )
            for q in data.get("questions", [])
        ]

    async def ask(self, question: str, event: dict, session: dict | None) -> str:
        import json
        import time
        from app.ai.prompts import ASK_SYSTEM, _DISCLAIMER

        system = ASK_SYSTEM.format(
            event_description=event.get("description", ""),
            amount=event.get("amount", ""),
            date=event.get("date", ""),
            category=event.get("category", ""),
            employment_type=(session or {}).get("employment_type", "unknown"),
            financial_year=(session or {}).get("financial_year", "2024-25"),
            ai_reasoning=event.get("ai_reasoning", ""),
            disclaimer=_DISCLAIMER,
        )
        messages = [{"role": "user", "content": question}]

        t0 = time.monotonic()
        response = await self._call_with_retry(system, messages)
        duration_ms = int((time.monotonic() - t0) * 1000)

        if response is None:
            fallback = AIResponse("", 0, 0, provider="", model="")
            self._fire_audit("ask", fallback, duration_ms, False)
            return _DISCLAIMER

        self._fire_audit("ask", response, duration_ms, True)
        data = json.loads(response.content)
        return data.get("answer", _DISCLAIMER)

    async def assess_risk(
        self, event: dict, profile: dict | None, skill_risk_rules: list | None
    ) -> RiskAssessment:
        import json
        import time
        from app.ai.prompts import RISK_SYSTEM

        system = RISK_SYSTEM.format(
            event_description=event.get("description", ""),
            amount=event.get("amount", ""),
            date=event.get("date", ""),
            category=event.get("category", ""),
            employment_type=(profile or {}).get("employment_type", "unknown"),
            financial_year=(profile or {}).get("financial_year", "2024-25"),
            skill_risk_rules=json.dumps(skill_risk_rules or []),
        )
        messages = [{"role": "user", "content": "Assess risk for this tax item."}]

        t0 = time.monotonic()
        response = await self._call_with_retry(system, messages)
        duration_ms = int((time.monotonic() - t0) * 1000)

        if response is None:
            fallback = AIResponse("", 0, 0, provider="", model="")
            self._fire_audit("assess_risk", fallback, duration_ms, False)
            return RiskAssessment(risk_level="medium", risk_flags=["assessment_unavailable"])

        self._fire_audit("assess_risk", response, duration_ms, True)
        data = json.loads(response.content)
        return RiskAssessment(
            risk_level=data.get("risk_level", "medium"),
            risk_flags=data.get("risk_flags", []),
            ai_reasoning=data.get("ai_reasoning", ""),
        )
