"""Small helper functions used by more than one file."""

BREAKDOWN_LABELS = {
    "skills_match": "Skills match",
    "experience_relevance": "Experience relevance",
    "education_fit": "Education fit",
    "keyword_coverage": "Keyword coverage",
    "resume_clarity": "Resume clarity",
}


def as_list(value):
    """Return the value if it is a list, otherwise an empty list."""
    return value if isinstance(value, list) else []


def clean_text(value):
    """Turn a value into clean text ('' if it is missing)."""
    return str(value).strip() if value is not None else ""


def clean_list(items):
    """Keep only non-empty text items from a list."""
    return [clean_text(item) for item in as_list(items) if clean_text(item)]


def score_label(score):
    """A simple label for the score. This is only a rough guide."""
    if score >= 80:
        return "Strong match"
    if score >= 60:
        return "Good match"
    if score >= 40:
        return "Partial match"
    return "Weak match"