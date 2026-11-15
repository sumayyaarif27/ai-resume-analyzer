"""Builds downloadable reports (Markdown and PDF) from an analysis result."""

import html
import io
from datetime import date

import pymupdf

from src.prompts import SCORE_CRITERIA
from src.utils import BREAKDOWN_LABELS, as_list, clean_list, clean_text, score_label

DISCLAIMER = (
    "This is an AI-generated estimate, not an official ATS score. "
    "Only add skills or keywords to your resume if they are true for you."
)

PDF_STYLE = """
h1 { color: #1f4e79; font-size: 20pt; }
h2 { color: #1f4e79; font-size: 14pt; margin-top: 14pt; }
p, li { font-size: 10pt; }
.note { color: #7a4b00; font-size: 9pt; }
"""


def _collect(result):
    """Gather and clean everything the report needs, in one place."""
    education = result["education_comparison"]
    recs = result["recommendations"]

    experience = []
    for item in as_list(result["relevant_experience"]):
        if isinstance(item, dict):
            role = clean_text(item.get("role_or_project"))
            why = clean_text(item.get("why_relevant"))
        else:
            role, why = clean_text(item), ""
        if role or why:
            experience.append((role, why))

    bullets = []
    for item in as_list(recs.get("bullet_point_improvements")):
        if isinstance(item, dict):
            original = clean_text(item.get("original"))
            suggested = clean_text(item.get("suggested"))
            note = clean_text(item.get("note"))
            if original or suggested:
                bullets.append((original, suggested, note))

    score = result["match_score"]
    return {
        "score": score,
        "label": score_label(score),
        "breakdown": [
            (BREAKDOWN_LABELS[key], result["score_breakdown"][key], max_points)
            for key, max_points in SCORE_CRITERIA.items()
        ],
        "matching": clean_list(result["matching_skills"]),
        "missing": clean_list(result["missing_skills"]),
        "strengths": clean_list(result["strengths"]),
        "weaknesses": clean_list(result["weaknesses"]),
        "experience": experience,
        "edu_verdict": clean_text(education.get("meets_requirement")) or "unclear",
        "edu_required": clean_text(education.get("required")) or "Not stated",
        "edu_has": clean_text(education.get("candidate_has")) or "Not found in resume",
        "edu_comment": clean_text(education.get("comment")),
        "keywords": clean_list(recs.get("missing_keywords")),
        "highlight": clean_list(recs.get("skills_to_highlight")),
        "summary": clean_text(recs.get("summary_suggestion")),
        "bullets": bullets,
        "formatting": clean_list(recs.get("formatting_tips")),
    }


# ---------- Markdown report ----------

def _md_list(items):
    """Markdown bullet list ('- None' when empty)."""
    return [f"- {item}" for item in items] if items else ["- None"]


def build_markdown_report(result):
    """Return the report as Markdown text."""
    d = _collect(result)
    lines = [
        "# Resume Analysis Report",
        f"Generated on {date.today():%d %B %Y}",
        "",
        f"> {DISCLAIMER}",
        "",
        "## Match score",
        f"**{d['score']} / 100** ({d['label']})",
        "",
    ]
    lines += [f"- {name}: {points} / {limit}" for name, points, limit in d["breakdown"]]

    lines += ["", "## Matching skills"] + _md_list(d["matching"])
    lines += ["", "## Missing skills"] + _md_list(d["missing"])
    lines += ["", "## Strengths"] + _md_list(d["strengths"])
    lines += ["", "## Weaknesses"] + _md_list(d["weaknesses"])

    lines += ["", "## Relevant experience"]
    if d["experience"]:
        for role, why in d["experience"]:
            lines.append(f"- **{role}**: {why}" if role else f"- {why}")
    else:
        lines.append("- None identified")

    lines += [
        "",
        "## Education comparison",
        f"- Result: {d['edu_verdict']}",
        f"- Required: {d['edu_required']}",
        f"- Your resume shows: {d['edu_has']}",
    ]
    if d["edu_comment"]:
        lines.append(f"- Comment: {d['edu_comment']}")

    lines += ["", "## Recommendations", "", "### Missing keywords"] + _md_list(d["keywords"])
    lines += ["", "### Skills to highlight"] + _md_list(d["highlight"])
    lines += ["", "### Professional summary suggestion", d["summary"] or "None"]

    lines += ["", "### Bullet point improvements"]
    if d["bullets"]:
        for original, suggested, note in d["bullets"]:
            lines.append(f"- From your resume: {original}")
            lines.append(f"  - Suggested: {suggested}")
            if note:
                lines.append(f"  - Note: {note}")
    else:
        lines.append("- None")

    lines += ["", "### Formatting tips"] + _md_list(d["formatting"])
    return "\n".join(lines) + "\n"


# ---------- PDF report ----------

def _html_list(items):
    """HTML bullet list, with all text made safe."""
    if not items:
        return "<p>None</p>"
    return "<ul>" + "".join(f"<li>{html.escape(i)}</li>" for i in items) + "</ul>"


def _build_html(result):
    """Build the HTML that PyMuPDF turns into PDF pages."""
    d = _collect(result)
    esc = html.escape

    breakdown = "".join(
        f"<li>{esc(name)}: {points} / {limit}</li>"
        for name, points, limit in d["breakdown"]
    )

    if d["experience"]:
        experience = "<ul>" + "".join(
            f"<li><b>{esc(role)}</b> {esc(why)}</li>" for role, why in d["experience"]
        ) + "</ul>"
    else:
        experience = "<p>None identified</p>"

    if d["bullets"]:
        bullets = "".join(
            f"<p><b>From your resume:</b> {esc(original)}<br>"
            f"<b>Suggested:</b> {esc(suggested)}"
            + (f"<br><i>{esc(note)}</i>" if note else "")
            + "</p>"
            for original, suggested, note in d["bullets"]
        )
    else:
        bullets = "<p>None</p>"

    education = (
        f"<p><b>Result:</b> {esc(d['edu_verdict'])}<br>"
        f"<b>Required:</b> {esc(d['edu_required'])}<br>"
        f"<b>Your resume shows:</b> {esc(d['edu_has'])}</p>"
    )
    if d["edu_comment"]:
        education += f"<p>{esc(d['edu_comment'])}</p>"

    return f"""
<h1>Resume Analysis Report</h1>
<p>Generated on {date.today():%d %B %Y}</p>
<p class="note">{esc(DISCLAIMER)}</p>

<h2>Match score</h2>
<p><b>{d['score']} / 100</b> ({esc(d['label'])})</p>
<ul>{breakdown}</ul>

<h2>Matching skills</h2>{_html_list(d['matching'])}
<h2>Missing skills</h2>{_html_list(d['missing'])}
<h2>Strengths</h2>{_html_list(d['strengths'])}
<h2>Weaknesses</h2>{_html_list(d['weaknesses'])}

<h2>Relevant experience</h2>{experience}
<h2>Education comparison</h2>{education}

<h2>Recommendations</h2>
<p><b>Missing keywords</b></p>{_html_list(d['keywords'])}
<p><b>Skills to highlight</b></p>{_html_list(d['highlight'])}
<p><b>Professional summary suggestion</b></p><p>{esc(d['summary'] or 'None')}</p>
<p><b>Bullet point improvements</b></p>{bullets}
<p><b>Formatting tips</b></p>{_html_list(d['formatting'])}
"""


def build_pdf_report(result):
    """Return the report as PDF bytes."""
    story = pymupdf.Story(html=_build_html(result), user_css=PDF_STYLE)

    buffer = io.BytesIO()
    writer = pymupdf.DocumentWriter(buffer)
    page_rect = pymupdf.paper_rect("a4")
    text_area = page_rect + (50, 50, -50, -50)  # 50-point margins

    more_pages = True
    while more_pages:
        device = writer.begin_page(page_rect)
        more_pages, _ = story.place(text_area)
        story.draw(device)
        writer.end_page()
    writer.close()

    return buffer.getvalue()