FIELD_LABELS = {
    "name": "your name",
    "age": "your age",
    "gender": "your gender",
    "state": "your state",
    "area": "whether you live in a rural or urban area",
    "caste_category": "your background category",
    "annual_income": "your annual income range",
    "has_disability": "your disability status",
    "bpl_card": "your BPL card status",
    "occupation": "your occupation",
    "is_student": "whether you are a student",
    "education_level": "your education level",
    "marital_status": "your marital status",
    "has_children": "whether you have children",
    "is_pregnant": "pregnancy-related eligibility information",
    "goals": "your goals",
}


def _has_value(value: object) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, list):
        return len(value) > 0
    return True


def detect_new_info(extracted: dict, tracker: dict) -> dict:
    return {
        field: value
        for field, value in extracted.items()
        if not field.startswith("_")
        and _has_value(value)
        and not tracker.get(field, False)
    }


def build_save_suggestion(new_fields: dict) -> str:
    labels = [
        FIELD_LABELS.get(field, field.replace("_", " "))
        for field in new_fields
        if _has_value(new_fields[field])
    ]

    if not labels:
        return "I noticed some new profile details. Want me to save them to find better schemes for you?"

    if len(labels) == 1:
        details = labels[0]
    else:
        details = ", ".join(labels[:-1]) + f", and {labels[-1]}"

    return (
        f"I noticed you mentioned {details}. "
        "Want me to save this to find better schemes for you?"
    )
