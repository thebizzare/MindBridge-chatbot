
import os
import hashlib
import uuid
from pathlib import Path
from typing import List

from pdfminer.high_level import extract_text as pdf_extract_text
from pdfminer.pdfparser import PDFSyntaxError


def load_root_env() -> None:
    """Load the root .env file located at the project root."""
    from dotenv import load_dotenv

    root_env_path = Path(__file__).resolve().parents[1] / ".env"
    load_dotenv(dotenv_path=root_env_path)


def get_hf_token() -> str:
    """Return HF_TOKEN from the environment or raise a clear error."""
    token = os.getenv("HF_TOKEN")
    if not token:
        raise EnvironmentError("HF_TOKEN not set in the root .env file")
    return token


def safe_uuid_filename(original_name: str) -> str:
    """Create a UUID-based filename preserving the original extension."""
    ext = Path(original_name).suffix
    return f"{uuid.uuid4()}{ext}"


def compute_sha256(text: str) -> str:
    """Return the hexadecimal SHA-256 hash of the given text."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def is_valid_pdf_signature(file_path: Path) -> bool:
    """Check whether a file starts with the PDF signature."""
    try:
        with file_path.open("rb") as f:
            header = f.read(5)
        return header == b"%PDF-"
    except Exception:
        return False


def extract_text_from_pdf(file_path: Path) -> str:
    """Extract readable text from a PDF."""
    try:
        text = pdf_extract_text(str(file_path))
        if not text.strip():
            raise RuntimeError("No extractable text found in PDF")
        return text
    except PDFSyntaxError as e:
        raise RuntimeError(f"PDF syntax error: {e}") from e
    except Exception as e:
        raise RuntimeError(f"Failed to extract PDF text: {e}") from e


def chunk_text(
    text: str,
    max_chunk_size: int = 500,
    overlap: int = 100
) -> List[str]:
    """Split text into 500-character chunks with 100-character overlap."""

    if max_chunk_size <= 0:
        raise ValueError("max_chunk_size must be greater than zero")

    if overlap < 0 or overlap >= max_chunk_size:
        raise ValueError("overlap must be between 0 and max_chunk_size")

    text = "\n\n".join(
        paragraph.strip()
        for paragraph in text.split("\n\n")
        if paragraph.strip()
    )

    chunks = []
    start = 0

    while start < len(text):
        end = min(start + max_chunk_size, len(text))

        # Prefer ending at a paragraph boundary when possible.
        if end < len(text):
            boundary = text.rfind("\n\n", start + 1, end)
            if boundary > start:
                end = boundary

        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        if end >= len(text):
            break

        start = max(start + 1, end - overlap)

    return chunks


def find_duplicate_document(session, new_text_hash: str) -> bool:
    """Check existing documents for matching extracted-text hashes."""
    from .models import Document

    docs = session.query(Document.id, Document.extracted_text).all()

    for _, txt in docs:
        if txt is None:
            continue

        if compute_sha256(txt) == new_text_hash:
            return True

    return False
