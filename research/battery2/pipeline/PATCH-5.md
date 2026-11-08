# Patch 5: seeded intake from issue tables of contents

Why: tests 4-6 kept 1 item from 105 search-harvested candidates. Deviation 2 (PREREG) allows a
research institute's complete issue TOC as record B; deviation 3 extends it to a CNKI article page
as record A, both parsed in code. The code is `stage_s`, `cnki_entry` and `toc_entry` in
`build_keys.py`; `build_keys.v5pre.py` is the version before it.

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
- Not covered: a TOC whose author field has a page range or unusual separators; a CNKI page whose
  similar-works list does not start with the article itself (the parser then refuses, so it fails safe).
- Test 8 reused test 7's states with verification fields reset by hand; a stale `key_flagged` marker from
  that reset first dropped all four, which was the reset's fault, not the pipeline's.
