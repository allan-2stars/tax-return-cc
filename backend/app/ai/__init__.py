from app.ai.base import AIAdapter
from app.config import settings


def get_ai_adapter(workspace_id: str = "") -> AIAdapter:
    provider_name = settings.AI_PROVIDER
    if provider_name == "claude":
        from app.ai.providers.claude import ClaudeProvider
        provider = ClaudeProvider()
    else:
        raise ValueError(f"Unknown AI_PROVIDER: {provider_name!r}")
    return AIAdapter(provider=provider, workspace_id=workspace_id)
