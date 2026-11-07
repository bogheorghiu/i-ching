Write ONE self-contained Python 3 script, `build_keys.py`, that builds verified answer keys for the evaluation described in ../design/final-design.md (sections A–C) under the frozen decisions in ../PREREG.md and the hard rules in ../keys-sonnet/INSTRUCTIONS.md. These three files are appended below. Output only the script, in one ```python block, then a short "How to run" note.

Design principle (the owner's): script everything. Models are called only where judging language is unavoidable, and every model output is checked by code. Each candidate is accepted or dropped in one pass; nothing loops open-endedly.

Requirements:
1. Stages, each resumable from files (a container restart kills processes; rerunning the script must skip work already saved):
   a. harvest candidates from journal tables of contents and catalogue/publisher lists via DeepSeek search (random offsets; the strata in the design);
   b. for each candidate, obtain two INDEPENDENT primary records (rules in INSTRUCTIONS.md), saving every raw response under snapshots/;
   c. extract author/title/venue/year/volume_issue from each snapshot with one call to "deepseek/deepseek-v4.1-flash-1017:exacto" (OpenRouter, "provider": {"zdr": true}, "reasoning": {"effort": "max"}); code then checks every extracted field occurs verbatim in that snapshot (after normalisation) or drops the field;
   d. compare the two records in code (traditional→simplified via a small built-in mapping or the `opencc` module only if already importable; never install anything); any mismatch drops the item;
   e. write the clue with one call to "anthropic/claude-sonnet-5.5" (OpenRouter, "provider": {"only": ["anthropic"]}, "reasoning": {"effort": "max"}); send it ONLY the verified key fields and the abstract/keywords text, never whole pages (the owner's OpenRouter guardrail redacts phone/email/IP-like strings, which can hit ISBNs);
   f. leakage check in code (no 3-char Chinese substring or 2-word English phrase shared with the title) and identifiability check (DeepSeek search of the clue returns the key in the top 10);
   g. verification: batches of 10 accepted items sent to "anthropic/claude-opus-5.5" (provider only anthropic, reasoning max) with the key fields, the two record URLs and short evidence excerpts; Opus returns JSON flags per item; any flagged item is dropped (never repaired).
2. Use "cache_control": {"type": "ephemeral"} at the top level of every Anthropic request (chat completions body), so repeated prefixes are cached.
3. Cost cap: sum usage.cost_details.upstream_inference_cost (BYOK; `usage.cost` reads 0) plus usage.cost for non-BYOK calls; stop cleanly when a --max-usd limit is reached. Log every model call (model, generation id, tokens, cost) to calls.jsonl.
4. Outputs: items.jsonl, dropped.jsonl (with the drop rule), REPORT.md (counts by stratum and drop rule, cost, yield). Flags: --target N (items to keep), --max-usd, --stage.
5. HTTP: use only the standard library (urllib). Endpoints: OpenRouter chat completions https://openrouter.ai/api/v1/chat/completions (Bearer $OPENROUTER_API_KEY); DeepSeek tools https://api.deepseek.com/v1/tools/search with {"query","count","need_content"} and /v1/tools/fetch with {"url"} (Bearer $DEEPSEEK_API_KEY). Any placeholder key works where a proxy injects keys. Retry each HTTP call twice on connection errors; save partial progress after every item.
6. Never scrape ctext.org; public academic queries only.

Reusable code from earlier agent runs is appended after the design files (their helper libraries); reuse what is sound.

ADDENDUM (owner, 2026-11-04): a built-in WRITER COMPARISON.
- Stage e (clue writing) runs three writers on the SAME verified candidates, each producing its own clue: (1) "anthropic/claude-sonnet-5.5" via OpenRouter, provider only anthropic, reasoning max; (2) "anthropic/claude-opus-5.5" the same way; (3) DeepSeek Flash via DeepSeek's OWN API, not OpenRouter: POST https://api.deepseek.com/anthropic/v1/messages, headers "x-api-key: $DEEPSEEK_API_KEY", "anthropic-version: 2023-06-01", model "deepseek-flash", max reasoning (use the largest thinking budget the endpoint accepts; record what was sent).
- A --writers flag selects any subset (default all three), so the run can proceed with DeepSeek alone if OpenRouter is unavailable (its workspace budget was exhausted on 2026-11-04).
- Each writer's clue passes the same code checks (leakage, identifiability); stage g verification by Opus covers every writer's output, blind to which writer produced it (shuffle, strip writer labels).
- REPORT.md gains a per-writer table: clues produced, passed leakage, passed identifiability, flagged by Opus, cost per accepted clue, and examples of disagreements between writers on the same item.
- Calls to DeepSeek's own API: cost is computed from its usage tokens and its published prices if returned; otherwise log tokens only and say so.
