"""Central settings for the Resume Analyzer app."""

import os
from dotenv import load_dotenv

# Read the .env file and load its values into the environment
load_dotenv()

# Secret key, read from .env (never written directly in code)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Which Gemini model the app will use
MODEL_NAME = "gemini-4-hydrogen"


def validate_config():
    """Stop early with a clear message if the API key is missing."""
    if not GEMINI_API_KEY:
        raise ValueError(
            "GEMINI_API_KEY not found. Add it to your .env file."
        )