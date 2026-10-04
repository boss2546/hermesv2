"""Meuu AI Gateway provider profile: 9Router AI Infrastructure (api.meuu.club)."""

from typing import Any
from providers import register_provider
from providers.base import ProviderProfile


class MeuuAIGatewayProfile(ProviderProfile):
    """Meuu AI Gateway (api.meuu.club) — 9Router high-performance AI cluster."""

    def build_api_kwargs_extras(
        self, *, reasoning_config: dict | None = None, supports_reasoning: bool = True, **ctx: Any
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        if not supports_reasoning:
            return {}, {}
        reasoning = dict(reasoning_config) if reasoning_config is not None else {"enabled": True, "effort": "medium"}
        return {"reasoning": reasoning}, {}


meuu_profile = MeuuAIGatewayProfile(
    name="meuu",
    aliases=("api.meuu.club", "meuu-gateway", "meuu_club", "9router"),
    env_vars=("MEUU_API_KEY", "OPENAI_API_KEY"),
    base_url="https://api.meuu.club/v1",
    default_headers={
        "HTTP-Referer": "https://api.meuu.club",
        "X-Title": "Hermes Agent (Meuu)",
    },
    default_aux_model="ag/gemini-2.5-flash",
)

register_provider(meuu_profile)
