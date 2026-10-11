"""AI model catalogue (Phase 12, Module 13).

A static registry of the chat models the platform can route to, with the
metadata the model router and UI need: provider, family, context window,
indicative cost, capability tags, and the minimum plan tier required to
use the model. Actual inference still flows through the single
``app.providers`` seam — this catalogue governs *which* model id the
router resolves to, not how bytes reach a vendor.
"""

from __future__ import annotations

# Plan tiers ranked low → high. Mirrors billing PlanCode ordering.
PLAN_RANK: dict[str, int] = {
    "free": 0,
    "starter": 1,
    "business": 2,
    "enterprise": 3,
}


def plan_rank(code: str) -> int:
    return PLAN_RANK.get((code or "free").lower(), 0)


# Each model: id (sent to provider), label, provider, family, tier
# (standard|premium), context_window, input/output cost per 1K tokens
# (USD, indicative), capability tags, and min_plan gate.
MODEL_CATALOGUE: list[dict] = [
    {
        "id": "gpt-4o-mini",
        "label": "GPT-4o mini",
        "provider": "openai",
        "family": "gpt-4o",
        "tier": "standard",
        "context_window": 128000,
        "input_per_1k": 0.00015,
        "output_per_1k": 0.0006,
        "capabilities": ["chat", "tools", "vision"],
        "min_plan": "free",
        "typical_latency_ms": 700,
    },
    {
        "id": "gpt-4o",
        "label": "GPT-4o",
        "provider": "openai",
        "family": "gpt-4o",
        "tier": "premium",
        "context_window": 128000,
        "input_per_1k": 0.0025,
        "output_per_1k": 0.01,
        "capabilities": ["chat", "tools", "vision"],
        "min_plan": "starter",
        "typical_latency_ms": 1400,
    },
    {
        "id": "gpt-5.5",
        "label": "GPT-5.5",
        "provider": "openai",
        "family": "gpt-5",
        "tier": "premium",
        "context_window": 256000,
        "input_per_1k": 0.005,
        "output_per_1k": 0.02,
        "capabilities": ["chat", "tools", "vision", "reasoning"],
        "min_plan": "business",
        "typical_latency_ms": 2600,
    },
    {
        "id": "claude-3-5-haiku",
        "label": "Claude 3.5 Haiku",
        "provider": "anthropic",
        "family": "claude-3.5",
        "tier": "standard",
        "context_window": 200000,
        "input_per_1k": 0.0008,
        "output_per_1k": 0.004,
        "capabilities": ["chat", "tools"],
        "min_plan": "free",
        "typical_latency_ms": 800,
    },
    {
        "id": "claude-3-5-sonnet",
        "label": "Claude 3.5 Sonnet",
        "provider": "anthropic",
        "family": "claude-3.5",
        "tier": "premium",
        "context_window": 200000,
        "input_per_1k": 0.003,
        "output_per_1k": 0.015,
        "capabilities": ["chat", "tools", "vision"],
        "min_plan": "starter",
        "typical_latency_ms": 1600,
    },
    {
        "id": "claude-3-opus",
        "label": "Claude 3 Opus",
        "provider": "anthropic",
        "family": "claude-3",
        "tier": "premium",
        "context_window": 200000,
        "input_per_1k": 0.015,
        "output_per_1k": 0.075,
        "capabilities": ["chat", "tools", "vision", "reasoning"],
        "min_plan": "business",
        "typical_latency_ms": 3200,
    },
    {
        "id": "gemini-1.5-flash",
        "label": "Gemini 1.5 Flash",
        "provider": "google",
        "family": "gemini-1.5",
        "tier": "standard",
        "context_window": 1000000,
        "input_per_1k": 0.000075,
        "output_per_1k": 0.0003,
        "capabilities": ["chat", "vision"],
        "min_plan": "free",
        "typical_latency_ms": 600,
    },
    {
        "id": "gemini-1.5-pro",
        "label": "Gemini 1.5 Pro",
        "provider": "google",
        "family": "gemini-1.5",
        "tier": "premium",
        "context_window": 2000000,
        "input_per_1k": 0.00125,
        "output_per_1k": 0.005,
        "capabilities": ["chat", "tools", "vision"],
        "min_plan": "starter",
        "typical_latency_ms": 1500,
    },
    {
        "id": "amazon.nova-pro",
        "label": "Amazon Nova Pro",
        "provider": "bedrock",
        "family": "nova",
        "tier": "premium",
        "context_window": 300000,
        "input_per_1k": 0.0008,
        "output_per_1k": 0.0032,
        "capabilities": ["chat", "tools", "vision"],
        "min_plan": "business",
        "typical_latency_ms": 1200,
    },
]

MODELS_BY_ID: dict[str, dict] = {m["id"]: m for m in MODEL_CATALOGUE}

# Safe universal fallback that every plan may use.
SAFE_DEFAULT_MODEL = "gpt-4o-mini"


def get_model(model_id: str) -> dict | None:
    return MODELS_BY_ID.get(model_id)


def cost_for(model_id: str | None, prompt_tokens: int, completion_tokens: int) -> float:
    """Indicative USD cost for a single completion.

    Uses the catalogue's per-1K input/output pricing. Unknown models fall
    back to the safe default's pricing so a number is always produced for
    observability. Returns a float rounded to 6 dp.
    """
    model = MODELS_BY_ID.get(model_id or "") or MODELS_BY_ID.get(SAFE_DEFAULT_MODEL, {})
    in_rate = float(model.get("input_per_1k", 0.0))
    out_rate = float(model.get("output_per_1k", 0.0))
    cost = (max(0, prompt_tokens) / 1000.0) * in_rate + (
        max(0, completion_tokens) / 1000.0
    ) * out_rate
    return round(cost, 6)


def is_entitled(model: dict, plan_code: str) -> bool:
    return plan_rank(plan_code) >= plan_rank(model.get("min_plan", "free"))


def entitled_models(plan_code: str) -> list[dict]:
    return [m for m in MODEL_CATALOGUE if is_entitled(m, plan_code)]


# Routing strategies the org may pick to bias model selection.
ROUTING_STRATEGIES = ("balanced", "cheapest", "fastest", "quality")
DEFAULT_ROUTING_STRATEGY = "balanced"


def blended_price(model: dict) -> float:
    """A single comparable price for a model (weights output 3:1 vs input)."""
    return float(model.get("input_per_1k", 0.0)) + 3.0 * float(
        model.get("output_per_1k", 0.0)
    )


def order_by_strategy(models: list[dict], strategy: str) -> list[dict]:
    """Return ``models`` ordered to reflect a routing strategy.

    * ``cheapest`` — lowest blended price first.
    * ``fastest``  — lowest typical latency first.
    * ``quality``  — premium tier and pricier (more capable) models first.
    * ``balanced`` — catalogue order (a curated default).
    """
    strat = (strategy or DEFAULT_ROUTING_STRATEGY).lower()
    if strat == "cheapest":
        return sorted(models, key=blended_price)
    if strat == "fastest":
        return sorted(models, key=lambda m: m.get("typical_latency_ms", 9_999))
    if strat == "quality":
        return sorted(
            models,
            key=lambda m: (0 if m.get("tier") == "premium" else 1, -blended_price(m)),
        )
    return list(models)
