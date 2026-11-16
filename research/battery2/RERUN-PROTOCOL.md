# Battery 2: how to run it again

Written 2026-11-16, before the first run. The owner marked this "next" on the plan page (`steer/current`,
version 3: "what stays fixed, what is recorded per run, how fresh questions are added as models get newer"),
and added on 2026-11-15: both readers on a random sample of pages for each new site. Where this file and
`PREREG.md` differ, `PREREG.md` wins; a change to this file is a dated section added below, never an edit.

**Why it is written now.** Battery 2's verdicts are only comparable across runs if what a run may change is
fixed before anyone has seen a result, the same reason `PREREG.md` fixed the admission rule first.

## 1. Fixed across runs

A run that changes any of these is a new battery, reported as such, not a re-run. Two exceptions, both re-runs: a threshold raised under PREREG decision 1 after the first run's results, and a new scorer version. In both, every earlier run is judged again under the change, and old and new verdicts are both reported.

- The frozen item set and its blocks, by the composition rule and seed recorded at freeze (not written yet;
  the composition step on the plan page). Its commit on the private branch `battery2-keys` of
  `bogheorghiu/delegation-results` is named in every run report.
- The 24 negative controls (not built yet; `final-design.md` §B), and the items chosen for repeat samples
  (40) and paraphrases (30) (`final-design.md` §F), all fixed at freeze with recorded seeds. If the §H overrun
  rule cuts paraphrases or repeat samples in a run, the run report says what was cut.
- The question text: the template, the instruction sentence, and each item's clue as frozen.
- The admission rule (`final-design.md` §E with `PREREG.md`). Before the first run, thresholds may still be
  revised as PREREG's rule validation allows; after the first run's results, a threshold may only be raised,
  recorded first (PREREG decision 1).
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
- Items published after a model's stated cutoff are reported separately for that model (`final-design.md` §B).
  They stay in their blocks and count in the admission rule as every item does.
- Reserve blocks 5-6 rotate into later runs (`final-design.md` §F). A block a model has answered is not
  "unseen" for that model's successor from the same maker; the report says which blocks each model family has
  already answered. What replaces a reserve block once §E has used it for an indeterminate model is not
  decided yet (Gap), nor the size and strata of a new block.
- Contamination before any answer: the item material passed through DeepSeek's and Moonshot's fetch APIs,
  Kimi compiled seed lists, and keys and clues were built with Claude and DeepSeek models. Each run report says,
  per maker of a tested model, which of its services saw the item material.

## 4. Sources and page readers

The two-readers rule stays (owner, 2026-11-15): in the seeded intake, record A and record B come through
different fetch APIs (PREREG deviation 4, which covers that intake only). Added, to be written as a PREREG
deviation before any item is built from a new site:

- **A new site** (any host not yet used as a record source) is first read through both readers on a random
  sample of its pages, and the two copies are compared in code by the unit that later stages read (an entry
  line, a field). The sample size, the seed and the bar are written down before the sample is drawn. The site
  is used only if the bar is met; the result is recorded with the site.
- **Existing sites** get the same check on a fresh random sample at each re-run, so a reader that changes
  between runs is caught. A failed check never removes items from the frozen set: the run report names the
  site, and reports every verdict twice, with and without that site's items.
- **Why**, in this project's own data: on 7 of 13 stored 周易研究 contents pages (2018-2024), DeepSeek's copy
  had silently lost 4 to 21 entry lines that Moonshot's copy kept (2026-11-16, `pipeline/CONTROLS-DESIGN.md`
  section 2). A lost line usually drops a key (it can also turn an ambiguous match into a unique one), and it can turn an absence check (negative controls, the
  "invented" verdict) into a false result.

## 5. Not covered yet (Gaps)

- The composition rule and freeze, the scorer, and the rule-validation simulation (`PREREG.md`) do not exist;
  section 1 names them as fixed once they do.
- Per run: whether the owner's 20 adjudications (PREREG decision 4, `final-design.md` §D) are a budget per
  run, and whether new blocks get their own pre-run key audits.
- Whether a call that stops at `finish_reason = length` counts as failed and is re-run; the answer cap that
  PREREG decision 2 raised; how "production setting" is chosen for a model decision 2 does not name.
- How the tool-using battery (owner, 2026-11-09: same keys, separate battery) shares blocks with this one.
