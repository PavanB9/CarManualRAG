import os
from functools import lru_cache

import anthropic
from dotenv import load_dotenv

load_dotenv()


class LLMConfigError(Exception):
    """Raised when the Anthropic API key is missing or invalid."""


@lru_cache(maxsize=1)
def get_client() -> anthropic.Anthropic:
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key or api_key == "sk-ant-your-key-here":
        raise LLMConfigError(
            "ANTHROPIC_API_KEY is not set. Add your key to .env (see .env.example) "
            "and restart the backend. Get a key at https://console.anthropic.com"
        )
    return anthropic.Anthropic(api_key=api_key)


def translate_llm_error(exc: Exception) -> str:
    if isinstance(exc, LLMConfigError):
        return str(exc)
    if isinstance(exc, anthropic.AuthenticationError):
        return "Anthropic API key was rejected. Check ANTHROPIC_API_KEY in .env."
    if isinstance(exc, anthropic.RateLimitError):
        return "Anthropic API rate limit hit. Please wait a moment and try again."
    if isinstance(exc, anthropic.APIConnectionError):
        return "Could not reach the Anthropic API. Check your network connection."
    if isinstance(exc, anthropic.APIStatusError):
        return f"Anthropic API error ({exc.status_code}): {exc.message}"
    return f"Unexpected error calling the Anthropic API: {exc}"
