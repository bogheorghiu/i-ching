# Battery 2: how to run it again

Written 2026-11-16, before the first run. The owner marked this "next" on the plan page (`steer/current`,
version 3: "what stays fixed, what is recorded per run, how fresh questions are added as models get newer"),
and added on 2026-11-15: both readers on a random sample of pages for each new site. Where this file and
`PREREG.md` differ, `PREREG.md` wins; a change to this file is a dated section added below, never an edit.

**Why it is written now.** Battery 2's verdicts are only comparable across runs if what a run may change is
fixed before anyone has seen a result, the same reason `PREREG.md` fixed the admission rule first.

## 1. Fixed across runs

A run that changes any of these is a new battery, reported as such, not a re-run.

- The frozen item set and its blocks, by the composition rule and seed recorded at freeze (not written yet;
  the composition step on the plan page). Its commit on `battery2-keys` is named in every run report.
- The question text: the template, the instruction sentence, and each item's clue as frozen.
- The admission rule (`final-design.md` §E with `PREREG.md`). A threshold may only be raised, recorded first
  (PREREG decision 1).
- The scorer and its version (not built yet). A scorer fix is a new version; every earlier run is re-scored
  with it and both scores are reported.
- Run settings: production settings per model (PREREG decision 2), no tools, item order shuffled per model
  with a seed recorded in the run report.

## 2. Recorded per run

In the run report (public: counts, verdicts, model ids; no item text) and on `battery2-keys` (everything else):

- for each model: the requested id, the served model and provider from each call's generation record, the
  reasoning setting sent, the date range of the calls, and its knowledge cutoff as its maker states it, with
  the source and the date it was read;
- the harness commit in this repo and the `battery2-keys` commit;
- every call's generation id, status, `finish_reason`, tokens and cost; failed calls marked missing and
  re-run (`final-design.md` §F), the count of re-runs per model;
- the scope line agreed on 2026-11-15: which cells the set covers and which are empty and why (the table on
  issue #33, 2026-11-15 06:02).

## 3. Fresh items as models get newer

The set ages: an item published before a model's cutoff may have been in its training data. So:

- New items are built by the same pipeline under the deviations in force, frozen as a new block with its own
  seed before any model answers it, and never mixed into an old block.
- Items published after a model's stated cutoff are reported separately for that model (`final-design.md` §B),
  and never used to rescue an admission.
- Reserve blocks 5-6 rotate into later runs (`final-design.md` §F). A block a model has answered is not
  "unseen" for that model's successor from the same maker; the report says which blocks each model family has
  already answered.

## 4. Sources and page readers

The two-readers rule stays (owner, 2026-11-15): record A and record B come through different fetch APIs
(PREREG deviation 4). Added:

- **A new site** (any host not yet used as a record source) is first read through both readers on a random
  sample of its pages, and the two copies are compared in code by the unit that later stages read (an entry
  line, a field). The sample size, the seed and the bar are written down before the sample is drawn. The site
  is used only if the bar is met; the result is recorded with the site.
- **Existing sites** get the same check on a fresh random sample at each re-run, so a reader that changes
  between runs is caught.
- **Why**, in this project's own data: on 7 of 13 stored 周易研究 contents pages (2018-2024), DeepSeek's copy
  had silently lost 4 to 21 entry lines that Moonshot's copy kept (2026-11-16, `pipeline/CONTROLS-DESIGN.md`
  section 2). A lost line can only drop a key, but it can turn an absence check (negative controls, the
  "invented" verdict) into a false result.

## 5. Not covered yet (Gaps)

- The composition rule and freeze, the scorer, and the rule-validation simulation (`PREREG.md`) do not exist;
  section 1 names them as fixed once they do.
- How the tool-using battery (owner, 2026-11-09: same keys, separate battery) shares blocks with this one.
