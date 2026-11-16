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

## 4. Result (2026-11-16)

**The call.** One call, no retry needed: generation `gen-1794835642-o4gtEy88ODIm2rLJHaAe`, `finish_reason`
stop, 14,070 prompt tokens, 5,623 completion tokens (5,512 reasoning), USD 0.046. The picked batch is a run 4
batch (`batch_6eab1cfcd693`). DeepSeek returned one parseable verdict for each of the 10 units.

| | Units |
|---|---|
| Neither flagged | 6 |
| Flagged by both | 0 |
| Opus only | 4 (3 `clue_leaks`, 1 `other_fitting_work`) |
| DeepSeek only | 0 |

DeepSeek flagged nothing; its note on each of the four reads, in substance, "records and clue match key; no
issues found".

**What the four Opus flags were** (read after the result; full notes on `battery2-keys`):
- The three `clue_leaks` each point at one or two title words that the clue repeats: a hexagram name, a
  character the article discusses, a period name. The code leakage check (a shared 3-character n-gram) let
  these through because the repeated term is shorter than 3 characters, or is split differently.
- The `other_fitting_work` names another article by the same author, in the same journal, that Opus says fits
  the clue too. That claim comes from Opus's memory and was not checked.

**What this shows, within its limits.** On this batch, DeepSeek V4 Pro at maximum effort was the more lenient
checker: it raised none of the four flags Opus raised and none of its own. That is the opposite of the
hypothesis being tried. One batch of 10 units cannot say how often this holds across the pool. Nothing changed
status (section 2).

**Not checked.** Whether Opus's four flags were right: whether those clues really leak, and whether the other
article exists. The three short-term leaks point at a gap in the code check that is worth its own look; that is
a separate change, not made here.

Saved: the answer, the batch and the unit-by-unit table are in this session's scratchpad until they can be
pushed to `battery2-keys`, folder `verifier2-trial-2026-11-16/` (this session has read access only; see the PR).
