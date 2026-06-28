from typing import Any

from langchain_google_genai import ChatGoogleGenerativeAI

from agent.sufficiency_checker import is_profile_sufficient
from config import settings
from rag.prompts import QUESTION_GENERATOR_PROMPT

FIELD_PRIORITY = [
    "state",
    "occupation",
    "goals",
    "age",
    "gender",
    "caste_category",
    "annual_income",
    "area",
]

FALLBACK_QUESTIONS = {
    "state": "Which state do you live in? That helps me find schemes available where you are.",
    "occupation": "What kind of work do you do, or are you currently studying?",
    "goals": "What kind of support are you hoping to find, like education, farming, housing, health, or business help?",
    "age": "Could you tell me your age? Many schemes use age ranges for eligibility.",
    "gender": "Would you like to share your gender? Some schemes are designed for specific groups.",
    "caste_category": "If you are comfortable sharing it, do you belong to SC, ST, OBC, or another background category?",
    "annual_income": "If you are comfortable sharing, what is your approximate annual household income?",
    "area": "Do you live in a rural or urban area?",
}


def _profile_summary(profile: dict) -> str:
    parts = []
    for field, value in profile.items():
        if field.startswith("_") or value is None:
            continue
        if isinstance(value, list):
            value = ", ".join(str(item) for item in value)
        parts.append(f"{field}: {value}")
    return "; ".join(parts) if parts else "No saved profile details yet."


def _prioritize_missing(missing_fields: list[str]) -> list[str]:
    ordered = [field for field in FIELD_PRIORITY if field in missing_fields]
    ordered.extend(field for field in missing_fields if field not in ordered)
    return ordered


def _fallback_question(missing_fields: list[str]) -> str:
    for field in _prioritize_missing(missing_fields):
        if field in FALLBACK_QUESTIONS:
            return FALLBACK_QUESTIONS[field]
    return "What kind of government support are you looking for right now?"


async def generate_next_question(profile: dict, history: list[dict[str, Any]]) -> str:
    _, missing_fields = is_profile_sufficient(profile)
    prioritized_missing = _prioritize_missing(missing_fields)
    if not prioritized_missing:
        return "What kind of government support would you like me to look for?"

    llm = ChatGoogleGenerativeAI(
        model=settings.llm_model,
        temperature=settings.temperature,
        google_api_key=settings.google_api_key,
    )
    prompt = QUESTION_GENERATOR_PROMPT.format(
        profile_summary=_profile_summary(profile),
        missing_fields=", ".join(prioritized_missing),
    )

    try:
        response = await llm.ainvoke(prompt)
        question = str(getattr(response, "content", response)).strip()
        return question or _fallback_question(prioritized_missing)
    except Exception:
        return _fallback_question(prioritized_missing)
