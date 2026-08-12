# utils_openai_rest.py
# Lightweight OpenAI chat completion helper modeled after utils_gemini_rest.py
import os, time, random, hashlib, threading
from typing import Optional, Tuple, Union, List
import requests
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_BASE = os.getenv("OPENAI_BASE", "https://api.openai.com/v1")
DEFAULT_MODEL_ORDER: List[str] = [os.getenv("OPENAI_MODEL", "gpt-4o-mini")]  # single active model
DEBUG = os.getenv("OPENAI_DEBUG", "0") == "1"

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

def _post_json(url: str, payload: dict, timeout: int) -> dict:
    sess = _get_session()
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }
    r = sess.post(url, json=payload, headers=headers, timeout=timeout)
    r.raise_for_status()
    return r.json()

# ---------------- Cache -----------------
_CACHE_MAX = int(os.getenv("OPENAI_CACHE_MAX", "256"))
_cache: dict[str, Tuple[str, str]] = {}
_cache_order: List[str] = []

def _cache_key(prompt: str, temperature: float, max_output_tokens: int, try_order: List[str]) -> str:
    h = hashlib.sha256()
    h.update(prompt.encode("utf-8", errors="ignore"))
    h.update(str(float(temperature)).encode("ascii"))
    h.update(str(int(max_output_tokens)).encode("ascii"))
    h.update("|".join(try_order).encode("utf-8"))
    return h.hexdigest()

def _cache_get(key: str) -> Optional[Tuple[str, str]]:
    return _cache.get(key)

def _cache_put(key: str, value: Tuple[str, str]) -> None:
    if key in _cache: return
    _cache[key] = value
    _cache_order.append(key)
    if len(_cache_order) > _CACHE_MAX:
        old = _cache_order.pop(0)
        _cache.pop(old, None)

# --------------- Public API ---------------

def openai_generate_text(
    prompt: str,
    models: Optional[List[str]] = None,
    timeout: int = 60,
    temperature: float = 0.0,
    max_output_tokens: int = 1024,
    max_retries: int = 4,
    sleep_between_models: float = 0.3,
    return_model: bool = False,
) -> Union[str, Tuple[str, str]]:
    """Generic OpenAI Chat Completion caller with retry, backoff, cache, and model fallback."""
    assert OPENAI_API_KEY, "OPENAI_API_KEY missing in environment"
    try_order = models or DEFAULT_MODEL_ORDER
    ck = _cache_key(prompt, temperature, max_output_tokens, try_order)
    cached = _cache_get(ck)
    if cached is not None:
        text, used_model = cached
        if DEBUG: print(f"[openai:cache] hit -> {used_model}")
        return (text, used_model) if return_model else text

    last_err: Optional[Exception] = None
    for m in try_order:
        url = f"{OPENAI_BASE}/chat/completions"
        payload = {
            "model": m,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": float(temperature),
            "max_tokens": int(max_output_tokens),
        }
        for attempt in range(max_retries):
            if DEBUG: print(f"[openai] calling: {m} attempt {attempt+1}/{max_retries}")
            try:
                data = _post_json(url, payload, timeout=timeout)
                choices = data.get("choices") or []
                if not choices:
                    text = str(data)
                else:
                    msg = choices[0].get("message", {})
                    text = (msg.get("content") or "").strip()
                _cache_put(ck, (text, m))
                return (text, m) if return_model else text
            except requests.HTTPError as e:
                last_err = e
                status = e.response.status_code if e.response is not None else None
                if status in (429, 500, 503) and attempt < max_retries - 1:
                    backoff = (2 ** attempt) + random.uniform(0, 0.4)
                    time.sleep(backoff)
                    continue
                break
            except Exception as e:
                last_err = e
                time.sleep(0.25)
                break
        time.sleep(sleep_between_models)
    raise RuntimeError(f"All OpenAI model(s) failed. Last error: {last_err}")
