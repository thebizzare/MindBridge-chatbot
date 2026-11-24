# --------------------------------------------------------------
# frontend/app.py  (new version)
# --------------------------------------------------------------
import streamlit as st
import requests
import json

# ------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------
API_URL = "http://127.0.0.1:8000"

st.set_page_config(
    page_title="MindBridge AI",
    page_icon="🧠",
    layout="centered",
)

st.title("🧠 MindBridge AI")
st.caption("Your Multimodal AI Companion")

# ------------------------------------------------------------------
# Helper functions (pure Python, no extra dependencies)
# ------------------------------------------------------------------
def create_conversation() -> int:
    """Ask the backend to create a new conversation and return its ID."""
    try:
        resp = requests.post(f"{API_URL}/conversations", json={"title": "Streamlit Session"})
        resp.raise_for_status()
        return resp.json()["conversation_id"]
    except requests.RequestException:
        st.error("❗ Unable to start a new conversation. Please check the backend.")
        st.stop()

def fetch_history(conv_id: int):
    """Pull previous messages for this conversation and store them in session_state."""
    try:
        resp = requests.get(f"{API_URL}/conversations/{conv_id}/messages")
        resp.raise_for_status()
        data = resp.json()
        msgs = [
            {"role": msg["role"], "content": msg["content"]}
            for msg in data.get("messages", [])
        ]
        st.session_state.messages = msgs
    except requests.RequestException:
        st.error("❗ Could not load chat history.")
        st.session_state.messages = []

def send_message(conv_id: int, user_text: str) -> str:
    """Send user text to /chat and return the assistant's answer."""
    payload = {"conversation_id": conv_id, "message": user_text}
    try:
        resp = requests.post(f"{API_URL}/chat", json=payload, timeout=30)
        resp.raise_for_status()
        return resp.json()["answer"]
    except requests.RequestException:
        st.error("❗ The AI service is unavailable right now. Please try again later.")
        return None

# ------------------------------------------------------------------
# Session‑state initialisation
# ------------------------------------------------------------------
if "conversation_id" not in st.session_state:
    # First page load – start a new conversation
    st.session_state.conversation_id = create_conversation()
    st.session_state.messages = []

# Load historic messages only once per session (or after a reset)
if not st.session_state.get("_history_loaded", False):
    fetch_history(st.session_state.conversation_id)
    st.session_state["_history_loaded"] = True

# ------------------------------------------------------------------
# UI – display chat history (no duplicates)
# ------------------------------------------------------------------
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# ------------------------------------------------------------------
# UI – button to start a fresh conversation
# ------------------------------------------------------------------
if st.button("🔄 New conversation"):
    for key in ["conversation_id", "messages", "_history_loaded"]:
        if key in st.session_state:
            del st.session_state[key]
    st.rerun()

# ------------------------------------------------------------------
# UI – user input handling
# ------------------------------------------------------------------
user_input = st.chat_input("Talk to MindBridge AI...")

if user_input:
    # Show user's message immediately
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.write(user_input)

    # Send to backend with spinner
    with st.spinner("MindBridge AI is thinking..."):
        answer = send_message(st.session_state.conversation_id, user_input)

    if answer is not None:
        st.session_state.messages.append({"role": "assistant", "content": answer})
        with st.chat_message("assistant"):
            st.write(answer)
    else:
        # error already shown via st.error(); keep user message in UI
        pass
