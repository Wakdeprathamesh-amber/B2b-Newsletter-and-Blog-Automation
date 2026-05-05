"""Model-agnostic LLM client with rate limiting, retry logic, and timeout handling.

Provides a single `complete()` async function that routes to OpenAI or Anthropic
based on the LLM_PROVIDER setting.  All pipeline nodes call this instead of
importing a vendor SDK directly.

Features:
- Automatic retry with exponential backoff (3 attempts)
- Rate limiting (max 10 concurrent requests)
- Timeout handling (120s default)
- Token usage tracking
- Error context logging

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

import asyncio
import json
import re
from datetime import datetime

import structlog
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)

from src.settings import settings

log = structlog.get_logger()

# Global rate limiter: max 10 concurrent LLM requests
_rate_limiter = asyncio.Semaphore(10)

# Metrics tracking
_metrics = {
    "total_calls": 0,
    "total_tokens": 0,
    "total_errors": 0,
    "total_retries": 0,
}


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
    timeout: float = 120.0,
):
    """Call the LLM and parse its response as JSON.

    Handles code-fence wrapping, prose around JSON, and both object/array outputs.
    Use this instead of complete() whenever the prompt expects JSON.
    
    Args:
        timeout: Request timeout in seconds (default: 120s)
    """
    text = await complete(
        role=role,
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
        timeout=timeout,
    )
    return extract_json(text)


async def complete(
    *,
    role: str = "generation",
    messages: list[dict[str, str]],
    max_tokens: int = 4000,
    temperature: float | None = None,
    timeout: float = 120.0,
    context: dict | None = None,
) -> str:
    """Send a chat-completion request to the configured LLM provider.

    Features:
    - Automatic retry with exponential backoff (3 attempts)
    - Rate limiting (max 10 concurrent requests)
    - Timeout handling
    - Token usage tracking
    - Error context logging

    Args:
        role: Which model tier to use — "generation" (fast/cheap) or
              "editorial" (capable/expensive).  Maps to settings.generation_model
              or settings.editorial_model.
        messages: OpenAI-style message list, e.g.
                  [{"role": "user", "content": "..."}].
        max_tokens: Maximum tokens in the response.
        temperature: Optional sampling temperature override.
        timeout: Request timeout in seconds (default: 120s).
        context: Optional context dict for error logging (e.g., {"topic_id": "TOP-01"})

    Returns:
        The assistant's reply as a plain string.

    Raises:
        RuntimeError: If no API key is configured for the active provider.
        asyncio.TimeoutError: If request exceeds timeout.
        Exception: Propagates provider SDK errors after retries exhausted.
    """
    provider = settings.llm_provider
    model = settings.generation_model if role == "generation" else settings.editorial_model

    # Apply rate limiting
    async with _rate_limiter:
        if provider == "openai":
            return await _complete_openai_with_retry(
                model, messages, max_tokens, temperature, timeout, context
            )
        elif provider == "anthropic":
            return await _complete_anthropic_with_retry(
                model, messages, max_tokens, temperature, timeout, context
            )
        else:
            raise ValueError(f"Unsupported LLM_PROVIDER: {provider!r}. Use 'openai' or 'anthropic'.")


def get_metrics() -> dict:
    """Get LLM usage metrics."""
    return _metrics.copy()


# ── OpenAI with Retry Logic ────────────────────────────────────────────────

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=4, max=60),
    retry=retry_if_exception_type((Exception,)),  # Retry on any exception
    before_sleep=before_sleep_log(log, "warning"),
    reraise=True,
)
async def _complete_openai_with_retry(
    model: str,
    messages: list[dict[str, str]],
    max_tokens: int,
    temperature: float | None,
    timeout: float,
    context: dict | None,
) -> str:
    """OpenAI completion with retry logic and timeout."""
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is not set but LLM_PROVIDER=openai")

    from openai import AsyncOpenAI, RateLimitError, APITimeoutError

    client = AsyncOpenAI(api_key=settings.openai_api_key, timeout=timeout)

    kwargs: dict = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
    }
    if temperature is not None:
        kwargs["temperature"] = temperature

    start_time = datetime.utcnow()
    
    try:
        # Apply timeout wrapper
        response = await asyncio.wait_for(
            client.chat.completions.create(**kwargs),
            timeout=timeout
        )
        
        # Track metrics
        _metrics["total_calls"] += 1
        if hasattr(response, "usage") and response.usage:
            tokens = response.usage.total_tokens
            _metrics["total_tokens"] += tokens
            
            duration = (datetime.utcnow() - start_time).total_seconds()
            log.info(
                "llm_call_success",
                model=model,
                tokens=tokens,
                duration_sec=duration,
                context=context or {},
            )
        
        return response.choices[0].message.content

    except asyncio.TimeoutError:
        _metrics["total_errors"] += 1
        log.error(
            "llm_timeout",
            model=model,
            timeout=timeout,
            context=context or {},
        )
        raise RuntimeError(f"LLM request timed out after {timeout}s")
    
    except (RateLimitError, APITimeoutError) as e:
        _metrics["total_retries"] += 1
        log.warning(
            "llm_rate_limit",
            model=model,
            error=str(e),
            context=context or {},
        )
        raise  # Will be retried by tenacity
    
    except Exception as e:
        _metrics["total_errors"] += 1
        log.error(
            "llm_error",
            model=model,
            error=str(e),
            context=context or {},
        )
        raise


# ── Legacy OpenAI (for backward compatibility) ──────────────────────────────

async def _complete_openai(
    model: str,
    messages: list[dict[str, str]],
    max_tokens: int,
    temperature: float | None,
) -> str:
    """Legacy OpenAI completion without retry (deprecated)."""
    return await _complete_openai_with_retry(
        model, messages, max_tokens, temperature, 120.0, None
    )


# ── Anthropic with Retry Logic ─────────────────────────────────────────────

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=4, max=60),
    retry=retry_if_exception_type((Exception,)),
    before_sleep=before_sleep_log(log, "warning"),
    reraise=True,
)
async def _complete_anthropic_with_retry(
    model: str,
    messages: list[dict[str, str]],
    max_tokens: int,
    temperature: float | None,
    timeout: float,
    context: dict | None,
) -> str:
    """Anthropic completion with retry logic and timeout."""
    if not settings.anthropic_api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is not set but LLM_PROVIDER=anthropic")

    import anthropic

    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key, timeout=timeout)

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

    start_time = datetime.utcnow()
    
    try:
        response = await asyncio.wait_for(
            client.messages.create(**kwargs),
            timeout=timeout
        )
        
        # Track metrics
        _metrics["total_calls"] += 1
        if hasattr(response, "usage") and response.usage:
            tokens = response.usage.input_tokens + response.usage.output_tokens
            _metrics["total_tokens"] += tokens
            
            duration = (datetime.utcnow() - start_time).total_seconds()
            log.info(
                "llm_call_success",
                model=model,
                tokens=tokens,
                duration_sec=duration,
                context=context or {},
            )
        
        return response.content[0].text

    except asyncio.TimeoutError:
        _metrics["total_errors"] += 1
        log.error(
            "llm_timeout",
            model=model,
            timeout=timeout,
            context=context or {},
        )
        raise RuntimeError(f"LLM request timed out after {timeout}s")
    
    except Exception as e:
        _metrics["total_errors"] += 1
        log.error(
            "llm_error",
            model=model,
            error=str(e),
            context=context or {},
        )
        raise


# ── Legacy Anthropic (for backward compatibility) ───────────────────────────

async def _complete_anthropic(
    model: str,
    messages: list[dict[str, str]],
    max_tokens: int,
    temperature: float | None,
) -> str:
    """Legacy Anthropic completion without retry (deprecated)."""
    return await _complete_anthropic_with_retry(
        model, messages, max_tokens, temperature, 120.0, None
    )
