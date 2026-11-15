"""Runs the resume analysis: builds the prompt, calls Gemini, checks the answer."""

import json

from src.gemini_client import ask_gemini_json
from src.prompts import SCORE_CRITERIA, build_analysis_prompt

MIN_JOB_DESCRIPTION_CHARS = 50
MAX_RESUME_CHARS = 20000
MAX_JOB_DESCRIPTION_CHARS = 10000

LIST_FIELDS = (
    "matching_skills",
    "missing_skills",
    "relevant_experience",
    "strengths",
    "weaknesses",
)
DICT_FIELDS = ("job_summary", "education_comparison", "recommendations")


class AnalysisError(Exception):
    """Raised when the analysis cannot be completed or the AI reply is unusable."""


def _parse_json(raw_text):
    """Turn Gemini's reply into a Python dictionary."""
    text = raw_text.strip()

    # Safety: remove markdown code fences if Gemini added them anyway
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
        text = text.strip()

    try:
        data = json.loads(text)
    except json.JSONDecodeError as error:
        raise AnalysisError(
            "The AI reply was not valid JSON. Please try again."
        ) from error

    if not isinstance(data, dict):
        raise AnalysisError(
            "The AI reply had an unexpected format. Please try again."
        )
    return data


def _to_number(value):
    """Convert a value to a number, or 0 if it cannot be converted."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _validate_and_clean(data):
    """Make sure the reply has every field our dashboard needs."""
    breakdown_raw = data.get("score_breakdown")
    if not isinstance(breakdown_raw, dict):
        raise AnalysisError(
            "The AI reply was missing the score breakdown. Please try again."
        )

    # Keep each part within its limit, then add them up ourselves
    breakdown = {}
    for name, max_points in SCORE_CRITERIA.items():
        points = _to_number(breakdown_raw.get(name))
        breakdown[name] = int(round(max(0, min(points, max_points))))

    data["score_breakdown"] = breakdown
    data["match_score"] = sum(breakdown.values())

    # Missing or wrong-type fields become empty, so the dashboard never crashes
    for key in LIST_FIELDS:
        if not isinstance(data.get(key), list):
            data[key] = []
    for key in DICT_FIELDS:
        if not isinstance(data.get(key), dict):
            data[key] = {}

    return data


def analyze_resume(resume_text, job_description):
    """Compare a resume with a job description and return the analysis."""
    resume_text = (resume_text or "").strip()
    job_description = (job_description or "").strip()

    if not resume_text:
        raise AnalysisError("No resume text found. Please upload a resume first.")

    if len(job_description) < MIN_JOB_DESCRIPTION_CHARS:
        raise AnalysisError(
            "Please paste a job description (at least 50 characters)."
        )

    # Cut very long text so the request stays fast and within limits
    prompt = build_analysis_prompt(
        resume_text[:MAX_RESUME_CHARS],
        job_description[:MAX_JOB_DESCRIPTION_CHARS],
    )

    raw_reply = ask_gemini_json(prompt)  # may raise GeminiAPIError
    data = _parse_json(raw_reply)
    return _validate_and_clean(data)