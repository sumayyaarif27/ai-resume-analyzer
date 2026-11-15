"""Live check with the REAL Gemini API.

Run it with:  python -m tests.live_check

It uses a little of your API quota and the results can change from run to
run. That is why it is NOT part of pytest.
"""

import re
from pathlib import Path

from src.analyzer import AnalysisError, analyze_resume
from src.gemini_client import GeminiAPIError
from src.pdf_extractor import extract_text_from_pdf

DATA = Path("sample_data")

# Words too common to prove that a skill appears in the resume
COMMON_WORDS = {
    "and", "with", "the", "for", "skill", "skills", "knowledge", "experience",
    "including", "basic", "strong", "good", "using", "understanding",
    "ability", "working", "tools", "tool",
}


def normalize(text):
    """Lowercase and collapse spaces and new lines, to compare texts fairly."""
    return re.sub(r"\s+", " ", str(text)).strip().lower()


def numbers_in(text):
    """All numbers written in a text, like 81.34 or 2027."""
    return set(re.findall(r"\d+(?:\.\d+)?", str(text)))


def skill_is_supported(skill, resume):
    """True if the skill, or any important word of it, appears in the resume."""
    skill = normalize(skill)
    if skill in resume:
        return True
    words = re.findall(r"[a-z0-9+#.]{3,}", skill)
    return any(word in resume for word in words if word not in COMMON_WORDS)


def check_support(result, resume_text):
    """Compare the AI's claims with the resume. Returns a list of things to review."""
    resume = normalize(resume_text)
    warnings = []

    # 1. Every matching skill should have some trace in the resume
    for skill in result["matching_skills"]:
        if not skill_is_supported(skill, resume):
            warnings.append(f"Matching skill not found in resume: {skill}")

    # 2. A skill marked missing should not be written in the resume
    recs = result["recommendations"]
    missing = list(result["missing_skills"]) + list(recs.get("missing_keywords", []))
    for item in missing:
        if len(normalize(item)) >= 3 and normalize(item) in resume:
            warnings.append(f"Marked missing, but the resume contains it: {item}")

    # 3. Bullet suggestions: the original must be copied from the resume,
    #    and the new wording must not add numbers
    bullets = recs.get("bullet_point_improvements", [])
    for number, item in enumerate(bullets, start=1):
        if not isinstance(item, dict):
            continue
        original = normalize(item.get("original", ""))
        if original and original not in resume:
            warnings.append(f"Bullet #{number}: 'original' is not word-for-word in the resume")
        new_numbers = numbers_in(item.get("suggested", "")) - numbers_in(resume_text)
        if new_numbers:
            warnings.append(f"Bullet #{number}: suggestion adds numbers not in resume: {sorted(new_numbers)}")

    # 4. The summary suggestion must not add numbers either
    new_numbers = numbers_in(recs.get("summary_suggestion", "")) - numbers_in(resume_text)
    if new_numbers:
        warnings.append(f"Summary suggestion adds numbers not in resume: {sorted(new_numbers)}")

    return warnings


def run_case(label, job_file, resume_text):
    """Analyze the resume against one job and print a short report."""
    job_text = (DATA / job_file).read_text(encoding="utf-8")
    result = analyze_resume(resume_text, job_text)
    warnings = check_support(result, resume_text)

    print(f"\n[{label}] score: {result['match_score']} / 100")
    print(f"  breakdown: {result['score_breakdown']}")
    print(f"  matching skills: {len(result['matching_skills'])}, "
          f"missing skills: {len(result['missing_skills'])}")
    if warnings:
        print(f"  {len(warnings)} item(s) to review by hand:")
        for warning in warnings:
            print(f"   - {warning}")
    else:
        print("  support check: every claim was found in the resume")
    return result["match_score"]


def main():
    resume_text = extract_text_from_pdf((DATA / "resume.pdf").read_bytes())
    print("Running 3 live analyses. This takes about a minute...")

    good_1 = run_case("Good match, run 1", "sample_job.txt", resume_text)
    good_2 = run_case("Good match, run 2", "sample_job.txt", resume_text)
    poor = run_case("Poor match", "sample_job_poor.txt", resume_text)

    print("\n--- Summary ---")
    print(f"Same resume and same job, two runs: {good_1} and {good_2}")
    checks = [
        ("Good match scores 65 or more", min(good_1, good_2) >= 65),
        ("Poor match scores 45 or less", poor <= 45),
        ("Good match beats poor match by 25+ points", min(good_1, good_2) - poor >= 25),
        ("Two runs of the same job differ by 8 points or less", abs(good_1 - good_2) <= 8),
    ]
    for text, passed in checks:
        print(("PASS   " if passed else "REVIEW ") + text)


if __name__ == "__main__":
    try:
        main()
    except (AnalysisError, GeminiAPIError) as error:
        print(f"\nStopped: {error}")