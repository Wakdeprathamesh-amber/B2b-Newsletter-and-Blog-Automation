"""Model-agnostic LLM client.

Provides a single `complete()` async function that routes to OpenAI or Anthropic
based on the LLM_PROVIDER setting.  All pipeline nodes call this instead of
importing a vendor SDK directly.

Usage:
    from src.llm import complete, complete_json

    text = await complete(
        role="generation",
        messages=[{"role": "user", "content": "Hello"}],
        max_tokens=1000,
    )

    # For prompts that expect a JSON response:
    data = await complete_json(
        role="editorial",
        messages=[{"role": "user", "content": "Return a JSON array..."}],
        max_tokens=4000,
    )
"""

from __future__ import annotations

import json
import re

import structlog

from src.settings import settings

log = structlog.get_logger()


_FENCE_RE = re.compile(r"^```(?:json)?\s*\n?|\n?```\s*$", re.IGNORECASE)


def extract_json(text: str):
    """Parse a JSON object/array from an LLM response, tolerant of:
       - leading/trailing whitespace
       - markdown code fences (```json ... ``` or ``` ... ```)
       - extra prose before/after the JSON body

    Raises json.JSONDecodeError if nothing parses.
    """
    if not text:
        raise json.JSONDecodeError("empty response", "", 0)

    stripped = text.strip()

    # Strip outer fenced code block if present
    if stripped.startswith("```"):
        stripped = _FENCE_RE.sub("", stripped).strip()
        # Remove any residual trailing fence
        if stripped.endswith("```"):
            stripped = stripped[:-3].strip()

    # Fast path — whole string is JSON
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        pass

    # Fallback: find the first {...} or [...] block and parse that
    for opener, closer in (("{", "}"), ("[", "]")):
        start = stripped.find(opener)
        end = stripped.rfind(closer)
        if start != -1 and end != -1 and end > start:
            candidate = stripped[start : end + 1]
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                continue

    raise json.JSONDecodeError(
        f"no parseable JSON in response ({len(text)} chars)", text[:200], 0
    )


async def complete_json(
    *,
    role: str = "generation",
    messages: list[dict[str, str]],
    max_tokens: int = 4000,
    temperature: float | None = None,
):
    """Call the LLM and parse its response as JSON.

    Handles code-fence wrapping, prose around JSON, and both object/array outputs.
    Use this instead of complete() whenever the prompt expects JSON.
    """
    text = await complete(
        role=role,
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    return extract_json(text)


async def complete(
    *,
    role: str = "generation",
    messages: list[dict[str, str]],
    max_tokens: int = 4000,
    temperature: float | None = None,
) -> str:
    """Send a chat-completion request to the configured LLM provider.

    Args:
        role: Which model tier to use — "generation" (fast/cheap) or
              "editorial" (capable/expensive).  Maps to settings.generation_model
              or settings.editorial_model.
        messages: OpenAI-style message list, e.g.
                  [{"role": "user", "content": "..."}].
        max_tokens: Maximum tokens in the response.
        temperature: Optional sampling temperature override.

    Returns:
        The assistant's reply as a plain string.

    Raises:
        RuntimeError: If no API key is configured for the active provider.
        Exception: Propagates provider SDK errors (caller should handle).
    """
    provider = settings.llm_provider
    model = settings.generation_model if role == "generation" else settings.editorial_model

    if provider == "openai":
        return await _complete_openai(model, messages, max_tokens, temperature)
    elif provider == "anthropic":
        return await _complete_anthropic(model, messages, max_tokens, temperature)
    else:
        raise ValueError(f"Unsupported LLM_PROVIDER: {provider!r}. Use 'openai' or 'anthropic'.")


# ── OpenAI ──────────────────────────────────────────────────────────────────

async def _complete_openai(
    model: str,
    messages: list[dict[str, str]],
    max_tokens: int,
    temperature: float | None,
) -> str:
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is not set but LLM_PROVIDER=openai")

    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=settings.openai_api_key)

    kwargs: dict = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
    }
    if temperature is not None:
        kwargs["temperature"] = temperature

    response = await client.chat.completions.create(**kwargs)
    return response.choices[0].message.content


# ── Anthropic ───────────────────────────────────────────────────────────────

async def _complete_anthropic(
    model: str,
    messages: list[dict[str, str]],
    max_tokens: int,
    temperature: float | None,
) -> str:
    if not settings.anthropic_api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is not set but LLM_PROVIDER=anthropic")

    import anthropic

    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    # Anthropic uses a separate `system` param — extract if present.
    system_msg = None
    chat_messages = []
    for msg in messages:
        if msg["role"] == "system":
            system_msg = msg["content"]
        else:
            chat_messages.append(msg)

    kwargs: dict = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": chat_messages,
    }
    if system_msg:
        kwargs["system"] = system_msg
    if temperature is not None:
        kwargs["temperature"] = temperature

    response = await client.messages.create(**kwargs)
    return response.content[0].text
