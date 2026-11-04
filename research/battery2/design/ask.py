#!/usr/bin/env python3
"""Send the design brief to the roster; save each answer with its generation ID."""
import json, pathlib, sys, time
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
import keys
HERE = pathlib.Path(__file__).resolve().parent
BRIEF = (HERE / "brief.md").read_text()
OR_ARMS = {
    "deepseek-v4.1-flash-1017": ("deepseek/deepseek-v4.1-flash-1017:exacto", {"effort": "max"}),
    "kimi-k3.1-pro": ("moonshotai/kimi-k3.1-pro:exacto", {"effort": "max"}),
    "glm-5.3": ("z-ai/glm-5.3:exacto", {"effort": "max"}),
    "mimo-v2.6-pro": ("xiaomi/mimo-v2.6-pro:exacto", None),
    "gpt-6.1-sol": ("openai/gpt-6.1-sol", {"effort": "high"}),
    "gemini-3.1-pro": ("google/gemini-3.1-pro-preview", {"effort": "high"}),
    "claude-opus-5.5-byok": ("anthropic/claude-opus-5.5", {"effort": "high"}),
}
def ask(name):
    model, reasoning = OR_ARMS[name]
    body = {"model": model, "messages": [{"role": "user", "content": BRIEF}], "max_tokens": 12000}
    if reasoning: body["reasoning"] = reasoning
    if not model.startswith(("openai/", "google/", "anthropic/")): body["provider"] = {"zdr": True}
    for attempt in (1, 2):
        try:
            r = keys.openrouter_chat(body)
            break
        except OSError as e:
            r = {"error": {"exception": repr(e), "attempt": attempt}}
    text = r["choices"][0]["message"].get("content") if "choices" in r else json.dumps(r)[:800]
    return name, {"model": model, "generation_id": r.get("id"), "text": text}
def ask_and_save(name):
    name, rec = ask(name)
    (HERE / f"round1-{name}.json").write_text(json.dumps(rec, ensure_ascii=False, indent=1))
    print(name, rec["generation_id"], len(rec["text"] or ""), flush=True)
names = sys.argv[1:] or list(OR_ARMS)
with ThreadPoolExecutor(8) as ex:
    list(ex.map(ask_and_save, names))
