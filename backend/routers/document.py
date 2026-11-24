from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from pathlib import Path
import shutil
import os

from ..database import get_db
from ..models import Document, DocumentChunk
from ..utils import (
    load_root_env,
    compute_sha256,
    safe_uuid_filename,
    is_valid_pdf_signature,
    extract_text_from_pdf,
    chunk_text,
    find_duplicate_document,
)

router = APIRouter(prefix="/documents", tags=["documents"])

# Ensure env is loaded once when module is imported
load_root_env()

MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MiB

@router.post("/")
async def upload_document(file: UploadFile = File(...), db: Session = Depends(get_db)):
    # Validate file type
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    # Read file into temp path
    temp_dir = Path("tmp")
    temp_dir.mkdir(exist_ok=True)
    uuid_name = safe_uuid_filename(file.filename)
    temp_path = temp_dir / uuid_name
    try:
        # Save uploaded content
        with temp_path.open("wb") as buffer:
            content = await file.read()
            if len(content) > MAX_FILE_SIZE:
                raise HTTPException(status_code=400, detail="File exceeds 5 MiB size limit")
            buffer.write(content)

        # Validate PDF signature
        if not is_valid_pdf_signature(temp_path):
            raise HTTPException(status_code=400, detail="File is not a valid PDF")

        # Extract text
        extracted = extract_text_from_pdf(temp_path)
        text_hash = compute_sha256(extracted)

        # Duplicate detection
        if find_duplicate_document(db, text_hash):
            raise HTTPException(status_code=400, detail="Document already uploaded (duplicate content)")

        # Chunk text
        chunks = chunk_text(extracted)

        # Store in DB within transaction
        with db.begin():
            doc = Document(
                filename=file.filename,
                file_type=file.content_type,
                file_path=str(temp_path),
                extracted_text=extracted,
            )
            db.add(doc)
            db.flush()  # get doc.id
            # Insert chunks
            for idx, chunk in enumerate(chunks):
                db.add(DocumentChunk(document_id=doc.id, chunk_index=idx, chunk_text=chunk))
        # Commit happens automatically on exit of context
        return {"message": "Document uploaded successfully", "document_id": doc.id}
    except HTTPException:
        # Propagate API errors after cleanup
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # If the document was not successfully stored, delete temp file
        # We check if the file exists and if there is no Document row with that path
        if temp_path.exists():
            # Simple heuristic: if document_id not defined in locals, assume failure
            if 'doc' not in locals():
                temp_path.unlink()

@router.get("/")
def list_documents(db: Session = Depends(get_db)):
    docs = db.query(Document).all()
    return [{
        "id": d.id,
        "filename": d.filename,
        "uploaded_at": d.uploaded_at,
    } for d in docs]
