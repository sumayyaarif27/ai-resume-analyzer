"""Tests for src/pdf_extractor.py. No internet or API key needed."""

import pymupdf
import pytest

from src.pdf_extractor import PDFExtractionError, extract_text_from_pdf


def make_pdf(text=None, password=None):
    """Build a small PDF in memory. With text=None the page stays blank."""
    document = pymupdf.open()
    page = document.new_page()
    if text:
        page.insert_text((72, 72), text)
    if password:
        pdf_bytes = document.tobytes(
            encryption=pymupdf.PDF_ENCRYPT_AES_256,
            user_pw=password,
            owner_pw="owner-secret",
        )
    else:
        pdf_bytes = document.tobytes()
    document.close()
    return pdf_bytes


def test_valid_pdf_returns_text():
    pdf_bytes = make_pdf("Hello resume world")
    assert "Hello resume world" in extract_text_from_pdf(pdf_bytes)


def test_empty_file_is_rejected():
    with pytest.raises(PDFExtractionError, match="empty"):
        extract_text_from_pdf(b"")


def test_non_pdf_file_is_rejected():
    with pytest.raises(PDFExtractionError, match="not a valid PDF"):
        extract_text_from_pdf(b"This is plain text, not a PDF.")


def test_corrupted_pdf_is_rejected():
    with pytest.raises(PDFExtractionError):
        extract_text_from_pdf(b"%PDF-1.5 this file is damaged")


def test_pdf_without_text_is_rejected():
    with pytest.raises(PDFExtractionError, match="No text found"):
        extract_text_from_pdf(make_pdf(text=None))


def test_too_large_file_is_rejected():
    too_big = b"%PDF" + b"0" * (6 * 1024 * 1024)
    with pytest.raises(PDFExtractionError, match="too large"):
        extract_text_from_pdf(too_big)


def test_password_protected_pdf_is_rejected():
    locked = make_pdf("Secret text", password="my-password")
    with pytest.raises(PDFExtractionError, match="password"):
        extract_text_from_pdf(locked)