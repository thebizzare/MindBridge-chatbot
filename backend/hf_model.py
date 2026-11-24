# backend/hf_model.py
import os
from pathlib import Path
from dotenv import load_dotenv

from huggingface_hub import InferenceClient
from huggingface_hub.errors import HfHubHTTPError, InferenceTimeoutError

# ----------------------------------------------------------------------
# Load the root .env file explicitly
# ----------------------------------------------------------------------
# The project root is two levels up from this file: backend/../ -> chatbot
env_path = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(dotenv_path=env_path)

# ----------------------------------------------------------------------
# Environment variable (must be present)
# ----------------------------------------------------------------------
HF_TOKEN = os.getenv("HF_TOKEN")
if not HF_TOKEN:
    raise RuntimeError(
        "HF_TOKEN not found in .env. Please add it to the root .env file."
    )

# ----------------------------------------------------------------------
# Model constant – can be changed in one place
# ----------------------------------------------------------------------
MODEL_ID = "Qwen 2.5 1.5B Instruct"

# ----------------------------------------------------------------------
# Singleton InferenceClient (synchronous)
# ----------------------------------------------------------------------
client = InferenceClient(
    provider="featherless-ai",
    token=HF_TOKEN
)


def generate_answer(prompt: str) -> str:
    """
    Synchronous call to Hugging Face chat completion.
    Returns the assistant's generated text.
    Raises RuntimeError on any inference‑related failure.
    """
    try:
        response = client.chat_completion(
            model=MODEL_ID,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=256,
        )
        # Expected: response.choices[0].message.content
        return response.choices[0].message.content.strip()
    except (HfHubHTTPError, InferenceTimeoutError) as exc:
        raise RuntimeError(f"Hugging Face inference error: {exc}") from exc
    except Exception as exc:
        raise RuntimeError(f"Unexpected inference error: {exc}") from exc
