"""Document parsing: PDF (pdfplumber) / DOCX (python-docx) / fallback OCR placeholder."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ParsedDoc:
    text: str
    pages: list[str]          # per-page text
    page_offsets: list[int]   # start char offset of each page in `text`
    source_kind: str          # "pdf" | "docx" | "image"


def parse(path: Path, filename: str) -> ParsedDoc:
    ext = Path(filename).suffix.lower()
    if ext == ".pdf":
        return _parse_pdf(path)
    if ext in (".docx", ".doc"):
        return _parse_docx(path)
    if ext in (".png", ".jpg", ".jpeg"):
        return _parse_image(path)
    raise ValueError(f"Unsupported file type: {ext}")


def _parse_pdf(path: Path) -> ParsedDoc:
    import pdfplumber

    pages: list[str] = []
    with pdfplumber.open(str(path)) as pdf:
        for page in pdf.pages:
            pages.append(page.extract_text() or "")

    # If PDF has no text layer at all, fall back to OCR
    if sum(len(p) for p in pages) < 50:
        return _ocr_fallback(path, kind="pdf")

    return _assemble(pages, "pdf")


def _parse_docx(path: Path) -> ParsedDoc:
    from docx import Document

    doc = Document(str(path))
    text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    return _assemble([text], "docx")


def _parse_image(path: Path) -> ParsedDoc:
    return _ocr_fallback(path, kind="image")


def _ocr_fallback(path: Path, kind: str) -> ParsedDoc:
    """Document AI fallback. Not wired in hackathon mode — raise clear error."""
    raise NotImplementedError(
        "Document appears to be scanned/image-based. "
        "Document AI OCR fallback is not enabled in hackathon mode. "
        "Use a digital PDF or DOCX."
    )


def _assemble(pages: list[str], kind: str) -> ParsedDoc:
    text_parts: list[str] = []
    page_offsets: list[int] = []
    cursor = 0
    for p in pages:
        page_offsets.append(cursor)
        text_parts.append(p)
        cursor += len(p) + 2  # +2 for join "\n\n"
    text = "\n\n".join(text_parts)
    return ParsedDoc(text=text, pages=pages, page_offsets=page_offsets, source_kind=kind)


def chunk_text(text: str, page_offsets: list[int], window: int = 1500, overlap: int = 200) -> list[dict]:
    """Sliding-window chunker. Returns list of {text, offset_start, offset_end, page_number}."""
    out: list[dict] = []
    i = 0
    n = len(text)
    while i < n:
        end = min(i + window, n)
        chunk = text[i:end]
        page = _page_for_offset(i, page_offsets)
        out.append({
            "text": chunk,
            "offset_start": i,
            "offset_end": end,
            "page_number": page,
        })
        if end >= n:
            break
        i = end - overlap
    return out


def _page_for_offset(offset: int, page_offsets: list[int]) -> int:
    page = 1
    for idx, po in enumerate(page_offsets):
        if offset >= po:
            page = idx + 1
        else:
            break
    return page
