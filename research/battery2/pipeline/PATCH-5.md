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
