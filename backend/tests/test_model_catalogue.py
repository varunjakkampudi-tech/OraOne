"""The model catalogue must match the OpenRouter models OraOne supports."""

from app.core.model_catalogue import (
    MODEL_CATALOGUE,
    SAFE_DEFAULT_MODEL,
    entitled_models,
    get_model,
)

SUPPORTED_IDS = {
    "openai/gpt-5.5",
    "anthropic/claude-sonnet-4",
    "google/gemini-2.5-pro",
    "google/gemini-2.5-flash",
}


def test_catalogue_lists_exactly_the_supported_openrouter_models() -> None:
    assert {m["id"] for m in MODEL_CATALOGUE} == SUPPORTED_IDS


def test_safe_default_is_a_catalogue_model_every_plan_can_use() -> None:
    assert get_model(SAFE_DEFAULT_MODEL) is not None
    assert SAFE_DEFAULT_MODEL in {m["id"] for m in entitled_models("free")}


def test_free_plan_gets_only_the_flash_model() -> None:
    free_ids = {m["id"] for m in entitled_models("free")}
    assert free_ids == {"google/gemini-2.5-flash"}
