from typing import Any

from langchain_google_genai import ChatGoogleGenerativeAI
from sqlalchemy.orm import Session

from agent.profile_extractor import extract_profile
from agent.question_generator import generate_next_question
from agent.sufficiency_checker import is_profile_sufficient
from agent.update_suggester import build_save_suggestion, detect_new_info
from config import settings
from rag.prompts import RESULTS_GENERATOR_PROMPT
from rag.retriever import search_schemes


class ConversationManager:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.llm = ChatGoogleGenerativeAI(
            model=settings.llm_model,
            temperature=settings.temperature,
            google_api_key=settings.google_api_key,
        )

    async def process(
        self,
        conversation_id: str,
        user_message: str,
        history: list[dict[str, Any]],
        profile: dict,
        tracker: dict | None = None,
    ) -> dict:
        tracker = tracker or {}
        current_profile = dict(profile or {})
        merged_profile = await extract_profile(user_message, history, current_profile)
        changed_fields = {
            field: value
            for field, value in merged_profile.items()
            if current_profile.get(field) != value
        }

        new_info = detect_new_info(changed_fields, tracker)
        current_is_sufficient, _ = is_profile_sufficient(current_profile)
        if new_info and current_is_sufficient:
            return {
                "reply": build_save_suggestion(new_info),
                "stage": "profile_update_prompt",
                "schemes_found": [],
                "profile_update_suggestion": {"new_fields": new_info},
            }

        is_sufficient, _ = is_profile_sufficient(merged_profile)
        if not is_sufficient:
            question = await generate_next_question(merged_profile, history)
            return {
                "reply": question,
                "stage": "collecting",
                "schemes_found": [],
                "profile_update_suggestion": None,
            }

        profile_query = self._profile_to_query(merged_profile)
        matched_schemes = search_schemes(profile_query, settings.top_k)
        reply = await self._generate_results_reply(merged_profile, matched_schemes)

        return {
            "reply": reply,
            "stage": "results",
            "schemes_found": matched_schemes,
            "profile_update_suggestion": None,
        }

    async def _generate_results_reply(
        self,
        profile: dict,
        matched_schemes: list[dict],
    ) -> str:
        if not matched_schemes:
            return (
                "I could not find likely matches from the current scheme knowledge base yet. "
                "Would you like to share a bit more about your goals or situation so I can refine the search?"
            )

        prompt = RESULTS_GENERATOR_PROMPT.format(
            profile_summary=self._profile_to_query(profile),
            scheme_chunks=self._format_scheme_chunks(matched_schemes),
        )

        try:
            response = await self.llm.ainvoke(prompt)
            reply = str(getattr(response, "content", response)).strip()
            return reply or self._fallback_results_reply(matched_schemes)
        except Exception:
            return self._fallback_results_reply(matched_schemes)

    def _format_scheme_chunks(self, schemes: list[dict]) -> str:
        chunks = []
        for index, scheme in enumerate(schemes, start=1):
            chunks.append(
                "\n".join(
                    [
                        f"Scheme {index}: {scheme.get('name')}",
                        f"Category: {scheme.get('category')}",
                        f"State: {scheme.get('state')}",
                        f"Source URL: {scheme.get('source_url')}",
                        f"Relevance score: {scheme.get('relevance_score')}",
                        f"Content: {scheme.get('content')}",
                    ]
                )
            )
        return "\n\n".join(chunks)

    def _fallback_results_reply(self, schemes: list[dict]) -> str:
        lines = ["Here are some schemes you likely qualify for:"]
        for scheme in schemes[: min(len(schemes), 5)]:
            reason = self._reason_from_scheme(scheme)
            lines.append(f"- {scheme.get('name')}: {reason}")
        lines.append("Which of these would you like to explore first?")
        return "\n".join(lines)

    def _reason_from_scheme(self, scheme: dict) -> str:
        parts = []
        if scheme.get("category"):
            parts.append(f"it matches the {scheme['category']} category")
        if scheme.get("state"):
            parts.append(f"it may apply in {scheme['state']}")
        return " and ".join(parts) if parts else "it aligns with your profile details"

    def _profile_to_query(self, profile: dict) -> str:
        ordered_fields = [
            "gender",
            "age",
            "state",
            "area",
            "caste_category",
            "annual_income",
            "occupation",
            "is_student",
            "education_level",
            "marital_status",
            "has_children",
            "is_pregnant",
            "has_disability",
            "bpl_card",
            "goals",
        ]
        parts = []
        for field in ordered_fields:
            value = profile.get(field)
            if value is None:
                continue
            if isinstance(value, bool):
                if value:
                    parts.append(field.replace("_", " "))
                continue
            if isinstance(value, list):
                if value:
                    parts.append(f"{field}: {', '.join(str(item) for item in value)}")
                continue
            parts.append(str(value))
        return " ".join(parts)
