from datetime import datetime
import re

import chromadb
from datasets import load_dataset
from langchain_core.documents import Document
from langchain_google_genai import GoogleGenerativeAIEmbeddings

from database import SessionLocal
from config import settings
from models import Scheme

BATCH_SIZE = 50


def _first_present(source: dict, *keys: str, default=None):
    for key in keys:
        value = source.get(key)
        if value not in (None, "", []):
            return value
    return default


def _clean_text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return ", ".join(str(item).strip() for item in value if str(item).strip())
    return str(value).strip()


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug or f"scheme-{datetime.utcnow().timestamp()}"


def _normalize_scheme(raw: dict) -> dict:
    name = _clean_text(_first_present(raw, "name", "scheme_name", "title"))
    description = _clean_text(
        _first_present(raw, "description", "details", "summary", "brief")
    )
    eligibility = _clean_text(
        _first_present(raw, "eligibility", "eligibility_criteria", "who_can_apply")
    )
    benefits = _clean_text(_first_present(raw, "benefits", "benefit", "assistance"))
    category = _clean_text(_first_present(raw, "category", "scheme_category", "sector"))
    state = _clean_text(_first_present(raw, "state", "state_name", "region")) or None
    ministry = _clean_text(_first_present(raw, "ministry", "department", "agency")) or None
    source_url = _clean_text(
        _first_present(raw, "source_url", "url", "scheme_url", "link")
    )
    application_url = _clean_text(
        _first_present(raw, "application_url", "apply_url", "application_link", "apply_link")
    ) or None
    application_process = _clean_text(
        _first_present(raw, "application_process", "how_to_apply")
    ) or None
    required_documents = _first_present(
        raw, "required_documents", "documents_required", default=[]
    )

    scheme_id = _clean_text(_first_present(raw, "id", "scheme_id", "slug"))
    if not scheme_id:
        scheme_id = _slugify(name or source_url or "scheme")

    return {
        "id": scheme_id,
        "name": name or "Unnamed Scheme",
        "eligibility": eligibility or "Eligibility details not available",
        "benefits": benefits or "Benefits details not available",
        "description": description or None,
        "application_process": application_process,
        "required_documents": required_documents,
        "ministry": ministry,
        "application_url": application_url,
        "category": category or "Uncategorized",
        "state": state,
        "status": "active",
        "tags": [],
        "source_url": source_url or "https://www.myscheme.gov.in/",
        "last_synced_at": datetime.utcnow(),
    }


def load_huggingface_schemes() -> list[dict]:
    dataset = load_dataset("shrijayan/gov_myscheme", split="train")
    return [_normalize_scheme(record) for record in dataset]


def tag_scheme(scheme: dict) -> list[str]:
    text = " ".join(
        [
            _clean_text(scheme.get("name")),
            _clean_text(scheme.get("eligibility")),
            _clean_text(scheme.get("description")),
            _clean_text(scheme.get("benefits")),
        ]
    ).lower()

    keyword_map = {
        "women_only": ["women", "woman", "girl", "mother", "widow"],
        "farmers_only": ["farmer", "agriculture", "crop", "kisan"],
        "students_only": ["student", "scholarship", "school", "college"],
        "sc_st_only": ["sc", "scheduled caste", "st", "scheduled tribe"],
        "obc_only": ["obc", "other backward class"],
        "bpl_only": ["bpl", "below poverty line", "poor household"],
        "labour": ["labour", "worker", "unorganised", "construction worker"],
        "ev_buyers": ["electric vehicle", "ev", "e-vehicle"],
        "housing": ["housing", "house", "home", "shelter"],
        "senior_citizens": ["senior citizen", "elderly", "old age", "pensioner"],
        "entrepreneurs": ["entrepreneur", "startup", "business", "self-employment"],
    }

    return [
        tag
        for tag, keywords in keyword_map.items()
        if any(keyword in text for keyword in keywords)
    ]


def scheme_to_document(scheme: dict) -> Document:
    scheme["tags"] = tag_scheme(scheme)
    content = "\n".join(
        [
            f"Name: {scheme['name']}",
            f"Category: {scheme['category']}",
            f"State: {scheme.get('state') or 'National'}",
            f"Eligibility: {scheme['eligibility']}",
            f"Benefits: {scheme['benefits']}",
        ]
    )
    return Document(
        page_content=content,
        metadata={
            "scheme_id": scheme["id"],
            "name": scheme["name"],
            "category": scheme["category"],
            "state": scheme.get("state") or "National",
            "source_url": scheme["source_url"],
            "tags": scheme["tags"],
        },
    )


def ingest_all(schemes: list[dict]) -> None:
    db = SessionLocal()
    embeddings = GoogleGenerativeAIEmbeddings(
        model=settings.embedding_model,
        google_api_key=settings.google_api_key,
    )
    client = chromadb.PersistentClient(path=settings.chroma_persist_directory)
    collection = client.get_or_create_collection(name=settings.chroma_collection_name)

    try:
        existing_ids = {scheme_id for (scheme_id,) in db.query(Scheme.id).all()}
        new_schemes = [scheme for scheme in schemes if scheme["id"] not in existing_ids]

        if not new_schemes:
            print("No new schemes to ingest.")
            return

        for scheme in new_schemes:
            db.add(Scheme(**scheme))
        db.commit()
        print(f"Saved {len(new_schemes)} new schemes to SQLite.")

        documents = [scheme_to_document(scheme) for scheme in new_schemes]
        for start in range(0, len(documents), BATCH_SIZE):
            batch = documents[start : start + BATCH_SIZE]
            batch_texts = [doc.page_content for doc in batch]
            batch_ids = [doc.metadata["scheme_id"] for doc in batch]
            batch_metadatas = []
            for doc in batch:
                metadata = dict(doc.metadata)
                metadata["tags"] = ", ".join(metadata.get("tags", []))
                batch_metadatas.append(metadata)

            batch_embeddings = embeddings.embed_documents(batch_texts)
            collection.add(
                ids=batch_ids,
                documents=batch_texts,
                metadatas=batch_metadatas,
                embeddings=batch_embeddings,
            )
            print(
                f"Ingested vector batch {start + 1}-{start + len(batch)} of {len(documents)}."
            )
    finally:
        db.close()


if __name__ == "__main__":
    schemes = load_huggingface_schemes()
    ingest_all(schemes)
