import os
import re
import sys
from csv import DictReader
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import chromadb
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings

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


def load_local_csv_schemes() -> list[dict]:
    csv_path = Path(__file__).resolve().parent / "data" / "schemes.csv"
    if not csv_path.exists():
        raise FileNotFoundError(f"Scheme CSV not found: {csv_path}")

    def parse_state(level: str) -> str | None:
        cleaned = _clean_text(level)
        if not cleaned:
            return None
        if "central" in cleaned.lower():
            return "Central"

        parts = [part.strip() for part in cleaned.split(",") if part.strip()]
        if not parts:
            return None

        last_part = parts[-1]
        if last_part.lower() == "state" and len(parts) > 1:
            return parts[0]
        return last_part

    schemes: list[dict] = []
    seen_slugs: set[str] = set()
    skipped_missing = 0
    skipped_duplicates = 0

    with csv_path.open("r", encoding="utf-8-sig", newline="") as csv_file:
        reader = DictReader(csv_file)
        for row in reader:
            slug = _clean_text(row.get("slug"))
            name = _clean_text(row.get("scheme_name"))
            if not slug or not name:
                skipped_missing += 1
                continue
            if slug in seen_slugs:
                skipped_duplicates += 1
                continue
            seen_slugs.add(slug)

            raw_category = _clean_text(row.get("schemeCategory"))
            categories = [part.strip() for part in raw_category.split(",") if part.strip()]
            raw_tags = _clean_text(row.get("tags"))
            tags = [part.strip() for part in raw_tags.split(",") if part.strip()]

            schemes.append(
                {
                    "id": slug,
                    "name": name,
                    "eligibility": _clean_text(row.get("eligibility"))
                    or "Eligibility details not available",
                    "benefits": _clean_text(row.get("benefits"))
                    or "Benefits details not available",
                    "description": _clean_text(row.get("details")) or None,
                    "application_process": _clean_text(row.get("application")) or None,
                    "required_documents": _clean_text(row.get("documents")) or None,
                    "ministry": None,
                    "application_url": None,
                    "category": categories[0] if categories else "Uncategorized",
                    "state": parse_state(row.get("level", "")),
                    "status": "active",
                    "tags": tags,
                    "source_url": f"https://www.myscheme.gov.in/schemes/{slug}",
                    "last_synced_at": datetime.utcnow(),
                }
            )

    print(
        f"Loaded {len(schemes)} schemes from {csv_path}. "
        f"Skipped {skipped_missing} rows with missing slug/name and "
        f"{skipped_duplicates} duplicate slugs."
    )
    return schemes


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
    from database import engine
    import models

    models.Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    embeddings = HuggingFaceEmbeddings(
        model_name=settings.embedding_model,
        encode_kwargs={"normalize_embeddings": True},
    )
    client = chromadb.PersistentClient(path=settings.chroma_persist_directory)
    collection = client.get_or_create_collection(name=settings.chroma_collection_name)

    try:
        existing_ids = {scheme_id for (scheme_id,) in db.query(Scheme.id).all()}
        new_schemes = [scheme for scheme in schemes if scheme["id"] not in existing_ids]

        for scheme in new_schemes:
            db.add(Scheme(**scheme))
        if new_schemes:
            db.commit()
            print(f"Saved {len(new_schemes)} new schemes to SQLite.")
        else:
            print("No new schemes to save in SQLite.")

        documents = [scheme_to_document(scheme) for scheme in schemes]
        total_batches = (len(documents) + BATCH_SIZE - 1) // BATCH_SIZE
        for start in range(0, len(documents), BATCH_SIZE):
            batch = documents[start : start + BATCH_SIZE]
            batch_number = (start // BATCH_SIZE) + 1
            batch_texts = [doc.page_content for doc in batch]
            batch_ids = [doc.metadata["scheme_id"] for doc in batch]
            batch_metadatas = []
            for doc in batch:
                metadata = dict(doc.metadata)
                metadata["tags"] = ", ".join(metadata.get("tags", []))
                batch_metadatas.append(metadata)

            print(f"Embedding batch {batch_number}/{total_batches}...")
            batch_embeddings = embeddings.embed_documents(batch_texts)
            collection.add(
                ids=batch_ids,
                documents=batch_texts,
                metadatas=batch_metadatas,
                embeddings=batch_embeddings,
            )
            print(f"Ingested vector batch {start + 1}-{start + len(batch)} of {len(documents)}.")
    finally:
        db.close()


if __name__ == "__main__":
    schemes = load_local_csv_schemes()
    ingest_all(schemes)
