"""Security guard tests: file size, type, headers."""
import io
from unittest.mock import MagicMock
import pytest
from fastapi import HTTPException

from app import security as sec


def _fake_upload(name: str, mime: str = "application/pdf"):
    f = MagicMock()
    f.filename = name
    f.content_type = mime
    return f


def test_validate_upload_rejects_bad_extension():
    with pytest.raises(HTTPException) as ei:
        sec.validate_upload(_fake_upload("evil.exe"))
    assert ei.value.status_code == 415


def test_validate_upload_accepts_pdf():
    sec.validate_upload(_fake_upload("contract.pdf"))


def test_validate_upload_accepts_docx():
    sec.validate_upload(_fake_upload(
        "contract.docx",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ))


def test_validate_size_rejects_oversize():
    big = b"x" * (sec.MAX_FILE_BYTES + 1)
    with pytest.raises(HTTPException) as ei:
        sec.validate_size(big)
    assert ei.value.status_code == 413


def test_validate_text_length_rejects_oversize():
    with pytest.raises(HTTPException) as ei:
        sec.validate_text_length("x" * (sec.MAX_TEXT_CHARS + 1))
    assert ei.value.status_code == 413


def test_validate_text_length_accepts_normal():
    sec.validate_text_length("standard contract text")
