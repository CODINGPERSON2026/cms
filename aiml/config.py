import os
from dotenv import load_dotenv

# Locate project root directory containing .env
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ENV_PATH = os.path.join(BASE_DIR, ".env")

if os.path.exists(ENV_PATH):
    load_dotenv(ENV_PATH, override=True)
else:
    load_dotenv(override=True)

MODEL_NAME = os.getenv("MODEL_NAME", "qwen2.5:7b")
