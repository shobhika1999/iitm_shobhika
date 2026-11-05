from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import BinaryIO

from pypdf import PdfReader


def extract_pdf_text(source: bytes | str | Path | BinaryIO) -> dict:
    """Extract selectable text from a PDF path, bytes object, or binary stream."""
    if isinstance(source, bytes):
        reader = PdfReader(BytesIO(source))
    else:
        reader = PdfReader(str(source)) if isinstance(source, (str, Path)) else PdfReader(source)

    page_text: list[str] = []
    for page in reader.pages:
        page_text.append((page.extract_text() or "").strip())

    text = "\n\n".join(part for part in page_text if part).strip()
    return {
        "page_count": len(reader.pages),
        "extracted_text": text,
        "status": "SUCCESS" if text else "WARNING: No selectable text found",
    }
