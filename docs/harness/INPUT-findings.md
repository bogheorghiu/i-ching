# Findings, 2026-11-04 (one session; evidence in the repo and in generation ids)

Routing and keys
- One module reads keys and decides where requests go (research/keys.py); everything else calls it. In a cloud environment the proxy injects keys: placeholders work.
- Claude through OpenRouter with provider.only=['anthropic'] runs on the owner's Anthropic key (BYOK): generation record is_byok=true, cost 0, upstream_inference_cost = real spend.
- An OpenRouter workspace weekly budget counts BYOK; hitting it stops every call mid-run. Check limits as well as credits.
- Cloud network-secret rules match literal path prefixes, trailing slash included (/chat/completions/ blocked /chat/completions until fixed). A session's environment description can lag the settings: test each rule with one call.
- The owner's OpenRouter guardrail redacts phone/email/IP-like strings (ISBNs at risk): keep raw page content out of guarded calls.

Cost
- Under BYOK, cost fields read 0, so cost-based stop conditions never fire: cap on upstream_inference_cost.
- Without prompt caching an agent loop resends its whole context each step (input 1k->52k tokens over 16 steps). Anthropic automatic caching: top-level cache_control (chat completions) / cacheControl (@openrouter/agent; snake_case silently dropped). Probe: second call cached 4011 tokens, cost 0.0101 -> 0.00045.
- reasoning effort max can consume all of max_tokens (Opus: empty answer, all 32k reasoning; DeepSeek: 64k thinking, 0 text, budget ignored). Set reasoning.max_tokens explicitly and max_tokens near the model's real output limit (Opus/Sonnet 5.5: 128k; DeepSeek flash: ~943k), not a habit number.

Transport
- Long non-streamed calls drop (DeepSeek: connection reset; OpenRouter: blank-line and ': OPENROUTER PROCESSING' padding before JSON; Kimi: IncompleteRead). Stream long calls; strip padding before parsing.
- Opus 5.5 rejects assistant prefill: continue a truncated answer with a new user turn, then stitch.
- Cloud worker restarts kill background processes (several times today). Every long job must resume from files.

Agents vs scripts
- Open agent loops (Sonnet max, Opus max, same prompt) collected ~200 source snapshots and closed 0 items in ~37 calls each. The scripted pipeline (models only where language judgment is unavoidable, every model output checked by code) closes or drops each candidate in one pass; test 4 produced the first verified item.
- The agent's best use: writing and patching the script (Opus wrote 1,531 lines; three function-level patches from run evidence, ~$0.4-0.7 each), applied by a small AST-based applier.
- An agent with a shell tool pip-installed a package unasked; forbid installs explicitly.

Verification discipline
- Pre-register before any run; keys checked against the fact's own record before the run (a key copied from a secondary note was wrong; a question misdescribed its work). Deviations recorded with reasons before the data they affect; the admission bar may be raised after results, never lowered.
- Corroborate load-bearing artefacts with an independent cheap strong model (DeepSeek flash wrote the same pipeline independently, 1,747 lines). Blind design rounds: 8 models proposed, 7 critiqued, one merged; disagreements listed, not averaged.
- Calibration on 5 well-cited items cannot separate selective-but-accurate from lucky; abstention varied 0-80% across models.

Coordination
- A shared board (Delegation artifact) carries in-flight heavy calls and dated environment facts between sessions; a second session built a "courier" (scheduled task that fires OpenRouter/DeepSeek calls and writes results to Drive) for the same purpose.
