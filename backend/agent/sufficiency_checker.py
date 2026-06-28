HIGH_VALUE_FIELDS = ["annual_income", "caste_category", "area"]


def _has_value(profile: dict, field: str) -> bool:
    value = profile.get(field)
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, list):
        return len(value) > 0
    return True


def get_missing_high_value(profile: dict) -> list[str]:
    return [field for field in HIGH_VALUE_FIELDS if not _has_value(profile, field)]


def is_profile_sufficient(profile: dict) -> tuple[bool, list[str]]:
    score = 0
    missing_fields = []

    if _has_value(profile, "age") or _has_value(profile, "gender"):
        score += 1
    else:
        missing_fields.extend(["age", "gender"])

    if _has_value(profile, "state"):
        score += 2
    else:
        missing_fields.append("state")

    if (
        _has_value(profile, "occupation")
        or _has_value(profile, "is_student")
        or _has_value(profile, "goals")
    ):
        score += 2
    else:
        missing_fields.extend(["occupation", "goals"])

    for field in get_missing_high_value(profile):
        if field not in missing_fields:
            missing_fields.append(field)

    return score >= 4, missing_fields
