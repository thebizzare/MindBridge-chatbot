
from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import text

from .database import engine, get_db
from .models import Conversation, Message

app = FastAPI(
    title="MindBridge AI",
    description="Multimodal AI Chatbot with RAG",
    version="1.0"
)

# Include routers
from .routers import document, rag
app.include_router(document.router)
app.include_router(rag.router)

# Request format
class ConversationRequest(BaseModel):
    title: str
class MessageRequest(BaseModel):
    conversation_id: int
    role: str
    content: str

# Home route
@app.get("/")
def home():
    return {"message": "MindBridge AI is running!"}


# Health check
@app.get("/health")
def health():
    return {"status": "healthy"}


# MySQL connection check
@app.get("/db-health")
def database_health():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))

        return {
            "status": "success",
            "message": "MySQL connected successfully!"
        }

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Database connection failed"
        )


# Create a new conversation
@app.post("/conversations")
def create_conversation(
    request: ConversationRequest,
    db: Session = Depends(get_db)
):
    new_conversation = Conversation(
        title=request.title
    )

    db.add(new_conversation)
    db.commit()
    db.refresh(new_conversation)

    return {
        "message": "Conversation created successfully!",
        "conversation_id": new_conversation.id,
        "title": new_conversation.title
    }

@app.post("/messages")
def save_message(
    request: MessageRequest,
    db: Session = Depends(get_db)
):
    # Check whether conversation exists
    conversation = db.query(Conversation).filter(
        Conversation.id == request.conversation_id
    ).first()

    if not conversation:
        raise HTTPException(
            status_code=404,
            detail="Conversation not found"
        )

    # Create a new message
    new_message = Message(
        conversation_id=request.conversation_id,
        role=request.role,
        content=request.content
    )

    db.add(new_message)
    db.commit()
    db.refresh(new_message)

    return {
        "message": "Chat message saved successfully!",
        "message_id": new_message.id,
        "conversation_id": new_message.conversation_id,
        "role": new_message.role,
        "content": new_message.content
    }

@app.get("/conversations/{conversation_id}/messages")
def get_messages(
    conversation_id: int,
    db: Session = Depends(get_db)
):
    # Check whether conversation exists
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id
    ).first()

    if not conversation:
        raise HTTPException(
            status_code=404,
            detail="Conversation not found"
        )

    # Get all messages of this conversation
    messages = db.query(Message).filter(
        Message.conversation_id == conversation_id
    ).order_by(Message.id.asc()).all()

    return {
        "conversation_id": conversation_id,
        "total_messages": len(messages),
        "messages": [
            {
                "message_id": msg.id,
                "role": msg.role,
                "content": msg.content
            }
            for msg in messages
        ]
    }
