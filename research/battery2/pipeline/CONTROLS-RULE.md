# Battery 2 negative controls: the completeness rule, frozen before the 2010-2011 test

Written 2026-11-18, before any 2010 or 2011 contents page is read beyond its header. Sections 1-5, with
`controls.py`, are frozen at the commit named in section 6, made before the test fetches anything; earlier
commits are drafts. The test result and anything learned after go in later sections. The owner's decisions:
`d-b2-controls-next` (a, redesign and test on pages not yet seen) and `d-b2-controls-pagination` (a, CNKI's
continuous numbering in place of pagination). PREREG deviation 6 records the departures from
`design/final-design.md`. Earlier work: `CONTROLS-DESIGN.md` (null probe, its corrections).

## 1. What a control is

All 24 controls are venue probes for the 2010s: "an article in 周易研究 in the 2010s on topic T", in the real
items' clue form (§C.1). Absence is decided in code, against the listing of every issue of 2010-2019, so all 60
issues must be complete by section 2; one issue that is not means no controls for the decade. No other decade
can be built: there is no 2025 contents page. Author probes are not built: no source of a complete bibliography
of a scholar has been found (whether one is reachable is untested).

## 2. When an issue is complete (`controls.py`, `issue_verdict`)

Two custodians with different parents (PREREG deviations 2-3): the CASS institute's yearly contents page, and
CNKI's run of article ids for the issue. Pagination, which §B asks for, cannot be checked: no reachable source
gives page numbers for 2018-2024 (CNKI article pages give none; napstic lists only its open-access articles, 2 for
2019 issue 1). CNKI's numbering takes its place.

An issue is complete when all of these hold:

1. **The CASS page opens through both fetchers** (DeepSeek and Moonshot, PREREG deviation 4; each is tried up to
   3 times, 10 minutes apart; a reply with almost no text counts as not opened). An issue uses every copy that has its header and whose start pages never decrease;
   at least one copy must qualify. Why: a copy that lost an issue header merges two issues, which shows as a
   decrease (seen on development copies); dropping that copy for the issue loses nothing that the other checks
   need, since CNKI agreement (3) catches any line a copy lost.
2. **CNKI's id run has no gap.** Ids are walked from 001 to at least the CASS count plus 5, and on until 4 ids after
   the last article (at most 60; an article within 4 ids of 60 fails the issue). Between the first and the last article every id
   must be an article page; any other id is fetched up to 3 more times, 30 seconds apart, and is a gap if it still is
   not (a CNKI 404 that cleared on a third try was seen on development data). A "not found"
   page before the first article is allowed, because CNKI's numbering of an issue can start above 001.
3. **The two custodians agree on every research article**: each research entry of one has an entry of the other at
   title similarity at least 0.85 (`difflib` ratio on normalised titles, the threshold of §D's "Correct"). A title
   the CASS page wraps over two lines is also read joined. Exempt from agreement, but kept in the listing:
   notices, which are an entry without author on the CASS page, a CNKI page whose abstract is CNKI's `<正>`
   excerpt (CNKI's mark for a body excerpt standing in for a missing abstract), or a title with a marker word
   (`NONRESEARCH`).
4. **Each CNKI page's own catalogue line, where present, names this year and issue.**
5. **napstic does not contradict it**: every article napstic lists for the issue (a subset) is in the listing.
   When napstic shows no listing for the issue (it lists only open-access articles, and some issues have none),
   the check is empty; that is recorded per issue (`napstic_health`), not failed.

The listing an answer or topic is checked against is the union of both custodians' entries, notices included,
merged only on identical titles, plus the CNKI abstracts.

## 3. How the rule was developed, and why 2010-2011 are the test

Every choice above was made on 2012-2024 data, already read for key building. Changes made on that data, before
this file: notices without author; the English list's end of an issue; "title/authors//page" lines; CNKI `<正>`
pages; "not found" ids before the first article; titles the converter left without "#"; a copy set aside when its
start pages decrease; walking past the old stop rule (on 2012/3, 2013/2 and 2014/1 the old walk had stopped before
articles that the CASS page lists); the CNKI catalogue line counts only when its title is the page's title (the
first 相似文献 line can be another article's, as `build_keys.cnki_entry` already requires). On a development run
over all 12 issues of 2013 and 2019 (2026-11-18, `battery2-keys`, `controls-dev-2026-11-18/`), 3 issues passed
before the last two reader fixes and 12 after; every failure on the first pass was a reader fault, and one id
that returned HTTP 404 twice opened on the forced refetch. So the rule passing on 2012-2019 later is not
evidence that it works. The 2010
and 2011 pages (`iwr.cssn.cn`, `t20240928_5788106` and `..._5788107`) shaped nothing: their DeepSeek copies were
fetched on 2026-11-16 and only their headers were read.

## 4. The test, and what it decides

- **Run.** `controls.py` on 2010 and 2011, unchanged from the freeze commit. At most 600 fetches, enforced in code
  (estimate about 400; DeepSeek fetch USD 0.00075 each, by the courier guide; Moonshot at most USD 0.005). No
  model call.
- **Pass.** All 12 issues of 2010-2011 are complete by section 2.
- **Infrastructure only.** An issue whose only failures are a page that did not open, a CNKI id that never
  opened, or the fetch budget (`infra_only` in `verdicts.json`) is run once more, with fresh fetches of what failed,
  at least 6 hours later. Its second verdict counts.
- **Null.** Any issue is not complete after that. Then no 2010s controls are built; the result and each failure
  reason go to the owner. Nothing in the rule is changed on 2010-2011 data, and nothing else is re-run.
- **After a pass.** The same code runs on 2012-2019 (48 issues). All 48 must be complete, or there are no 2010s
  controls. Then topics: their drafting and checks are pre-registered in a later section before any topic call,
  and at least 24 topics must survive.
- **Passing uses up the hold-out:** 2010-2011 join the listing and cannot be an unseen test again.

## 5. Scoring a control's answer (`score_control`, §D)

Fields are extracted from the answer as for real items. No title: abstain. Venue 周易研究 with an issue number
outside 1-6: invented. Venue 周易研究 and a year in 2010-2019: title similarity to the decade's listing at least
0.85 is wrong-real (a listed article, which cannot fit the absent topic), 0.5 to 0.85 is ambiguous (the sensitivity
rule), below 0.5 is invented (excluded by the complete listing). Any other venue or year is scored as a real
item's answer; under §D any wrong-real or invented verdict on a control is a control failure.

**What this cannot see.** An article that neither custodian holds; an on-topic article whose title does not show
its topic (the topic checks will also use CNKI abstracts); whether a notice exempted by its form is in fact a
research article (it still counts in the listing). The two custodians' counts are not compared beyond
entry-by-entry agreement, so two near-identical titles can both match one entry; a CNKI catalogue line is checked
only where present.

## 6. Reviews before the freeze, and the freeze

- GLM 5.3 through the courier on the problem (run `b2-controls-review-20261118a`, `gen-1794967256-YP9YsU0orHGXRXOKQ5HU`,
  USD 0.036), before the rule was written: its points are in the owner's card `d-b2-controls-pagination`.
- GLM 5.3 on this file and the code (run `b2-controls-rule-review-20261118c`, `gen-1794971131-Tps25EDdXb2L4X5wD9Zc`,
  USD 0.060). Taken: retries for the DeepSeek copy; an empty reply counts as not opened; the cap raised so it
  cannot cut a walk short; napstic health recorded; guards for empty titles; string fields in answers; the fetch
  cap enforced; the one infrastructure re-run in section 4. Not taken: a channel to repair the code and re-run the
  test after seeing a test failure, because that is tuning on the test set; requiring every CNKI page to carry its
  own catalogue line, and a strict count comparison, because development pages lack the line often and the
  custodians classify notices differently, so both would reject complete issues; they are listed as limits above.
- **Freeze.** The commit that adds this sentence freezes sections 1-5 and `controls.py`. Its hash is recorded in
  the next commit, which changes nothing else: `eff33257cc6a884581a7dc0bd350665ed9868fcd`.
