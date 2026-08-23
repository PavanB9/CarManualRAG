import os
from dataclasses import dataclass
from functools import lru_cache

import anthropic
import openai
from dotenv import load_dotenv

load_dotenv()


class LLMConfigError(Exception):
    """Raised when the active provider's API key is missing or invalid."""


@dataclass
class GenerationResult:
    text: str
    input_tokens: int
    output_tokens: int
    provider: str
    model: str


def get_provider() -> str:
    return os.environ.get("LLM_PROVIDER", "openai").strip().lower()


def get_model_id(provider: str | None = None) -> str:
    provider = provider or get_provider()
    if provider == "openai":
        return os.environ.get("OPENAI_MODEL", "gpt-5.6-luna")
    if provider == "anthropic":
        return os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-5")
    raise LLMConfigError(f"Unknown LLM_PROVIDER: {provider!r} (expected 'openai' or 'anthropic')")


@lru_cache(maxsize=1)
def _openai_client() -> openai.OpenAI:
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key or api_key.startswith("sk-...") or "your-key" in api_key:
        raise LLMConfigError(
            "OPENAI_API_KEY is not set. Add your key to .env (see .env.example) "
            "and restart the backend. Get a key at https://platform.openai.com/api-keys"
        )
    return openai.OpenAI(api_key=api_key)


@lru_cache(maxsize=1)
def _anthropic_client() -> anthropic.Anthropic:
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key or api_key.startswith("sk-ant-your") or "your-key" in api_key:
        raise LLMConfigError(
            "ANTHROPIC_API_KEY is not set. Add your key to .env (see .env.example) "
            "and restart the backend. Get a key at https://console.anthropic.com"
        )
    return anthropic.Anthropic(api_key=api_key)


def _generate_openai(system: str, user_prompt: str, max_tokens: int) -> GenerationResult:
    client = _openai_client()
    model = get_model_id("openai")
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user_prompt},
        ],
        max_completion_tokens=max_tokens,
        reasoning_effort="medium",
    )
    choice = response.choices[0]
    text = choice.message.content or ""
    usage = response.usage
    return GenerationResult(
        text=text,
        input_tokens=usage.prompt_tokens if usage else 0,
        output_tokens=usage.completion_tokens if usage else 0,
        provider="openai",
        model=model,
    )


def _generate_anthropic(system: str, user_prompt: str, max_tokens: int) -> GenerationResult:
    client = _anthropic_client()
    model = get_model_id("anthropic")
    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user_prompt}],
    )
    text = "".join(block.text for block in response.content if block.type == "text")
    return GenerationResult(
        text=text,
        input_tokens=response.usage.input_tokens,
        output_tokens=response.usage.output_tokens,
        provider="anthropic",
        model=model,
    )


def generate(system: str, user_prompt: str, max_tokens: int) -> GenerationResult:
    provider = get_provider()
    if provider == "openai":
        return _generate_openai(system, user_prompt, max_tokens)
    if provider == "anthropic":
        return _generate_anthropic(system, user_prompt, max_tokens)
    raise LLMConfigError(f"Unknown LLM_PROVIDER: {provider!r} (expected 'openai' or 'anthropic')")


def translate_llm_error(exc: Exception) -> str:
    if isinstance(exc, LLMConfigError):
        return str(exc)
    if isinstance(exc, (anthropic.AuthenticationError, openai.AuthenticationError)):
        return "API key was rejected by the provider. Check your key in .env."
    if isinstance(exc, (anthropic.RateLimitError, openai.RateLimitError)):
        return "Provider rate limit hit. Please wait a moment and try again."
    if isinstance(exc, (anthropic.APIConnectionError, openai.APIConnectionError)):
        return "Could not reach the LLM provider API. Check your network connection."
    if isinstance(exc, anthropic.APIStatusError):
        return f"Anthropic API error ({exc.status_code}): {exc.message}"
    if isinstance(exc, openai.APIStatusError):
        return f"OpenAI API error ({exc.status_code}): {exc.message}"
    return f"Unexpected error calling the LLM provider: {exc}"
