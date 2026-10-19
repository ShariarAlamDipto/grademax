"""Unified LLM client for Groq and OpenRouter (both OpenAI-compatible chat APIs)."""
from __future__ import annotations
import json
import time
import urllib.request
import urllib.error

from .env import load_env

_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

_ENDPOINTS = {
    "groq": "https://api.groq.com/openai/v1/chat/completions",
    "openrouter": "https://openrouter.ai/api/v1/chat/completions",
}
_KEYS = {"groq": "GROQ_API_KEY", "openrouter": "OPENROUTER_API_KEY"}


class LLMError(RuntimeError):
    pass


def chat(provider: str, model: str, messages: list[dict], *,
         temperature: float = 0.2, max_tokens: int = 2048,
         json_mode: bool = False, retries: int = 5) -> str:
    env = load_env()
    key = env.get(_KEYS[provider])
    if not key:
        raise LLMError(f"Missing {_KEYS[provider]}")
    url = _ENDPOINTS[provider]
    body: dict = {"model": model, "messages": messages,
                  "temperature": temperature, "max_tokens": max_tokens}
    if json_mode:
        body["response_format"] = {"type": "json_object"}
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {key}",
        "User-Agent": _UA,
        "HTTP-Referer": "https://grademax.me",
        "X-Title": "GradeMax Predictor",
    }
    delay = 2.0
    last_err = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, data=json.dumps(body).encode(), headers=headers)
            with urllib.request.urlopen(req, timeout=90) as r:
                data = json.load(r)
            return data["choices"][0]["message"]["content"]
        except urllib.error.HTTPError as e:
            detail = ""
            try:
                detail = e.read().decode()[:300]
            except Exception:
                pass
            last_err = f"HTTP {e.code}: {detail}"
            # 429 / 5xx are retryable
            if e.code in (429, 500, 502, 503, 529):
                time.sleep(delay)
                delay = min(delay * 2, 30)
                continue
            raise LLMError(last_err)
        except (urllib.error.URLError, TimeoutError) as e:
            last_err = str(e)
            time.sleep(delay)
            delay = min(delay * 2, 30)
    raise LLMError(f"Exhausted retries: {last_err}")


def chat_json(provider: str, model: str, messages: list[dict], **kw) -> dict:
    """Call chat() and parse a JSON object out of the response (tolerant of code fences)."""
    raw = chat(provider, model, messages, json_mode=True, **kw)
    return parse_json(raw)


def _repair_json(s: str) -> str:
    """Make LLM-emitted JSON parseable without corrupting LaTeX.

    Two common hazards, fixed by walking the string with quote-state tracking:
      1. LaTeX with single backslashes inside strings ("\\frac", "\\text", "\\theta").
         Sequences like \\t \\f \\b are valid JSON escapes, so json.loads silently
         turns "\\text" into <tab>ext. We double every backslash except genuine
         structural escapes (\\\\ \\" \\/ \\uXXXX) — in LaTeX-bearing content a stray
         backslash is always a command, not an escape.
      2. Raw control characters (newline/tab) inside string values, which JSON
         forbids — we escape them.
    """
    out: list[str] = []
    in_str = False
    i, n = 0, len(s)
    while i < n:
        ch = s[i]
        if not in_str:
            if ch == '"':
                in_str = True
            out.append(ch); i += 1; continue
        if ch == "\\" and i + 1 < n:
            nxt = s[i + 1]
            if nxt in '"\\/u':
                out.append(ch); out.append(nxt); i += 2
            else:
                out.append("\\\\"); i += 1
        elif ch == '"':
            in_str = False; out.append(ch); i += 1
        elif ch == "\n":
            out.append("\\n"); i += 1
        elif ch == "\r":
            out.append("\\r"); i += 1
        elif ch == "\t":
            out.append("\\t"); i += 1
        elif ord(ch) < 0x20:
            out.append(f"\\u{ord(ch):04x}"); i += 1
        else:
            out.append(ch); i += 1
    return "".join(out)


def parse_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```", 2)[1]
        if text.lstrip().lower().startswith("json"):
            text = text.lstrip()[4:]
    text = text.strip()
    # Trim to the outermost JSON object if there is leading/trailing prose.
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end != -1 and end > start:
        text = text[start:end + 1]
    try:
        return json.loads(_repair_json(text))
    except json.JSONDecodeError:
        return json.loads(text)
