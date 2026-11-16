# Battery 2: DeepSeek as a second verifier, one-batch trial

Written 2026-11-16, before the call it describes. The owner marked this "next" on the plan page
(`steer/current`, version 3): "Try DeepSeek as a second checker of questions. Your idea: it may be the stronger
adversary. One already-checked batch, report where its flags differ." Sections 1-3 are frozen once committed;
the result goes in a later section.

## 1. What is compared

Stage g of `build_keys.py` sends verification batches of up to 10 units (key fields, two record excerpts, one
clue) to Claude Opus 5.5, which may only raise flags; code drops every flagged unit. Each batch is saved on
`battery2-keys` as `keys-pipeline-run*/verify/batch_*.json`, with the exact units sent (`request_units`) and
Opus's answer (`raw_output`).

The trial sends **one saved batch, unchanged**, with the same system prompt (`verify_system()`), to DeepSeek V4
Pro, and compares the flags unit by unit.

- **Batch.** All 64 saved batch files (runs 1-4, every one with an Opus answer) are sorted by path;
  `random.Random("b2-ds-verifier-20261116").choice` picks one. Code picks it, after this file is committed.
- **Model and settings.** `deepseek/deepseek-v4-pro-0813` through OpenRouter, `provider.zdr = true` (as the
  pipeline's non-Anthropic calls), `reasoning.effort = "max"` (the owner's production setting for DeepSeek,
  PREREG decision 2), `max_tokens = 128000`, streamed. Why this model: the newest and largest DeepSeek model in
  OpenRouter's catalogue on 2026-11-16. Why this route and not the courier: it is the route the Opus batch went
  through, so the two runs differ in the model only; a single call needs no batching.
- **What leaves the session.** The batch's key fields and record excerpts (public bibliographic data and
  scholars' names as published) and the clue. The same kind of content already went to DeepSeek as clue writer
  and extractor. No personal data. Generation ID and cost are recorded.
- **Cap.** USD 1. One retry if the answer is empty or cut off (`finish_reason = length`); nothing more.

## 2. What is reported

For each unit: Opus's flags, DeepSeek's flags, both notes. Counts: units neither flagged, flagged by both,
by Opus only, by DeepSeek only; and for units flagged by both, whether the flag names agree.

Fixed now, before the answer:
- **Report-only.** No unit, clue or item changes status because of this trial, whatever DeepSeek says.
- A DeepSeek-only flag on a unit Opus passed is listed in full for the owner. Making DeepSeek a standing
  second verifier would need its own PREREG deviation, written before it drops anything.
- A DeepSeek answer that cannot be parsed into one verdict per unit, after the one retry, is reported as a
  failed trial, not re-asked in another form.
- One batch is 10 units at most. The result can show that the two models differ and how; it cannot estimate
  how often they differ in the pool.

## 3. Where things go

The answer, the unit-by-unit table and the call record go to the private branch `battery2-keys`, folder
`verifier2-trial-2026-11-16/`, because they hold key fields. This repo gets only counts and flag names.
