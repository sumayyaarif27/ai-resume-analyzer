"""Extracts text from uploaded PDF resumes."""

import pymupdf

MAX_FILE_SIZE_MB = 5


class PDFExtractionError(Exception):
    """Raised when a PDF cannot be read or has no usable text."""


def extract_text_from_pdf(file_bytes):
    """Take the raw bytes of a PDF and return its text."""
    if not file_bytes:
        raise PDFExtractionError("The uploaded file is empty.")

    if len(file_bytes) > MAX_FILE_SIZE_MB * 1024 * 1024:
        raise PDFExtractionError(
            f"File is too large. Maximum size is {MAX_FILE_SIZE_MB} MB."
        )

    # Every real PDF starts with these 4 characters
    if not file_bytes.startswith(b"%PDF"):
        raise PDFExtractionError("This file is not a valid PDF.")

    try:
        document = pymupdf.open(stream=file_bytes, filetype="pdf")
    except Exception:
        raise PDFExtractionError(
            "Could not open this PDF. The file may be corrupted."
        )

    with document:
        if document.needs_pass:
            raise PDFExtractionError(
                "This PDF is password-protected. Please upload an unlocked copy."
            )

        pages_text = [page.get_text() for page in document]

    text = "\n".join(pages_text).strip()

    if not text:
        raise PDFExtractionError(
            "No text found in this PDF. It may be a scanned image. "
            "Please upload a text-based PDF."
        )

    return text