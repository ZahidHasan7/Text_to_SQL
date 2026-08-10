import os
import time
import random
import hashlib
import threading
from typing import List, Optional, Tuple, Union
import requests
from dotenv import load_dotenv

load_dotenv()

# --- Configurations ---
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini").lower()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

GEMINI_BASE = os.getenv("GEMINI_BASE", "https://generativelanguage.googleapis.com/v1beta")
OPENAI_BASE = os.getenv("OPENAI_BASE", "https://api.openai.com/v1")

DEFAULT_GEMINI_MODELS = ["models/gemini-3.5-flash"]
DEFAULT_OPENAI_MODELS = ["gpt-4o-mini"]

DEBUG = os.getenv("LLM_DEBUG", "0") == "1"

# --- Session & Cache ---
_session_lock = threading.Lock()
_session: Optional[requests.Session] = None

def _get_session() -> requests.Session:
    global _session
    if _session is None:
        with _session_lock:
            if _session is None:
                s = requests.Session()
                adapter = requests.adapters.HTTPAdapter(pool_connections=8, pool_maxsize=16, max_retries=0)
                s.mount("http://", adapter)
                s.mount("https://", adapter)
                _session = s
    return _session

_CACHE_MAX = 256
_cache = {}
_cache_order = []

def _cache_key(prompt: str, temperature: float, max_tokens: int, provider: str, models: List[str]) -> str:
    h = hashlib.sha256()
    h.update(prompt.encode("utf-8", errors="ignore"))
    h.update(str(float(temperature)).encode("ascii"))
    h.update(str(int(max_tokens)).encode("ascii"))
    h.update(provider.encode("ascii"))
    h.update("|".join(models).encode("utf-8"))
    return h.hexdigest()

def _cache_get(key: str):
    return _cache.get(key)

def _cache_put(key: str, value):
    if key in _cache: return
    _cache[key] = value
    _cache_order.append(key)
    if len(_cache_order) > _CACHE_MAX:
        old = _cache_order.pop(0)
        _cache.pop(old, None)

# --- Implementations ---

def _extract_gemini_text(resp_json: dict) -> str:
    try:
        cands = resp_json.get("candidates") or []
        if not cands: return str(resp_json)
        parts = cands[0].get("content", {}).get("parts") or []
        if parts and "text" in parts[0]: return parts[0]["text"]
        texts = [p.get("text", "") for p in parts if isinstance(p, dict)]
        if any(texts): return "\n".join(texts)
        return str(resp_json)
    except Exception:
        return str(resp_json)

def _call_gemini(prompt: str, models: List[str], timeout: int, temperature: float, max_tokens: int, max_retries: int) -> Tuple[str, str]:
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY missing in .env")
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": float(temperature), "maxOutputTokens": int(max_tokens)},
    }
    last_err = None
    for m in models:
        url = f"{GEMINI_BASE}/{m}:generateContent?key={GEMINI_API_KEY}"
        for attempt in range(max_retries):
            if DEBUG: print(f"[gemini] {m} attempt {attempt+1}")
            try:
                r = _get_session().post(url, json=payload, timeout=timeout)
                r.raise_for_status()
                text = _extract_gemini_text(r.json())
                return text, m
            except requests.HTTPError as e:
                last_err = e
                status = e.response.status_code if e.response is not None else None
                if status in (429, 503) and attempt < max_retries - 1:
                    time.sleep((2 ** attempt) + random.uniform(0, 0.35))
                    continue
                break
            except Exception as e:
                last_err = e
                time.sleep(0.3)
                break
        time.sleep(0.4)
    raise RuntimeError(f"All Gemini models failed. Last error: {last_err}")

def _call_openai(prompt: str, models: List[str], timeout: int, temperature: float, max_tokens: int, max_retries: int) -> Tuple[str, str]:
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY missing in .env")
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
    last_err = None
    for m in models:
        url = f"{OPENAI_BASE}/chat/completions"
        payload = {
            "model": m,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": float(temperature),
            "max_tokens": int(max_tokens),
        }
        for attempt in range(max_retries):
            if DEBUG: print(f"[openai] {m} attempt {attempt+1}")
            try:
                r = _get_session().post(url, json=payload, headers=headers, timeout=timeout)
                r.raise_for_status()
                data = r.json()
                choices = data.get("choices") or []
                text = choices[0].get("message", {}).get("content", "").strip() if choices else str(data)
                return text, m
            except requests.HTTPError as e:
                last_err = e
                status = e.response.status_code if e.response is not None else None
                if status in (429, 500, 503) and attempt < max_retries - 1:
                    time.sleep((2 ** attempt) + random.uniform(0, 0.4))
                    continue
                break
            except Exception as e:
                last_err = e
                time.sleep(0.25)
                break
        time.sleep(0.3)
    raise RuntimeError(f"All OpenAI models failed. Last error: {last_err}")

# --- Unified API ---

def generate_text(
    prompt: str,
    provider: Optional[str] = None,
    models: Optional[List[str]] = None,
    timeout: int = 60,
    temperature: float = 0.0,
    max_output_tokens: int = 2048,
    max_retries: int = 5,
    return_model: bool = False,
) -> Union[str, Tuple[str, str]]:
    
    provider = (provider or LLM_PROVIDER).lower()
    if provider == "gemini":
        use_models = models or DEFAULT_GEMINI_MODELS
    elif provider == "openai":
        use_models = models or DEFAULT_OPENAI_MODELS
    else:
        raise ValueError(f"Unknown LLM provider: {provider}")

    ck = _cache_key(prompt, temperature, max_output_tokens, provider, use_models)
    cached = _cache_get(ck)
    if cached is not None:
        text, used_model = cached
        if DEBUG: print(f"[{provider}:cache] hit -> {used_model}")
        return (text, used_model) if return_model else text

    if provider == "gemini":
        text, used_model = _call_gemini(prompt, use_models, timeout, temperature, max_output_tokens, max_retries)
    else:
        text, used_model = _call_openai(prompt, use_models, timeout, temperature, max_output_tokens, max_retries)

    _cache_put(ck, (text, used_model))
    return (text, used_model) if return_model else text
