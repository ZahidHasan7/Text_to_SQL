"""
utils_gemini_rest.py
====================
Backward-compatible wrapper for the unified LLM layer (utils_llm.py).

Previously: Direct Gemini REST API caller with its own session, cache, and retry logic.
Now:        Thin wrapper that delegates all calls to utils_llm.generate_text(),
            which supports Gemini, OpenAI, and OpenRouter providers.

The gemini_generate_text() function signature is preserved so that existing
runner scripts (03_run_cot.py, 03_run_qdecomp.py, 03_run_qd_intercol.py)
continue to work without any import changes.

Provider & model selection is controlled by environment variables:
  - OPENROUTER_API_KEY + OPENROUTER_MODEL  (recommended — single key, any model)
  - GEMINI_API_KEY                          (legacy direct Gemini)
  - OPENAI_API_KEY                          (legacy direct OpenAI)
See .env.example for details.
"""

import os
from typing import List, Optional, Tuple, Union

from utils_llm import generate_text

# Re-export DEBUG for any code that reads it
DEBUG = os.getenv("GEMINI_DEBUG", "0") == "1"


def gemini_generate_text(
    prompt: str,
    models: Optional[List[str]] = None,
    timeout: int = 60,
    temperature: float = 0.0,
    max_output_tokens: int = 2048,
    max_retries: int = 5,
    sleep_between_models: float = 0.4,
    return_model: bool = False,
) -> Union[str, Tuple[str, str]]:
    """
    Backward-compatible wrapper around utils_llm.generate_text().

    All parameters are forwarded to the unified LLM layer. The active provider
    and model are determined by environment variables (see .env.example).

    Args:
        prompt: Input text to send to the LLM.
        models: Optional model list override (ignored when using OpenRouter;
                model is set via OPENROUTER_MODEL env var instead).
        timeout: Per-request timeout in seconds.
        temperature: Sampling temperature.
        max_output_tokens: Max output token limit.
        max_retries: Retry attempts per model before failing.
        sleep_between_models: (Legacy param, no longer used — retained for
                              signature compatibility.)
        return_model: If True, return (text, model_name) tuple.

    Returns:
        str or (str, model_name) depending on return_model.
    """
    return generate_text(
        prompt=prompt,
        models=models,
        timeout=timeout,
        temperature=temperature,
        max_output_tokens=max_output_tokens,
        max_retries=max_retries,
        return_model=return_model,
    )
