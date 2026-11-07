#!/usr/bin/env python3
"""Round 2 merge: Claude Opus 5.5 (OpenRouter BYOK) revises the draft against the roster's critiques."""
import json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
import keys
HERE = pathlib.Path(__file__).resolve().parent
crit = []
for f in sorted(HERE.glob("round2-*.json")):
    d = json.loads(f.read_text())
    t = d.get("text") or "".join(c.get("text", "") for c in d.get("content", []) if c.get("type") == "text")
    if t and len(t) > 500:
        crit.append(f"=== Critique from {f.stem.removeprefix('round2-')} ===\n{t}")
PROMPT = f"""You merged eight proposals into the draft below. Now {len(crit)} models have critiqued it. Produce the FINAL design, under 1300 words, ready to pre-register.

Hard constraints (from the decision-maker, not negotiable):
- No team. The only human adjudicates at most 20 answers in total. Everything else (key building, key verification, extraction, retrieval checks) is done by tools: a search API returning Chinese database and catalogue records (CNKI, VIP, Wanfang, CiNii, publisher and university pages), a fetch tool, and cheap LLMs.
- An LLM may extract and normalise fields and draft a verdict for a human to check; it never makes a final verdict on an invented/unresolved flag that drives a decision.
- Budget: a few US dollars of model calls in total, eight models.
- The decision-maker's values: an invented record is worse than a refusal; a near-miss that keeps meaning and stays retrievable is tolerable; a model that answers rarely but accurately should be admitted only if its answer rate is not negligible, and if its answer rate swings between item sets while its accuracy holds, it should be admitted. The rule must test that directly.

Sections:
A. Key building without a team (step by step; what counts as a primary record; independence of the two retrievals; what drops an item).
B. Item set and negative controls (counts sized to what tools can verify; strata).
C. Question wording.
D. Scoring definitions (mechanical where possible), and how the human's 20 adjudications are allocated.
E. Decision rule: exact thresholds, the interval method, the "answer rate swings, accuracy holds" test, the indeterminate zone.
F. Threats and guards.
G. Critiques NOT adopted, each with one line why.
H. Cost estimate (calls per model, total).

=== DRAFT ===
{(HERE / 'merged-draft-1.md').read_text()}

{chr(10).join(crit)}"""
r = keys.openrouter_chat({"model": "anthropic/claude-opus-5.5", "messages": [{"role": "user", "content": PROMPT}],
                          "max_tokens": 20000, "reasoning": {"effort": "high"}})
text = r["choices"][0]["message"]["content"] if "choices" in r else json.dumps(r)
(HERE / "final-design.md").write_text(f"<!-- merged by anthropic/claude-opus-5.5 via OpenRouter BYOK from {len(crit)} round-2 critiques, generation {r.get('id')} -->\n\n{text}\n")
print(r.get("id"), len(text), len(crit))
