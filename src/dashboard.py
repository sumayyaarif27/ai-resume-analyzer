"""Draws the results dashboard from the analysis result.

Uses only built-in Streamlit components, so it needs no extra packages.
"""

import streamlit as st

from src.prompts import SCORE_CRITERIA

BREAKDOWN_LABELS = {
    "skills_match": "Skills match",
    "experience_relevance": "Experience relevance",
    "education_fit": "Education fit",
    "keyword_coverage": "Keyword coverage",
    "resume_clarity": "Resume clarity",
}


# ---------- Small helper functions ----------

def _as_list(value):
    """Return the value if it is a list, otherwise an empty list."""
    return value if isinstance(value, list) else []


def _text(value):
    """Turn a value into clean text ('' if it is missing)."""
    return str(value).strip() if value is not None else ""


def _clean_list(items):
    """Keep only non-empty text items from a list."""
    return [_text(item) for item in _as_list(items) if _text(item)]


def _escape(text):
    """Stop AI text from being shown as links or formatting."""
    for char in ("\\", "`", "*", "_", "[", "]"):
        text = text.replace(char, "\\" + char)
    return text


def _show_bullets(items):
    """Show a list of short texts as bullet points."""
    if not items:
        st.write("Nothing to show here.")
        return
    for item in items:
        st.markdown(f"- {_escape(item)}")


def _score_label(score):
    """A simple label for the score. This is only a rough guide."""
    if score >= 80:
        return "Strong match"
    if score >= 60:
        return "Good match"
    if score >= 40:
        return "Partial match"
    return "Weak match"


# ---------- Dashboard sections ----------

def _show_score(result):
    """Score card on the left, score breakdown bars on the right."""
    score = result["match_score"]
    left, right = st.columns([1, 2])

    with left:
        st.metric("Estimated match score", f"{score} / 100")
        st.progress(score / 100)
        st.write(f"**{_score_label(score)}**")
        st.caption(
            "AI-generated estimate based on the criteria shown here. "
            "It is not an official ATS score."
        )

    with right:
        st.markdown("**How the score was calculated**")
        for key, max_points in SCORE_CRITERIA.items():
            points = result["score_breakdown"][key]
            st.progress(
                points / max_points,
                text=f"{BREAKDOWN_LABELS[key]}: {points} / {max_points}",
            )


def _show_skills(result):
    """Skills summary and the lists of matching and missing skills."""
    matching = _clean_list(result["matching_skills"])
    missing = _clean_list(result["missing_skills"])
    total = len(matching) + len(missing)

    st.subheader("Skills match")
    left, right = st.columns([1, 2])

    with left:
        if total:
            st.metric("Required skills found", f"{len(matching)} of {total}")
            st.progress(len(matching) / total)
        else:
            st.info("No skills were identified.")
        count_matching, count_missing = st.columns(2)
        count_matching.metric("Matching", len(matching))
        count_missing.metric("Missing", len(missing))

    with right:
        col_match, col_missing = st.columns(2)
        with col_match:
            st.markdown("**✅ Matching skills**")
            _show_bullets(matching)
        with col_missing:
            st.markdown("**❌ Missing skills**")
            _show_bullets(missing)


def _show_strengths_weaknesses(result):
    """Two columns: what is good and what can be better."""
    st.subheader("Strengths and weaknesses")
    col_strengths, col_weaknesses = st.columns(2)
    with col_strengths:
        st.markdown("**💪 Strengths**")
        _show_bullets(_clean_list(result["strengths"]))
    with col_weaknesses:
        st.markdown("**🔧 Weaknesses**")
        _show_bullets(_clean_list(result["weaknesses"]))


def _show_experience(result):
    """Experience from the resume that fits this job."""
    st.markdown("**💼 Relevant experience**")
    shown = False
    for item in _as_list(result["relevant_experience"]):
        if isinstance(item, dict):
            role = _text(item.get("role_or_project"))
            why = _text(item.get("why_relevant"))
        else:
            role, why = _text(item), ""
        if not role and not why:
            continue
        shown = True
        with st.container(border=True):
            if role:
                st.markdown(f"**{_escape(role)}**")
            if why:
                st.markdown(_escape(why))
    if not shown:
        st.write("No clearly relevant experience was identified.")


def _show_education(result):
    """Compare the education asked for with the education on the resume."""
    education = result["education_comparison"]
    verdict = _text(education.get("meets_requirement")).lower()

    st.markdown("**🎓 Education comparison**")
    if verdict.startswith("yes"):
        st.success("Meets the education requirement")
    elif verdict.startswith("partial"):
        st.warning("Partially meets the education requirement")
    elif verdict.startswith("no"):
        st.error("Does not meet the education requirement")
    else:
        st.info("The education requirement is unclear")

    required = _text(education.get("required")) or "Not stated"
    has = _text(education.get("candidate_has")) or "Not found in resume"
    st.markdown(f"**Required:** {_escape(required)}")
    st.markdown(f"**Your resume shows:** {_escape(has)}")
    comment = _text(education.get("comment"))
    if comment:
        st.caption(comment)


def _show_recommendations(result):
    """AI suggestions to improve the resume, in tabs."""
    recs = result["recommendations"]

    st.subheader("💡 Recommendations")
    st.warning(
        "Only add a skill or keyword to your resume if it is true for you. "
        "These are suggestions for wording and highlighting. "
        "You are responsible for the facts."
    )

    tab_keywords, tab_highlight, tab_summary, tab_bullets, tab_format = st.tabs(
        [
            "🔑 Missing keywords",
            "⭐ Skills to highlight",
            "📝 Summary",
            "✏️ Bullet points",
            "🎨 Formatting",
        ]
    )

    with tab_keywords:
        st.caption("Job keywords not found in your resume. Use them only where they truthfully apply.")
        _show_bullets(_clean_list(recs.get("missing_keywords")))

    with tab_highlight:
        st.caption("Skills you already have that this job values. Make them easy to spot.")
        _show_bullets(_clean_list(recs.get("skills_to_highlight")))

    with tab_summary:
        suggestion = _text(recs.get("summary_suggestion"))
        if suggestion:
            st.markdown(_escape(suggestion))
        else:
            st.write("No summary suggestion was given.")

    with tab_bullets:
        shown = False
        for item in _as_list(recs.get("bullet_point_improvements")):
            if not isinstance(item, dict):
                continue
            original = _text(item.get("original"))
            suggested = _text(item.get("suggested"))
            if not original and not suggested:
                continue
            shown = True
            with st.container(border=True):
                col_old, col_new = st.columns(2)
                with col_old:
                    st.markdown("**From your resume**")
                    st.markdown(_escape(original))
                with col_new:
                    st.markdown("**Suggested wording**")
                    st.markdown(_escape(suggested))
                note = _text(item.get("note"))
                if note:
                    st.caption(note)
        if not shown:
            st.write("No bullet point suggestions were given.")

    with tab_format:
        _show_bullets(_clean_list(recs.get("formatting_tips")))


def render_dashboard(result):
    """Draw the whole dashboard."""
    st.header("📊 Your Results")
    _show_score(result)
    st.divider()
    _show_skills(result)
    st.divider()
    _show_strengths_weaknesses(result)

    col_experience, col_education = st.columns(2)
    with col_experience:
        _show_experience(result)
    with col_education:
        _show_education(result)

    st.divider()
    _show_recommendations(result)