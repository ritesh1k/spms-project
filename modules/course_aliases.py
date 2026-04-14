import re


COURSE_ALIASES = {
    "BCA": [
        "BCA",
        "Bachelor of Computer Application",
        "Bachelor of Computer Applications",
    ],
    "BTECH": [
        "BTech",
        "B.Tech",
        "Bachelor of Technology",
    ],
    "MCA": [
        "MCA",
        "Master of Computer Application",
        "Master of Computer Applications",
    ],
    "MTECH": [
        "MTech",
        "M.Tech",
        "Master of Technology",
    ],
}


def _normalize_text(value):
    if value is None:
        return ""
    text = str(value).strip().lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def canonical_course_name(value):
    normalized = _normalize_text(value)
    if not normalized:
        return value

    for canonical, aliases in COURSE_ALIASES.items():
        all_variants = [canonical] + aliases
        if normalized in {_normalize_text(v) for v in all_variants}:
            if canonical == "BTECH":
                return "B.Tech"
            if canonical == "MTECH":
                return "M.Tech"
            return canonical

    return str(value).strip()


def get_course_aliases(value):
    canonical_value = canonical_course_name(value)
    normalized = _normalize_text(canonical_value)

    for canonical, aliases in COURSE_ALIASES.items():
        variants = [canonical] + aliases
        normalized_variants = {_normalize_text(v) for v in variants}
        if normalized in normalized_variants:
            result = []
            for variant in variants:
                cleaned = str(variant).strip()
                if cleaned and cleaned not in result:
                    result.append(cleaned)
            canonical_display = canonical_course_name(canonical)
            if canonical_display not in result:
                result.insert(0, canonical_display)
            return result

    return [str(canonical_value).strip()]


def course_matches(value_a, value_b):
    return _normalize_text(canonical_course_name(value_a)) == _normalize_text(canonical_course_name(value_b))
