"""AI model catalogue (Phase 12, Module 13).

A static registry of the chat models the platform can route to, with the
metadata the model router and UI need: vendor, family, context window,
indicative cost, capability tags, and the minimum plan tier required to
use the model. Inference flows through the single ``app.providers`` seam (OpenRouter).
This catalogue governs which model id the router resolves to.
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


# Every model is addressed by its OpenRouter id (``vendor/model``). Fields:
#   id                 OpenRouter model id sent with each request
#   label              name shown in the product
#   vendor             organization that trained the model
#   family             model line, used for grouping
#   tier               "standard" or "premium"
#   context_window     maximum tokens of context
#   input_per_1k       indicative USD price per 1K prompt tokens
#   output_per_1k      indicative USD price per 1K completion tokens
#   capabilities       feature tags
#   min_plan           lowest plan tier that may use the model
#   typical_latency_ms rough median latency, used by the "fastest" strategy
#
# Prices are indicative and must be verified them against OpenRouter's pricing page before
# relying on cost figures.
MODEL_CATALOGUE: list[dict] = [
    {
        "id": "openai/gpt-5.5",
        "label": "GPT-5.5",
        "vendor": "openai",
        "family": "gpt-5",
        "tier": "premium",
        "context_window": 400000,
        "input_per_1k": 0.00125,
        "output_per_1k": 0.01,
        "capabilities": ["chat", "tools", "vision"],
        "min_plan": "business",
        "typical_latency_ms": 1500,
    },
    {
        "id": "anthropic/claude-sonnet-4",
        "label": "Claude Sonnet 4",
        "vendor": "anthropic",
        "family": "claude-4",
        "tier": "premium",
        "context_window": 200000,
        "input_per_1k": 0.003,
        "output_per_1k": 0.015,
        "capabilities": ["chat", "tools", "vision"],
        "min_plan": "business",
        "typical_latency_ms": 1600,
    },
    {
        "id": "google/gemini-2.5-pro",
        "label": "Gemini 2.5 Pro",
        "vendor": "google",
        "family": "gemini-2.5",
        "tier": "premium",
        "context_window": 1000000,
        "input_per_1k": 0.00125,
        "output_per_1k": 0.01,
        "capabilities": ["chat", "tools", "vision"],
        "min_plan": "starter",
        "typical_latency_ms": 1300,
    },
    {
        "id": "google/gemini-2.5-flash",
        "label": "Gemini 2.5 Flash",
        "vendor": "google",
        "family": "gemini-2.5",
        "tier": "standard",
        "context_window": 1000000,
        "input_per_1k": 0.0003,
        "output_per_1k": 0.0025,
        "capabilities": ["chat", "tools", "vision"],
        "min_plan": "free",
        "typical_latency_ms": 800,
    },
]

MODELS_BY_ID: dict[str, dict] = {m["id"]: m for m in MODEL_CATALOGUE}

# Safe universal fallback that every plan may use.
SAFE_DEFAULT_MODEL = "google/gemini-2.5-flash"


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
