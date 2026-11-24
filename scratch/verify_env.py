import os
from pathlib import Path
from dotenv import load_dotenv

# Resolve path two levels up from this file (backend/hf_model.py location)
hf_model_path = Path(r'C:\Users\HP\OneDrive\Documents\chatbot\backend\hf_model.py')
env_path = hf_model_path.resolve().parents[2] / '.env'
print('Resolved env_path:', env_path)
print('Exists:', env_path.is_file())

# Load and check HF_TOKEN presence
load_dotenv(dotenv_path=env_path)
print('HF_TOKEN present?', bool(os.getenv('HF_TOKEN')))
