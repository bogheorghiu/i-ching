"""The one module that reads API keys and decides where requests go (CODEOWNERS should own it).

Keys come only from the environment. Where a proxy injects credentials (a Claude Code cloud
environment), any placeholder value works and the proxy replaces it.
"""
import json
import os
import urllib.request

OPENROUTER = "https://openrouter.ai/api/v1"
DEEPSEEK = "https://api.deepseek.com/v1/tools"


def _post(url, key_var, body, timeout=600):
    key = os.environ.get(key_var)
    if not key:
        raise SystemExit(f"{key_var} is not set. Add it to the environment (never to a file or chat).")
    req = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST",
                                 headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read().decode(errors="replace")
    except urllib.error.HTTPError as e:
        return {"error": {"status": e.code, "body": e.read().decode(errors="replace")[:2000]}}
    # OpenRouter pads long (reasoning) calls with blank lines and ': OPENROUTER PROCESSING' comments.
    body = "\n".join(l for l in raw.splitlines() if l.strip() and not l.startswith(":"))
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        return {"error": {"unparsed_body": raw[-3000:]}}


def _get(url, key_var, timeout=60):
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {os.environ.get(key_var, '')}"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return {"error": {"status": e.code}}


def openrouter_chat(body):
    return _post(f"{OPENROUTER}/chat/completions", "OPENROUTER_API_KEY", body)


def openrouter_generation(gen_id):
    return _get(f"{OPENROUTER}/generation?id={gen_id}", "OPENROUTER_API_KEY")


def deepseek_search(query, count=5):
    """Public, academic queries only: this API offers no zero-retention guarantee."""
    return _post(f"{DEEPSEEK}/search", "DEEPSEEK_API_KEY", {"query": query, "count": count, "need_content": False})
