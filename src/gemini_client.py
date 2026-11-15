"""Talks to the Gemini API. No other file should call Gemini directly."""

import time

from google import genai
from google.genai import errors, types

from src.config import GEMINI_API_KEY, MODEL_NAME, validate_config

MAX_RETRIES = 2
RETRY_WAIT_SECONDS = 5


class GeminiAPIError(Exception):
    """Raised when Gemini cannot be reached or returns an error."""


def get_client():
    """Create a Gemini client using the key from config."""
    validate_config()
    return genai.Client(api_key=GEMINI_API_KEY)


def ask_gemini(prompt):
    """Send a text prompt to Gemini and return its text reply."""
    client = get_client()
    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt,
    )
    return response.text


def _friendly_message(code):
    """Turn an API error code into a message a user can understand."""
    if code == 429:
        return "Rate limit reached. Please wait a minute and try again."
    if code in (401, 403):
        return "Gemini rejected the API key. Check your .env file."
    if code == 404:
        return "Model not found. Check MODEL_NAME in src/config.py."
    if code in (500, 503):
        return "Gemini is busy right now. Please try again shortly."
    return f"Gemini returned an error (code {code})."


def ask_gemini_json(prompt):
    """Send a prompt and return Gemini's reply as raw JSON text.

    Retries a couple of times if Gemini is busy or rate-limited.
    """
    client = get_client()
    config = types.GenerateContentConfig(
        response_mime_type="application/json",  # ask for JSON only
        temperature=0.2,  # low = more stable, less creative answers
    )

    for attempt in range(MAX_RETRIES + 1):
        try:
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=prompt,
                config=config,
            )
            if not response.text:
                raise GeminiAPIError("Gemini returned an empty response.")
            return response.text

        except GeminiAPIError:
            raise

        except errors.APIError as error:
            code = getattr(error, "code", None)
            can_retry = code in (429, 500, 503)
            if can_retry and attempt < MAX_RETRIES:
                time.sleep(RETRY_WAIT_SECONDS * (attempt + 1))
                continue
            raise GeminiAPIError(_friendly_message(code)) from error

        except Exception as error:
            raise GeminiAPIError(
                "Could not reach Gemini. Check your internet connection."
            ) from error