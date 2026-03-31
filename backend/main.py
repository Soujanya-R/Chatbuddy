from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from database import SessionLocal, engine
from models import Base, Message
from pydantic import BaseModel
import os
import requests

app = FastAPI()

# Create DB tables
Base.metadata.create_all(bind=engine)

# DB dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Hugging Face API setup
HF_API_URL = "https://api-inference.huggingface.co/models/gpt2"  # or another free model
HF_API_KEY = os.getenv("HUGGINGFACE_API_KEY")
headers = {"Authorization": f"Bearer {HF_API_KEY}"}

def get_hf_response(prompt: str):
    payload = {"inputs": prompt}
    response = requests.post(HF_API_URL, headers=headers, json=payload)
    data = response.json()
    # Hugging Face returns a list of dicts with 'generated_text'
    if isinstance(data, list) and "generated_text" in data[0]:
        return data[0]["generated_text"]
    return "Sorry, I couldn't generate a response."

# Pydantic model
class ChatRequest(BaseModel):
    message: str

# Chat endpoint
@app.post("/chat")
def chat(req: ChatRequest, db: Session = Depends(get_db)):
    # Save user message
    new_msg = Message(role="user", content=req.message)
    db.add(new_msg)
    db.commit()
    db.refresh(new_msg)

    # Get reply from HF model
    reply_text = get_hf_response(f"You are a friendly AI buddy. Reply to this: {req.message}")

    # Save assistant reply
    db.add(Message(role="assistant", content=reply_text))
    db.commit()

    return {"reply": reply_text}

# Health check
@app.get("/")
def root():
    return {"message": "ChatBuddy backend is alive!"}
