import json
from typing import Any

from langchain_google_genai import ChatGoogleGenerativeAI

from config import settings
from rag.prompts import PROFILE_EXTRACTOR_PROMPT


def _strip_json_fences(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned.removeprefix("```json").strip()
    elif cleaned.startswith("```"):
        cleaned = cleaned.removeprefix("```").strip()

    if cleaned.endswith("```"):
        cleaned = cleaned.removesuffix("```").strip()

    return cleaned


def _format_history(history: list[dict] | str) -> str:
    if isinstance(history, str):
        return history

    return "\n".join(
        f"{item.get('role', 'unknown')}: {item.get('content', '')}"
        for item in history
    )


def _merge_profile(current_profile: dict, extracted: dict) -> dict:
    merged = dict(current_profile or {})
    for field, value in extracted.items():
        if value is not None:
            merged[field] = value
        elif field not in merged:
            merged[field] = None
    return merged


async def extract_profile(
    user_message: str,
    history: list[dict] | str,
    current_profile: dict | None,
) -> dict:
    llm = ChatGoogleGenerativeAI(
        model=settings.llm_model,
        temperature=0,
        google_api_key=settings.google_api_key,
    )
    prompt = PROFILE_EXTRACTOR_PROMPT.format(
        history=_format_history(history),
        message=user_message,
    )

    try:
        response = await llm.ainvoke(prompt)
        raw_content: Any = getattr(response, "content", response)
        extracted = json.loads(_strip_json_fences(str(raw_content)))
    except Exception:
        return {}

    if not isinstance(extracted, dict):
        return {}

    return _merge_profile(current_profile or {}, extracted)
