from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
import re
import math
from collections import Counter
from typing import List, Dict

def _tokenize(text: str) -> List[str]:
    """Simple whitespace and punctuation tokenizer, lower‑cased."""
    # split on any non‑alphanumeric character
    return re.findall(r"\b\w+\b", text.lower())

def _compute_idf(corpus: List[str]) -> Dict[str, float]:
    """Compute inverse document frequency for each term.
    Uses smoothing: idf = log((N + 1) / (df + 1)) + 1.
    """
    N = len(corpus)
    df: Counter = Counter()
    for doc in corpus:
        terms = set(_tokenize(doc))
        df.update(terms)
    idf: Dict[str, float] = {}
    for term, freq in df.items():
        idf[term] = math.log((N + 1) / (freq + 1)) + 1.0
    return idf

def _tfidf_vector(text: str, idf: Dict[str, float]) -> Dict[str, float]:
    """Return TF‑IDF vector (sparse dict) for a single document."""
    tokens = _tokenize(text)
    tf_counts = Counter(tokens)
    total = len(tokens) if tokens else 1
    vec: Dict[str, float] = {}
    for term, count in tf_counts.items():
        tf = count / total
        vec[term] = tf * idf.get(term, 0.0)
    return vec

def _cosine_similarity(vec_a: Dict[str, float], vec_b: Dict[str, float]) -> float:
    """Cosine similarity between two sparse vectors."""
    # dot product
    dot = sum(vec_a.get(k, 0.0) * vec_b.get(k, 0.0) for k in vec_a)
    norm_a = math.sqrt(sum(v * v for v in vec_a.values()))
    norm_b = math.sqrt(sum(v * v for v in vec_b.values()))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


from ..database import get_db
from ..models import Conversation, Message, DocumentChunk
from ..hf_model import generate_answer

router = APIRouter(prefix="/rag", tags=["rag"])

class RagRequest(BaseModel):
    conversation_id: int
    message: str
    top_k: int = Field(default=3, ge=1, le=10)

@router.post("/")
def rag_chat(request: RagRequest, db: Session = Depends(get_db)):
    # Verify conversation exists
    conv = db.query(Conversation).filter(Conversation.id == request.conversation_id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Save user message first
    user_msg = Message(conversation_id=request.conversation_id, role="user", content=request.message)
    db.add(user_msg)
    db.flush()

    # Retrieve all document chunks
    chunks = db.query(DocumentChunk).all()
    if not chunks:
        # No documents, fallback to normal chat (could call existing /chat, but here just error)
        raise HTTPException(status_code=400, detail="No documents available for RAG")

    # Prepare corpus for TF-IDF
    corpus = [c.chunk_text for c in chunks]
    # Compute IDF across all chunks
    idf = _compute_idf(corpus)
    # Vector for the query
    query_vec = _tfidf_vector(request.message, idf)
    # Vectors for each chunk
    chunk_vectors = [_tfidf_vector(txt, idf) for txt in corpus]
    # Cosine similarities
    sims = [_cosine_similarity(query_vec, vec) for vec in chunk_vectors]
    # Get top_k indices sorted by similarity descending
    top_k = min(request.top_k, len(sims))
    top_indices = sorted(range(len(sims)), key=lambda i: sims[i], reverse=True)[:top_k]
    max_score = sims[top_indices[0]] if top_k > 0 else 0.0
    if max_score == 0.0:
        # No relevant info
        answer_text = "I don't have enough information in the uploaded documents to answer that."
        # Save assistant message
        assistant_msg = Message(conversation_id=request.conversation_id, role="assistant", content=answer_text)
        db.add(assistant_msg)
        db.commit()
        return {"answer": answer_text, "retrieved_chunks": []}

    retrieved_chunks = [chunks[i].chunk_text for i in top_indices]
    # Build prompt
    context = "\n---\n".join(retrieved_chunks)
    prompt = f"You are answering based on the following extracted document excerpts:\n{context}\n\nUser question: {request.message}\nAnswer:" 
    # Call HF model
    try:
        answer = generate_answer(prompt)
    except Exception as e:
        # Rollback user message but keep it saved as per requirement? keep user msg, return 502
        db.rollback()
        raise HTTPException(status_code=502, detail=str(e))

    # Save assistant message
    assistant_msg = Message(conversation_id=request.conversation_id, role="assistant", content=answer)
    db.add(assistant_msg)
    db.commit()
    return {"answer": answer, "retrieved_chunks": retrieved_chunks}
