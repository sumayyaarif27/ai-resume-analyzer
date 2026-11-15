"""Streamlit app for the AI-Powered Resume Analyzer & Job Matcher."""

import streamlit as st

from src.analyzer import AnalysisError, analyze_resume
from src.dashboard import render_dashboard
from src.gemini_client import GeminiAPIError
from src.pdf_extractor import PDFExtractionError, extract_text_from_pdf
from src.report_generator import build_markdown_report, build_pdf_report

st.set_page_config(
    page_title="AI Resume Analyzer",
    page_icon="📄",
    layout="wide",
)

st.title("📄 AI-Powered Resume Analyzer & Job Matcher")
st.write(
    "Upload your resume and compare it with a job description to see "
    "your match, missing skills and ways to improve."
)

# ---------- Step 1: Resume upload ----------
st.header("1. Upload your resume")
uploaded_file = st.file_uploader("Choose a PDF resume", type=["pdf"])

resume_text = ""

if uploaded_file is not None:
    try:
        resume_text = extract_text_from_pdf(uploaded_file.getvalue())
    except PDFExtractionError as error:
        st.error(str(error))
    else:
        st.success(f"Resume read successfully ({len(resume_text)} characters).")
        with st.expander("View extracted resume text"):
            st.text(resume_text)

# ---------- Step 2: Job description ----------
st.header("2. Paste the job description")
job_description = st.text_area(
    "Job description",
    height=250,
    placeholder="Paste the full job description here...",
)

# ---------- Step 3: Analyze ----------
st.header("3. Analyze")
analyze_clicked = st.button("🔍 Analyze Resume", type="primary")

if analyze_clicked:
    if not resume_text:
        st.warning("Please upload a valid PDF resume first.")
    elif not job_description.strip():
        st.warning("Please paste a job description.")
    else:
        try:
            with st.spinner("Analyzing your resume with Gemini. This can take up to 30 seconds..."):
                st.session_state["result"] = analyze_resume(resume_text, job_description)
        except (AnalysisError, GeminiAPIError) as error:
            st.error(str(error))

# ---------- Results dashboard ----------
result = st.session_state.get("result")
if result:
    st.divider()
    render_dashboard(result)

    # ---------- Download report ----------
    st.divider()
    st.subheader("📥 Download your report")
    st.caption("The report may contain details taken from your resume. Keep it private.")

    col_pdf, col_text = st.columns(2)

    with col_pdf:
        try:
            pdf_bytes = build_pdf_report(result)
        except Exception as error:
            st.warning(f"The PDF report could not be created ({error}). Use the text report instead.")
        else:
            st.download_button(
                "⬇️ Download PDF report",
                data=pdf_bytes,
                file_name="resume_analysis_report.pdf",
                mime="application/pdf",
            )

    with col_text:
        st.download_button(
            "⬇️ Download text report (.md)",
            data=build_markdown_report(result),
            file_name="resume_analysis_report.md",
            mime="text/markdown",
        )

    with st.expander("Raw analysis data (for testing)"):
        st.json(result)