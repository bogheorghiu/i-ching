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

## 5. Corrections after blind review (2026-11-16)

A fresh agent checked sections 1-4 against the code, the saved batch and the raw answer. It confirmed the batch
pick (re-run of the seeded choice), the order of events (sections 1-3 committed at `823026b` before the call;
byte-identical in the result commit), the call record, the counts and the flag names. Corrections:

- **The runs differ in more than the model.** Section 1 says the route makes the two runs "differ in the model
  only". False. Stage g called Opus with `reasoning.max_tokens = 16000`, `max_tokens = 32000`,
  `provider.only = ["anthropic"]`, not streamed; this trial sent DeepSeek `reasoning.effort = "max"`,
  `max_tokens = 128000`, `provider.zdr = true`, streamed. So section 4's conclusion reads: on this batch, DeepSeek
  V4 Pro at maximum effort raised none of the four flags that Opus raised under a 16,000-token reasoning cap.
  Model and reasoning setting both differ.
- **No `:exacto` endpoint.** The pipeline's non-Anthropic call uses one, and PREREG decision 2 names them for
  the models under test; this call did not.
- **"Newest and largest"**: `deepseek-v4-pro-0813` is the newest Pro model listed on 2026-11-16, not the newest
  DeepSeek model (`deepseek-v4.1-flash-1017` is later). "Largest" was not checked against parameter counts.
- **A confound not named in section 2.** 3 of the 10 clues were written by DeepSeek's own model (the pipeline's
  native writer); a DeepSeek verifier may favour them. Opus flagged 1 of those 3 and 3 of the 7 Sonnet clues.
- **DeepSeek's notes** are the same string, word for word, on all 10 units, with 5,512 reasoning tokens at
  maximum effort.
- **The cap** of USD 1 was not enforced in code; it held in fact (USD 0.046, no retry).
- **Saved files.** The batch is already on `battery2-keys`; the scratchpad holds the answer, the table, the
  script and its log. Nothing is in `verifier2-trial-2026-11-16/` yet: a deviation from section 3 until this
  session can push there.
- The code leakage check also has an English 2-word rule; section 4 describes only the Chinese one, which is the
  one that applied.

## 6. Deviation, 2026-11-16, before its call: Flash 1017 replaces Pro (owner's instruction)

The owner, in chat after the Pro result: "forget deepseek pro, use flash 1017". So the trial is run again on
the same batch (`batch_6eab1cfcd693`, same seeded pick), with the same system prompt and user message, on
`deepseek/deepseek-v4.1-flash-1017:exacto` (the pipeline's own extractor endpoint, which also answers the
`:exacto` point in section 5), `reasoning.effort = "max"`, `max_tokens = 128000`, `provider.zdr = true`,
streamed. Same reporting rules as section 2, same one-retry rule, cap USD 1. The Pro result in section 4 stays
on record; Flash is the trial's model from here on. Written before the Flash call.

## 7. Result with Flash 1017 (2026-11-16)

One call, no retry: generation `gen-1794836165-lFOyvu9y02MI6yJcSW3k`, `finish_reason` stop, 14,004 prompt tokens,
15,916 completion tokens (15,593 reasoning), USD 0.0085. Ten parseable verdicts.

| | Units |
|---|---|
| Neither flagged | 6 |
| Flagged by both | 0 |
| Opus only | 4 (the same 4 as in section 4) |
| Flash only | 0 |

Unlike Pro, Flash wrote a note specific to each unit, each saying it found no issue. So on this batch both
DeepSeek tiers at maximum effort raised none of Opus's four flags (Opus under a 16,000-token reasoning cap). The
self-preference confound of section 5 does not explain it here: of Opus's four flags, three were on Sonnet-written
clues, and Flash passed those too.

**Route, recorded after the call.** The owner's standing preference (ClaudeShared `field-notes/model-routing.md`,
2026-11-12) sends DeepSeek work to DeepSeek's own API, keeping the OpenRouter balance for steps that need model
diversity. Both trial calls went through OpenRouter instead (USD 0.055 together). Later DeepSeek calls from this
work go to `api.deepseek.com` (`deepseek-flash`, thinking enabled, `reasoning_effort` max, streamed), as that note
and the courier guide describe.

**Next, if wanted (not done):** whether Opus's flags are right decides which checker is "stronger" here. The three
`clue_leaks` flags are checkable in code (a 1-2 character title term repeated in the clue) on the whole pool,
without any model.
