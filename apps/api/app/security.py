"""Security middleware: headers, file validation, request size."""
from __future__ import annotations
from pathlib import Path
from fastapi import HTTPException, UploadFile, Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

# Limits
MAX_FILE_BYTES = 25 * 1024 * 1024  # 25 MB
MAX_TEXT_CHARS = 500_000           # 500 KB of text
ALLOWED_EXTS = {".pdf", ".docx", ".doc", ".txt"}
ALLOWED_MIME_PREFIXES = ("application/pdf", "application/vnd.openxmlformats", "application/msword", "text/plain")


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add baseline browser security headers to every response."""

    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        response.headers.setdefault(
            "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
        )
        return response


def validate_upload(file: UploadFile) -> None:
    """Reject oversized or wrong-type uploads BEFORE saving to disk."""
    name = file.filename or ""
    ext = Path(name).suffix.lower()
    if ext not in ALLOWED_EXTS:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type {ext!r}. Allowed: {', '.join(sorted(ALLOWED_EXTS))}",
        )
    mime = (file.content_type or "").lower()
    if mime and not any(mime.startswith(p) for p in ALLOWED_MIME_PREFIXES):
        raise HTTPException(status_code=415, detail=f"Unsupported MIME type {mime!r}")


def validate_size(data: bytes) -> None:
    if len(data) > MAX_FILE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large: {len(data)} bytes (max {MAX_FILE_BYTES})",
        )


def validate_text_length(text: str) -> None:
    if len(text) > MAX_TEXT_CHARS:
        raise HTTPException(
            status_code=413,
            detail=f"Text too long: {len(text)} chars (max {MAX_TEXT_CHARS})",
        )
