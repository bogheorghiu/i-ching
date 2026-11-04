#!/usr/bin/env python3
"""Round 1 merge: Claude Opus 5.5 (OpenRouter BYOK) merges the roster's proposals into one draft design."""
import json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
import keys
HERE = pathlib.Path(__file__).resolve().parent
props = []
for f in sorted(HERE.glob("round1-*.json")):
    d = json.loads(f.read_text())
    t = d.get("text") or "".join(c.get("text", "") for c in d.get("content", []) if c.get("type") == "text")
    props.append(f"=== Proposal from {f.stem.removeprefix('round1-')} ===\n{t}")
PROMPT = f"""Below is a design brief, then {len(props)} independent proposals answering it, from different models.

Merge them into ONE concrete evaluation design, under 1100 words, with these sections:
A. Item set (count, strata, how keys are verified before the run, negative controls).
B. Question wording rules.
C. Scoring definitions (answered, correct, near-miss, wrong, invented), mechanical where possible; who or what judges the rest.
D. Pre-registered decision rule with thresholds, and the sample-size reasoning behind them.
E. Threats and guards.
F. DISAGREEMENTS: every point where proposals materially disagree, each with the options, which proposals took which, and your recommendation with its reason. Do not hide a disagreement by averaging.
Prefer the cheapest design that still separates "selective but accurate" from "lucky" and from "prolific inventor". Budget: a few US dollars total for six to eight cheap models.

=== BRIEF ===
{(HERE / 'brief.md').read_text()}

{chr(10).join(props)}"""
r = keys.openrouter_chat({"model": "anthropic/claude-opus-5.5", "messages": [{"role": "user", "content": PROMPT}],
                          "max_tokens": 16000, "reasoning": {"effort": "high"}})
text = r["choices"][0]["message"]["content"] if "choices" in r else json.dumps(r)
(HERE / "merged-draft-1.md").write_text(f"<!-- merged by anthropic/claude-opus-5.5 via OpenRouter BYOK, generation {r.get('id')} -->\n\n{text}\n")
print(r.get("id"), len(text))
