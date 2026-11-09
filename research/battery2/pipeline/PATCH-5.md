# Patch 5: seeded intake from issue tables of contents

Why: tests 4-6 kept 1 item from 105 search-harvested candidates. Deviation 2 (PREREG) allows a
research institute's complete issue TOC as record B; deviation 3 extends it to a CNKI article page
as record A, both parsed in code. The code is `stage_s`, `cnki_entry` and `toc_entry` in
`build_keys.py`; the version before it is `git show origin/main:research/battery2/pipeline/build_keys.py`.

Run: `python3 -I pipeline/build_keys.py --workdir <dir> --seed-file pipeline/kimi/papers-2026-11-08-final.jsonl --target N`
(`--stage s` registers seeds only). Seeds: one paper per line with candidate source URLs
(`kimi/papers-2026-11-08-final.jsonl`, the owner's Kimi run, 2026-11-08; its open page ranges are in
`kimi/c98fa360-remaining-page-ranges.md`).

## Test 7-8 (2026-11-08, observed; workdirs `keys-pipeline-test7/8`, not committed)

- Seeded 10 (《周易研究》2016/2 only: the other three issues have no CNKI + CASS TOC pair in the seeds).
- Dropped in code: 2 author mismatches (陈业新 vs 陈亚新; CNKI lists translator 张悦, the TOC does not),
  3 recoverability failures, 1 clue leak (stage f).
- Opus verification, first pass (test 7): all 4 units flagged `not_primary`, because the verifier did not
  know deviation 2. After the verifier prompt names the exception (test 8, verification only, other stages
  cached): 3 accepted, 1 clue flagged `clue_leaks`.
- Result: **3 items from 10 candidates.** Spend $1.03 in total, of which the first Opus pass was wasted;
  the cost per item at scale is not measured by this test (Gap).
- Parser checks: each parser was run on a corrupted copy of its page (heading title changed; title absent)
  and refused the record (`field_unverified`, `toc_entry_absent`).
- Blind review (2026-11-08) blocking findings, fixed: seeds now take record A from CNKI only; `cnki_entry`
  takes only the first 相似文献 line and checks its year and issue against the URL's CNKI id (mutations:
  own line not first, later same-title line, wrong URL issue: all refused); deviation 3's heading now
  says tests 7-8 ran the same day.
- Not covered: a TOC whose author field has a page range or unusual separators; Latin-script names in a
  TOC (split on spaces); a translator marked 译 in the TOC matches CNKI without the mark (review
  findings 5-9, non-blocking, left as they are).
- Test 8 reused test 7's states with verification fields reset by hand; a stale `key_flagged` marker from
  that reset first dropped all four, which was the reset's fault, not the pipeline's.

## Run 1 (2026-11-09, observed; workdir `keys-pipeline-run1`, not committed)

- Seeds: `kimi/papers-2026-11-09-round2.jsonl` (Kimi round 2: 92 papers; new issues 《周易研究》2018/1-3 with
  CNKI pages and the `iwr.cass.cn` 2018 TOC). 75 seeded; 17 skipped (no CASS TOC URL, e.g. 中国哲学史 2018/4).
- First pass found 2 items: 36 candidates failed `toc_entry_absent` because the 2018 TOC writes entries as
  `title/authors` with `、` between authors and no page number. `toc_entry` now reads three formats:
  `title//authors（page）` (2016), `title/authors` (2018) and `title/author|author` (2019, as the Kimi app
  reported the page). Checks: real 2016 and 2018 pages parse; a synthetic 2019 line parses; an absent title
  gives `toc_entry_absent`; a line whose "author" is prose gives `toc_author_unparsed`.
- After the fix (only those 36 reprocessed, fetches cached): **10 items from 75 candidates, $1.54 in total**
  (writers: DeepSeek only). Remaining drops: 25 `unfetchable_source` (the `iwr.cssn.cn` TOCs for 2019/3 and
  2021/5: DeepSeek fetch fails there, while the Kimi app's fetch opened the page on 2026-11-09), 17 clue
  checks (stage f), 9 `toc_entry_absent` (6 of them notices or book blurbs with no author, correctly
  dropped), 5 clues flagged by the verifier, 4 CNKI records unverified (obituaries, notes), 3 recoverability,
  2 author mismatches.

## Run 1, continued, and run 2 (2026-11-09, observed; workdirs not committed)

- **Moonshot fallback.** `ds_fetch` retries a failed DeepSeek fetch through `api.moonshot.ai/v1/tools/fetch`
  for hosts in `MOONSHOT_FALLBACK_HOSTS` (`iwr.cssn.cn`); the snapshot records `fetcher: moonshot`. Both
  `iwr.cssn.cn` TOCs (2019, 2021) returned 200 through it, so the 25 blocked run-1 candidates reached the
  later stages; 2 still dropped `unfetchable_source`.
- **Verifier fault found and fixed.** Two Opus verify batches spent the whole 32k `max_tokens` on reasoning
  (effort "max") and returned no answer; 12 units were dropped `no_verdict` ($1.43 spent for nothing). The
  verify call now sets `reasoning.max_tokens` 16000 under `max_tokens` 32000, and a batch with an empty answer
  stays pending instead of being judged. Re-verified: $0.21, reasoning about 1k tokens per batch. Whether the
  shorter reasoning makes the verifier less strict is not measured (Gap).
- **Run 1 final: 21 items from 75 candidates, $3.17** (of which $1.43 was the lost batches).
- **Run 2 (self-seeded):** `seed_from_toc.py` on the 2019 and 2020 TOCs (`iwr.cass.cn` ids 5788115, 5788116)
  gave 138 seeds from about 150 entries (48 CNKI pages matched no entry: notices, columns, other issues).
  Pipeline: **52 items from 138 candidates, $1.14.** Drops: 52 clue checks (stage f), 20 clues flagged
  by the verifier (9 leaks, 9 misdescribe, 2 other fitting work), 7 off topic (pre-screen), 4 CNKI records
  unverified, 3 author mismatches. Writers: DeepSeek only; clue loss is now the largest drop.
- Yearly TOCs of 《周易研究》 2012-2024 sit at consecutive ids 5788108-5788120 on `iwr.cass.cn` (titles read
  2026-11-09), so further years need no new source.
- Blind review (2026-11-09), no blocking findings. Fixed: a Moonshot 401/402/429 now stops the run (InfraError) instead of caching the page as unfetchable. Left as they are (non-blocking): the TOC parser takes the year from the page header without checking the entry's issue section; failed fetches are cached and not retried; a batch with an empty verdict is paid again on each rerun (cap runs with --max-usd).

## Sonnet as second clue writer (2026-11-09, observed)

- Candidates that had died at the clue stage were reopened and re-run with `--writers deepseek,sonnet`
  (records and DeepSeek clues reused; an item drops only if every clue fails).
- Run 2's first 40 reruns used Sonnet at effort "max": 36 clues, 7.5k reasoning tokens and $0.078 each. With
  the writer's reasoning capped at 3k tokens (max_tokens 8k), run 1's reruns cost $0.19 for their Sonnet
  clues in total. Whether the cap lowers clue quality is not measured (Gap).
- Results: run 1 **21 → 28 items** (of 75; $3.74 in total); run 2 **52 → 73 items** (of 138; $5.15, stopped at
  the $5 cap with 9 candidates still open). **Total 101 items for $8.89.** Most spend is now Opus
  verification (run 1 $3.54, run 2 $1.89, including the $1.43 lost earlier). DeepSeek clue calls record $0
  because no DeepSeek prices were passed (`--ds-price-*`), so their cost is a Gap in these figures.

## Runs 3 and 4 (2026-11-09, observed; workdirs on `battery2-keys`, not committed here)

- **Run 3:** seeds from `seed_from_toc.py` on the 2017 and 2021-2024 TOCs (277 rows, built in session
  012mve9X). `--writers deepseek,sonnet --max-usd 6`. **133 items from 277 candidates, $4.34.** Drops: 53 clue
  checks (stage f), 25 author mismatches, 25 clues flagged by the verifier, 24 off topic (pre-screen), 17 CNKI
  records unverified; no `no_verdict` drops. Sonnet: 83 accepted clues for $0.96.
- **Run 3's author mismatches:** 20 of the 25 differ only in separators (the TOC runs the names together,
  CNKI splits them with `；`), counted by comparing the two fields with `；` removed. The other 5: two with
  translator or editor marks (撰, 译, 整理), one missing co-author, one name cut short, one character
  substituted. Accepting a TOC field that equals the CNKI names joined with no separator would likely
  recover the 20 (estimated from that count, not run); not done, because those items fall in the 2016+
  article/zh band, which is already over target (below).
- **Run 4:** `seed_from_toc.py` on the 2012-2016 and 2018 TOCs (ids 5788108-5788112, 5788114) gave 293 rows
  (154 CNKI pages matched no TOC entry). Only the 203 rows from 2012-2015 were run (2016 and 2018 left out:
  that band is over target). **106 items from 203 candidates, $3.54.** Drops: 33 clues flagged by the
  verifier, 27 clue checks, 14 off topic, 10 CNKI records unverified, 7 recoverability, 6 author mismatches.
- **Total after four runs: 340 item rows for $16.78, 333 distinct items** (DeepSeek clue calls still unpriced,
  so a Gap in the cost). 7 rows are the same article accepted twice: run 1 overlaps run 2 four times (2019)
  and run 3 three times (2021), because their seeds covered the same issues and runs do not check other
  workdirs. So the earlier "101 items" for runs 1-2 was a row count; 97 of them are distinct. Two rows count as
  one item when the key's title, author and year all match; one further pair shares a title but differs in
  author and year, so it is two items.

## Strata after run 4 (against `design/final-design.md` §B)

The design asks for 300 items: 60% articles / 40% books, 80% zh / 20% en, three date bands, and a
fame split. The 333 distinct items are **all article/zh, all fame `unknown`**: 227 from 2016 or later,
106 from 2000-2015. So the article/zh cell (144 of 300) is over target, and several cells have no items:

- books (zh and en), English articles, pre-2000: none. The current intake pairs a CNKI article page with
  the CASS yearly TOC of 《周易研究》 (2012-2024), so it yields only Chinese journal articles from those years; each needs its own record pair and design (issue #33, step 3).
- fame: no item carries a citation or holdings count from a primary record, so the fame split cannot be
  filled with this intake (Gap).

Which 300 to freeze from the article/zh surplus, and whether to build the other cells, is the owner's call.

## Two fetch APIs, one per record (PREREG deviation 4, 2026-11-09)

- `toc_entry` now fetches through `moonshot_fetch`; `cnki_entry` still fetches through `ds_fetch`. `stage_b` drops an
  item `same_fetcher` when both records' snapshots name one fetcher. A Moonshot snapshot is stored as `fm_<hash>.json`;
  a fallback snapshot Moonshot already made for the same URL is reused. Why: PREREG deviation 4.
- Checked (2026-11-09, live, one pair: CNKI `ZYJY201602002` with the 2016 table of contents, `iwr.cass.cn` id
  5788112): record A through DeepSeek, record B through Moonshot, authors equal. Mutation: with
  `toc_entry` put back on `ds_fetch` and a DeepSeek-shaped snapshot for the table of contents, the item drops
  `same_fetcher`. An old Moonshot fallback snapshot is reused without a second file.
- Items resumed from an earlier work directory (same day, state built from the live pair with a DeepSeek-shaped
  record B): equal entry gives `recB_reread: equal` and the Moonshot snapshot; a stored author changed by one
  character drops `reread_mismatch:author`; a cached Moonshot 502 gives `not_rechecked` and no drop; a second run
  changes nothing. Mutation: with the call to `reread_record_b` removed, the changed author is not dropped.
- A blind review (fresh agent, diff and a checkout of `main`) found that items with a saved record B skipped the rule
  (fixed by `reread_record_b`), an unlocked first fetch of a page shared by a year's items (now under a lock), and
  wording stronger than the evidence (corrected in PREREG).
- A second blind review (the code diff) found that a `not_rechecked` item still went on to be accepted (fixed: `held`
  stops it in `process`, `is_good` and `finalize`, and the report counts it), that a page Moonshot returns in a form
  the parser cannot read would have dropped the item (now held), and that the re-read compared more strictly than
  `stage_d` (now the same comparisons). Checked: a cached 502 and a header pushed past 600 characters both hold the
  item; mutation: with the hold removed from `is_good`, the held item counts as good.
- Known and left: after an equal re-read, `entryB`, `key_forms` and the verifier's verdict still come from the earlier
  snapshot (`replaced_snapshot_file`); a keyed item dropped by the re-read still blocks a later duplicate, as any
  drop after stage d does; the verifier's excerpt is cut from Moonshot's raw markdown (`**`, `\|`), while
  `toc_entry` parses it with those removed.
- Left as they are, all older than this change: `load_host_stats` and the report's "DeepSeek tool calls" line count
  Moonshot fetches too; a Moonshot auth or rate error stops one item, not the run (`process` catches `InfraError`
  per item), which the "now stops the run" line above overstates; `MOONSHOT_API_KEY` is not named in the module
  docstring.
- Not checked: the tables of contents of the other years through Moonshot, among them whether each keeps its header
  in the first 600 characters, which `toc_entry` needs; the real work directories (the re-read has run only on the
  constructed state above); a full pipeline run. `seed_from_toc.py` still reads the table of contents through
  `ds_fetch` with its fallback for `iwr.cssn.cn` only: seeds are candidates, never records.

## Record B read again through Moonshot: result (2026-11-09, after PR 35)

Run on the four stored work directories with `--stage b` (each with its own target and writers), on `main` at
55db1b0. The outcomes were fixed in PREREG deviation 4 before the run.

| Outcome | Items |
|---|---|
| Equal, kept with the Moonshot snapshot | 334 (325 accepted, 9 in progress) |
| Dropped | 1 (accepted, run 3: `toc_entry_absent`) |
| Held (`not_rechecked`) | 0 |
| Record B already through Moonshot, not re-read | 14 (accepted, run 1) |

- 13 table-of-contents pages (2012-2024) were fetched through Moonshot, each with status 200 and a readable header.
- Accepted items: 340 before, 339 after; distinct by title and author: 332.
- The dropped item: its title holds a rare character, and Moonshot's conversion breaks the line after it, so the
  title and the author sit on two lines and `toc_entry` finds no entry. DeepSeek's conversion kept the line whole.
  The page is the same; the two converters differ. Under the rule fixed in advance an absent entry drops, and the
  item is not repaired.
- What this shows about the converters: across 335 entries read through both, the parsed title, author, venue and
  year agreed on 334, and the one difference is a line break, not a changed character.
- Not checked: the snapshots were compared through `toc_entry`'s fields only, not page text against page text.

