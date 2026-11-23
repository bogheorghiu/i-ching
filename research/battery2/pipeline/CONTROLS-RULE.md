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

## 7. Result (2026-11-18): null, 8 of 12 issues complete

**The run.** `controls.py` at the freeze commit on 2010 and 2011: 284 fetches in all (2 through Moonshot, the
rest DeepSeek; under USD 0.25). A container restart stopped the run after 2010/3; it was resumed with the same
code and workdir, so pages already saved were reused and 2010/1-3 were recomputed from the same snapshots. No
model call. Files: `battery2-keys`, `controls-test-2010-2011/`.

| Issue | Verdict | Failure |
|---|---|---|
| 2010/1, 2010/4, 2011/1-6 | complete | |
| 2010/2 | not complete | 1 CNKI page not on the CASS page |
| 2010/3 | not complete | 1 CNKI page not on the CASS page |
| 2010/5 | not complete | 2 CNKI pages not on the CASS page |
| 2010/6 | not complete | 2 CNKI pages not on the CASS page; 1 CASS entry not in CNKI |

None of the four is an infrastructure failure, so section 4's one re-run does not apply. **By section 4 this is a
null: no 2010s controls are built.** Nothing in the rule or the code was changed after the freeze.

**What the failures are** (read after the result; changes nothing above):
- The 6 CNKI-only pages are book notices and news items (a new book, an appointment of the journal's editor).
  Their CNKI pages have an empty abstract. Section 2 exempts a CNKI page as a notice only when its abstract is
  CNKI's `<正>` excerpt, so under the rule as written they count as research articles that the CASS page lacks.
  The code also meant to treat an empty abstract as a notice, but its abstract pattern reads the next section
  heading (`【引证文献】`) as the abstract, so that branch never fires on this page layout. Rule text and code agree
  on these six pages; the code's intent and its effect do not.
- The CASS-only entry in 2010/6 is a foreword to a book (`序《墨经正读》`). No page in CNKI's run for that issue holds
  it. That is a real disagreement between the custodians, and it would fail the issue even if the six notices
  were exempt.

**What this does and does not show.** The rule's notion of a notice was too narrow for 2010's CNKI pages, which
the development years did not show (their notices carried `<正>` excerpts). It does not show that the CASS
pages or CNKI miss research articles: apart from the foreword, every disagreement is a notice. The 2-control-failure
gate of §E cannot be applied (PREREG deviation 6). The next step is the owner's (board card
`d-b2-controls-null`).

## 8. Amendment after the null (2026-11-21): wider notices, a re-run that is not blind

Written 2026-11-21, after the result in section 7 and before the re-run fetches anything. The owner chose option a of
board card `d-b2-controls-null`. Sections 1-7 are not edited. This section, section 9 and the amended `controls.py`
are frozen at the commit named in section 9; earlier commits are drafts. PREREG deviation 7 records the departure from
deviation 6.

**What changes in `controls.py`.**

1. *A CNKI page with an empty abstract counts as a notice.* Section 2 point 3 exempts a CNKI page from agreement only
   when its abstract is CNKI's `<正>` excerpt. The code meant to exempt a page without an abstract as well, and did for
   a page with no `【摘要】` line; but when the line is there and empty, its pattern ran on to the next heading
   (`【引证文献】`) and read that as the abstract (section 7). An abstract that begins with `【` is now read as empty.
2. *A foreword is a notice, on either custodian's page:* a title that begins with 序 and then, with nothing but
   spaces between, a book-title mark (《 or 〈), like the CASS entry of section 7. The pattern is this narrow because
   序 also occurs inside research titles (卦序, 序卦), and a marker word would take those out of the agreement check.
3. *The fetch cap is 1,500.* Section 4's 600 was for two years.
4. *The verdict lists what the two exemptions waived:* per issue, the exempt entries (a CNKI page with no abstract,
   whether its `【摘要】` line is empty or missing; a foreword) that the other custodian does not hold
   (`waived_unmatched`, its count also in `counts`; a title that the CASS page wraps over two lines is shown joined).
   An entry exempt only by a marker word, by `<正>` or by a missing CASS author is not listed: those exemptions are
   section 2's, and section 7's test ran with them. The list is there to be read, so that a pass can be checked for a
   hidden gap in the two new exemptions.

An exempt entry stays in the listing that answers and topics are checked against; only the agreement check skips it.
Everything else in section 2 is unchanged: both fetchers, the id run and its retries, the 0.85 similarity, the
catalogue line, napstic.

**Why, and what a pass would be.**

- Section 7 reads the seven disagreements of the failed issues as six notices (CNKI pages with an empty abstract) and
  one foreword. That reading was made after the result, by the session that ran the test; this section does not
  re-verify it.
- An empty abstract is not proof of a notice. On the saved 2010-2011 pages 15 CNKI pages have an empty abstract. Eight
  are not on the CASS page and are, by their titles, book notices or news items (two of them were already exempt by a
  marker word). Seven are on the CASS page: five are conference speeches, reports or notices, two are plain research
  articles. On 2013 and 2019 one page has an empty abstract, a research article that is on the CASS page. Over all the
  saved CNKI pages of 2010-2019 (826 article pages from earlier runs, chosen for other purposes, so not a rate) the
  heading followed directly by `【引证文献】` occurs on 14 pages, all of 2010, and ten pages of 2011-2019 have no `【摘要】`
  line at all, which the frozen code already took as a notice; by their titles six of those ten are research articles.
  So the exemption could also hide a research article that only CNKI holds. (Read offline from the saved pages on
  2026-11-22, nothing fetched; the classes are the writer's reading of titles, not code's.)
- This is not a blind test. The exemptions were written after reading the 2010-2011 results, which are the cases they
  were written to fix, and the 2012-2019 pages were read for key building and for developing the rule (section 3), so
  no issue of 2010-2019 is unseen. The 12 issues of 2010-2011 passing again would show that the code does what this
  section says, not that the rule is right. For 2012-2019 the amendment can change a verdict only where a page has an
  empty abstract or a foreword title; the frozen code passed the 12 development issues of 2013 and 2019 after the
  reader fixes of section 3.
- A pass would show that under this rule the two custodians agree on every entry that is not exempt, in all 60
  issues. That is weaker than a pass of section 4's bar: an exempt entry is no longer held against the other
  custodian. A research article with an empty CNKI abstract that the CASS page lacks (or one with a foreword title that
  the other custodian lacks) would no longer raise the warning that a custodian misses articles. It would still be in
  the listing, so no answer is scored invented against a listing that lacks it; what is lost is the warning, not the
  entry.
- Not checked before writing this: how many pages of 2012-2019 have no abstract or a foreword title, and how many of
  them only one custodian holds (the lists of change 4 report that after the run). Checked on the ten CASS pages of
  2010-2019, all saved, nothing fetched (2026-11-22): three entries have a preface shape (`序《…》`, `…前言`, `…总序`);
  one is the foreword of section 7, and the other two (2010/1, 2013/5) have CNKI pages and were complete in the earlier
  runs. The CNKI side of 2012-2019 is not enumerated. Whether a title that looks like a notice is one is a reading of
  the title, not a check (Gap).

**The re-run and its bar.**

- *Run.* `controls.py` as frozen in section 9, on all 60 issues of 2010-2019, in one invocation with a `--year` and a
  `--cass` for each year. The CASS pages are `t20240928_5788106.shtml` (2010) to `t20240928_5788115.shtml` (2019) under
  `/qknj/zhouyi/mulu/202409/`, as `http://iwr.cssn.cn/…` for 2010-2011 and `http://iwr.cass.cn/…` for 2012-2019; a saved
  page is reused only under the same URL string. The pages saved by the test run (2010-2011) and the development run
  (2013, 2019) are copied into the new work directory first and reused as `fetch` reuses any stored 200 reply; every
  other page is fetched. For the 12 issues of 2010-2011 the amended rule is then the only difference from section 7.
  Those 12 and the 12 of 2013 and 2019 are judged on pages saved on 2026-11-18, not fetched again; the report says so.
- *Budget.* At most 1,500 fetches in one invocation of the program, enforced in code. Estimate: about 850 with the saved
  pages and about 1,400 without (the test took 284 fetches for 12 issues); the owner's card allowed about 1,200 and about
  USD 1 (DeepSeek fetch USD 0.00075 each by the courier guide, Moonshot at most USD 0.005). The cap counts one
  invocation; a resumed run (a restart, or section 4's one infrastructure re-run, which counts the fetch budget as an
  infrastructure failure) has its own cap, and the total over all of them is read from `snapshots/index.jsonl` and
  reported. No model call.
- *Pass.* All 60 issues are complete by section 2 as amended here, which is a certification without a blind test.
- *Reading the waived entries.* The report reads each entry of `waived_unmatched` by its title and says which are book
  notices, news or plates and which look like research articles (a reading by the session that ran the check, not
  blind). The verdict of this section is the code's, but the topics stage does not start until the owner has ruled on
  every entry read as a research article, as one of two: *notice* (the reason is recorded; the issue stays complete) or
  *research article* (the issue is not complete, and the null paragraph below applies). Why: an exempt entry that the
  other custodian lacks is the case where one custodian may be missing an article, and the code no longer warns of it.
- *Infrastructure only.* As in section 4: an issue whose only failures are infrastructure is run once more, with fresh
  fetches of what failed, at least 6 hours later; its second verdict counts.
- *Null.* Any issue not complete after that: no 2010s controls are built, the result and every failure reason go to the
  owner, and the rule is not widened again on these data. A different rule would be a new amendment: the owner's
  decision, written before it runs, with its result reported next to this one and not as a pass of this section. This
  amendment is the only one made after reading the result of section 7.
- *After a pass.* Topics as in section 4 (pre-registered in a later section before any topic call; at least 24 must
  survive), then the 2-control-failure gate of §E as pre-registered. Every statement that rests on this listing says
  that it was certified without a blind test.
- *Both results are reported.* Section 7 (a null, from a blind test) is not replaced by this one (labelled not blind).

## 9. Review of the amendment, and the freeze

- GLM 5.3 through the courier, on section 8, PREREG deviation 7 and the diff of `controls.py` (run
  `b2-controls-amend-review-20261122a`, `gen-1795313456-VPOBYqQ4lbs3uFfeU9Lp`, USD 0.040). It could not see the CASS
  parser, `best` or the merge code, so its points were checked here against those and against the saved pages. The
  order that ran held two context lines of the code excerpt in other words than the file (a comment, a docstring
  wrap); no point rests on them.
- **Taken.** Point 2 now says what its pattern allows (spaces between 序 and the mark). Point 4 now says that the list
  covers the two new exemptions only: it had promised a check for hidden gaps that it cannot give for the exemptions
  of section 2. A title the CASS page wraps is shown joined in `waived_unmatched`, because its `forms[0]` is only the
  second line. PREREG deviation 7 says that the pattern is kept and an abstract that begins with a heading is read as
  empty. The run is one invocation, so the cap is one cap, and the pass carries its label in its own sentence. An
  entry read as a research article now stops the topics stage until the owner has ruled, and each ruling is written
  down before the run: the review found that the doubt, as first written, could not change anything. A different rule
  is a new amendment and not a pass of this section.
- **Not taken, and why.**
  - *List the exemptions of section 2 as well.* Section 7's test ran with them and the amendment does not widen them;
    the hole is real and not new. Point 4 says so.
  - *A cut-off page becomes a notice.* A page with neither `【摘要】` nor `【引证文献】` is `not_found`, which between
    the first and the last article is a gap that fails the issue; a reply with almost no text is a failed fetch.
  - *Other spellings of the heading, or a structured abstract that begins with `【`.* None among the 826 saved article
    pages of 2010-2019; all 14 empty headings are followed by `【引证文献】`. A new layout would turn CNKI pages into
    notices, but every CASS research entry still needs a CNKI entry (a notice can be that entry), and the CNKI-only
    pages would fill `waived_unmatched`, so it would show.
  - *An abstract on the line below the heading reads as empty.* It does not: the pattern's `\s*` spans the line
    break, and a synthetic page tests it.
  - *The foreword pattern misses 跋, 后记, 前言, 代序, a leading quotation mark, a title that ends with the word.* The
    owner chose the foreword of section 7. Of the three preface shapes on the ten saved CASS pages the other two were
    complete in the earlier runs (section 8, "Not checked"); a wider pattern would be written on shapes not seen on
    the pages to be judged. If a paratext that only CNKI holds fails an issue, that is a null, and a wider rule is a
    new amendment.
  - *`foreword` reads every form, `NONRESEARCH` only the first.* The joined reading of a wrapped CASS title is the only
    place its first line lives: the foreword of section 7 is the second line of its entry. The first-form test is
    section 2's and unchanged.
  - *The fetch budget counted as an infrastructure failure is a route to a pass.* It is section 4's registered rule,
    and a resumed run is judged by the same rule on every issue. It is a route to a larger bill, which the total in
    `index.jsonl` reports.
  - *Section 2 and the code now differ.* Point 1 says so; sections 1-7 are not edited.
- **Freeze.** The commit that adds this sentence freezes section 8, this section and the amended `controls.py`. Its
  hash is recorded in the next commit, which changes nothing else: `0f48a50bad012cadefb71fe7d1364bbfda631f4e`.

## 10. Notes after the freeze, written while the re-run was in progress

Written 2026-11-22 after the freeze (section 9) and after the first 16 of the 60 verdicts were printed: 15 complete,
2012/2 not complete (no usable CASS copy). Nothing frozen is edited: section 8, section 9 and `controls.py` are as at
the freeze commit (`git diff 0f48a50 HEAD -- research/battery2/pipeline/controls.py` is empty). This commit adds this
section and `pipeline/check_controls_amendment.py`, the synthetic checks that section 9 cites: 14 checks of the
amendment, which pass 14 of 14 on the frozen code and 7 of 14 on the code of `eff3325`. The rejection checks of
section 11 were added to the same file in a later commit.

- **A second review.** A fresh agent on Anthropic's side, given only the diff and the three changed files (no
  repository, no history, no result) and asked what could be wrong, raised twelve points. The code points are true
  and stay, because the code is frozen: a run that reaches the cap stops with a KeyError after writing that issue's
  verdict (noticed in section 8); an invocation judges every issue of a year again and forces a fresh fetch of any
  non-article id inside a CNKI run, so a later invocation can turn a gap that was not infrastructure into a pass. The
  rules below meet both without changing code. The other points are words in section 9 that are not exact; they are
  corrected below.
- **Which verdict counts.** The first verdict written for an issue counts, unless every failure in it was
  infrastructure (`infra_only`): then the verdict of the one infrastructure re-run counts (section 8). A resumed run,
  after a restart or the cap, is an invocation after the first in this sense. The first verdicts are kept: `verdicts.json`
  is copied before each later invocation, and each invocation's printed lines are kept.
- **Saved pages.** "Judged on pages saved on 2026-11-18, not fetched again" (section 8) states an intent. The code
  fetches again a saved page that is not a readable 200 reply, a non-article id inside a CNKI run, and any URL not saved
  under the same string. The report counts the fetches that were made for the 24 issues and says which; the 12 issues
  of 2010-2011 were completed with no fetch.
- **Budget.** The cap is 1,500 for one invocation, against the card's "about 1,200". The report gives the total over
  all invocations from `index.jsonl` (the saved pages were copied without their index, so it counts this re-run, one
  probe fetch included) and its cost.
- **The owner's ruling.** Section 9's "each ruling is written down before the run" means the two possible rulings and
  what each does (section 8, "Reading the waived entries"); the rulings themselves come after. A ruling can only make
  an issue stricter: the code already leaves an issue with exempt entries complete, so *notice* changes nothing and
  *research article* makes the issue not complete. The reading of titles is by the session that ran the check, not
  blind. If the run passes, the owner gets the whole list of waived entries and not only those read as research
  articles, and a second reader that is not this session (anonymised, through the courier) reads the titles too; an
  entry on which the two readings differ goes to the owner as one read as a research article.
- **Words in section 9 that are not exact.** (1) "PREREG deviation 7 says that the pattern is kept": deviation 7 says
  that an abstract that begins with a section heading is read as empty; the code is as section 8 point 1 says, any
  abstract whose first character is `【`. (2) "The list covers the two new exemptions only": it covers an entry exempt for
  having no abstract (an empty `【摘要】` line, which is new; a missing line, which the frozen code already exempted
  and section 2 does not name) and forewords; section 8 point 4 is the exact statement. (3) "A wider pattern would be
  written on shapes not seen on the pages to be judged": the CASS pages were seen. The pattern stays narrow because the
  two other preface shapes have CNKI pages and their issues were complete without any exemption; what is not
  enumerated is the CNKI side. (4) "The run is one invocation, so the cap is one cap": one cap for that invocation.
  (5) Dates: section 8 and deviation 7 were first written on 2026-11-21 and amended on 2026-11-22 before the freeze
  (2026-11-22T02:26:30Z); the counts dated 2026-11-22 belong to that amendment, and "Not checked before writing this"
  in deviation 7 is as of its first writing.
- **The foreword test on a joined title.** A joined CASS reading can in principle start with a line that belongs to
  another entry. On the ten saved CASS pages (38 copies) the test fires on exactly one entry, 2010/6.
- **A squash merge.** It removes `0f48a50` from the history of `main`; the commit stays reachable as
  `refs/pull/49/head`, and the frozen code is identified by its content: `controls.py` is git blob
  `61e86d869ce8dcc18f943b46c4f2e88c5d888f15` (`git hash-object`), sha256
  `243105a0c39d4333f94ffd7de2432f433154e00e0df1b3e27a0f2b2e02afd8d7`, and that is the file the run executed.

## 11. Notes from the blind review of PR 48, written while the re-run was in progress

A second fresh agent on Anthropic's side was given the diff of PR 48 (sections 1-7, `controls.py` at its freeze, the
test result), the three changed files and an export of `main`, no history and no results, and asked what could be
wrong. It raised fourteen points. The code is frozen, so none of them changes it. What each led to:

- **Mutations.** It was right that nothing shown so far made the rule reject an incomplete issue; the checks only
  showed that it did not reject a complete one. Nine checks in `pipeline/check_controls_amendment.py` now do that: one
  control, an issue that passes, and eight that each break one thing in it (a CNKI page missing, a CASS entry missing,
  a gap in the ids, an id that does not open, no CASS copy that carries the issue, a copy whose start pages decrease,
  a napstic title not in the listing, a different title in place of one) and require the verdict to name it. They pass
  9 of 9 on the frozen code and on the code of `eff3325`. Four mutants of the code were each caught, counted over all
  23 checks: agreement off (`unmatched` returns nothing; 5 fail, 3 of these nine and 2 of the 14 of section 10), gap
  check off (1), napstic check off (1), and the failure for an issue that no CASS copy serves removed (2). Section 14
  lists the mutants that are not caught.
- **Numbers from the saved pages** (2026-11-22, offline). A title with a marker word (`NONRESEARCH`) is exempt from
  agreement. Of 718 CASS entries with an author in 2010-2019, 25 are exempt only by that word (研讨会 9, 综述 7, 目录 5,
  新书架 2, 简介 1, 论坛 1), and a literature review (综述) is a research article; they stay in the listing. A CNKI
  abstract is one line: of 655 pages with one, 17 have a line after it before the next heading, and that line is the
  interface text `下载App查看全文`; the first line has a median of 128 characters. The "284 fetches" of section 7 is the
  line count of the test run's `snapshots/index.jsonl`.
- **Limits of the registered rule that stay.** (1) Ids after the last article are not retried or reported: if the
  last article's page does not open, the CNKI side loses it without a failure, and only the CASS side can still
  catch it; a `not_found` id before the first article is allowed without a retry. (2) A run that reaches the cap
  stops with a KeyError (section 8), and `http_post` raises `InfraError` after three connection failures, which
  `controls.py` does not catch; either stops the run, and a resumed run is an invocation after the first (section 10).
  (3) `score_control` leaves an issue given as "第3期" a string and scores it as an impossible issue, so as invented:
  the extractor's output format matters and is not in this change. (4) CNKI is fetched through DeepSeek only, the CASS
  page through both fetchers. (5) The CASS start pages are read and used only to set a copy aside, not as the
  pagination check of §B. (6) The claims of sections 2 and 3 about live services (CNKI gives no page numbers; what
  napstic lists) are dated 2026-11-16 to 2026-11-18 and carry no evidence tag; they were not checked again (Gap).
- **The first freeze.** A squash merge removes `eff3325` from the history of `main`; it stays reachable as
  `refs/pull/48/head`. `controls.py` as frozen there is git blob `7ab077990f9139495b48ed61c647eb232ef8ae72`, sha256
  `5fd259f935cef683510dd45ff9a4530fab4ef1ce260a8b73dca3e72a2f9079cf`, and the head of PR 48 holds the same file.

## 12. Result of the re-run (2026-11-22): null, 51 of 60 issues complete (not blind)

**The run.** `controls.py` as frozen in section 9 (git blob `61e86d869ce8dcc18f943b46c4f2e88c5d888f15`), one
invocation over all 60 issues of 2010-2019, from 02:29Z to 03:52Z, no restart, no model call. 713 fetches (707 DeepSeek,
6 Moonshot; one of them, a probe of the CASS 2012 page that timed out, was made just before the launch; 21 URLs were
fetched more than once), at most USD 0.56, under the cap of 1,500 and the card's "about 1,200" and "about USD 1". The
24 issues of 2010-2011, 2013 and 2019 were judged on pages saved on 2026-11-18 with no fetch at all; all 713 fetches went
to 2012 and 2014-2018. Files: `battery2-keys`, `controls-2010s-20261122/` (verdicts, saved pages, and `analysis/` with
the scripts and outputs behind the numbers below). The numbers are GROUNDED in the run's own record (`verdicts.json`,
`snapshots/index.jsonl`).

| Issue | Verdict | Failure |
|---|---|---|
| the other 51 | complete | |
| 2012/2, 2012/5 | not complete | no usable CASS copy; 12 and 13 CNKI pages not on the CASS page |
| 2014/4, 2014/6 | not complete | a CNKI page's catalogue line names another year and issue |
| 2015/6, 2016/1 | not complete | 1 napstic title not in the listing |
| 2016/6, 2018/1 | not complete | a CNKI id between two articles that is not an article (a gap) |
| 2017/5 | not complete | 2 CNKI research pages not on the CASS page |

None of the nine is an infrastructure failure, so section 8's one re-run does not apply. **By section 8 this is a
null: no 2010s controls are built.** Nothing in the rule or the code was changed after the freeze, and no invocation
came after the first, so `verdicts.json` holds the first verdicts (section 10). Section 7 (a null from a blind test)
stands next to this one (a null from a test that was not blind).

**What the failures are** (read after the result; changes nothing above; GROUNDED means read from the saved pages,
offline, on 2026-11-22):
- *2012/2, 2012/5 (the reader).* The CASS 2012 page lists the headers of issues 5, 2 and 1 one after another and then
  one block of entries; the reader files that block under issue 1, the last of the three. The blocks of issues 2 and 5
  come later with no header of their own, after an English list that sets the issue being read to none, so
  `cass_issues` skips them (it reads entries only under a header). Matched against CNKI's titles, the page's six
  blocks fall, in page order, on issues 6, 1, 2, 3, 4 and 5, each on one issue only (13 of 14, 12 of 12, 12 of 12,
  12 of 12, 14 of 14 and 15 of 15 entries match): the entries are on the page, under the wrong header or none. The
  copies of 2026-11-09 parse the same way, in both fetchers. GROUNDED; on 2026-11-23 the frozen `cass_issues` was run
  again on both saved copies: it reads the headers in the order 6; 5, 2, 1; 3; 4 and files 14, 13, 12 and 14 entries
  under issues 6, 1, 3 and 4 and none under 2 and 5.
- *2014/4, 2014/6 (the reader).* Both are plates (id 001) whose title is also the title of an article in another
  journal (2018, 2020). The code takes the first line of CNKI's "similar documents" list that has the page's title as the
  page's own catalogue line, without checking the journal. 2 of the 849 saved CNKI pages of 2010-2019 with such a line
  show it. GROUNDED.
- *2015/6, 2016/1 (the rule).* napstic lists the news column 信息动态 as an article. It is in neither custodian's
  listing, and the napstic check has no exemption for notices. GROUNDED.
- *2016/6, 2018/1 (CNKI's numbering).* Id 011 of 2016/6 and id 012 of 2018/1 return CNKI's frame page on four tries,
  between two articles. In both issues every CASS research entry matches a CNKI page, so no listed article is behind the
  hole. Whether CNKI ever held an article there is UNRESOLVED.
- *2017/5 (a disagreement of the custodians).* CNKI ids 009 and 010 are research articles that the CASS page lacks in
  both fetched copies: their title words occur nowhere on the page, and its start pages for issue 5 jump from 53 to 81.
  The union listing holds them. Whether the source page lacks them or both converters drop them is UNRESOLVED; a third
  source would settle it (Gap).

**The exempt entries.** 13 entries were exempt by section 8 and are not held by the other custodian: 9 in 2010, 1 each
in 2014 and 2016, 2 in 2018 (counted from the `waived_unmatched` of `verdicts.json`, 2026-11-23). By their titles all
13 are news, book notices, plates or a foreword; none looks like a research article (a reading by the session that ran
the check, not blind). No ruling of the owner is open under section 8. The titles are in the private results.

**What this does and does not show.** Six of the nine failures (2012/2, 2012/5, 2014/4, 2014/6, 2015/6, 2016/1) are
faults of the reader or the rule on pages whose entries agree; two are holes in CNKI's numbering (2016/6, 2018/1); one is
a real disagreement between the custodians (2017/5). The amendment of section 8 did what it was written for: the 12
issues of 2010-2011 passed, with no fetch. The 36 issues of 2012 and 2014-2018, on which it was not written and which
the development on 2013 and 2019 did not cover (they were read before, for key building and for the rule of section 3,
so none is unseen), show five kinds of failure (the five lines above), 9 issues in all. The
napstic check was not empty in 18 of the 60 issues (86 titles); in the other 42 it was empty, or its page 1 was not read.
Under the pre-registered consequence nothing is built from this listing; what to do next is the owner's decision (board
card `d-b2-controls-after-rerun`).

## 13. After the result: GitHub rebased this branch (2026-11-22, 23:58Z)

PR 48 was squash-merged at 23:58Z (`e454285` on `main`). Eight seconds after the merge request was accepted, GitHub
rebased this branch onto it and force-pushed it (head `eea2a24` to `59d4d39`; the PR's timeline, `issues/49/timeline`,
shows the event `head_ref_force_pushed` at 23:58:37Z under the bot account, the rebased commits' committer is GitHub,
and no session ran a push). Section 10 ("A squash merge") says the freeze commit stays reachable as
`refs/pull/49/head`. After the rebase it does not, so that sentence no longer holds. Sections 9 and 10 are not edited;
this section is the correction.

- **The content is the same.** Eight commits, in the same order, with the same messages and author dates. The trees of
  the old and the new head differ by three files that `main` gained in between (`research/battery2/RERUN-PROTOCOL.md`
  and, in `research/battery2/pipeline/`, `CONTROLS-DESIGN.md` and `VERIFIER2-TRIAL.md`), and so do the trees of
  `0f48a50` and `69cb2cb` (`git diff --name-status`, 2026-11-23). No earlier section, no `controls.py` (git blob
  `61e86d869ce8dcc18f943b46c4f2e88c5d888f15`) and no check file changed. GROUNDED.
- **The hashes, old to new.** The freeze `0f48a50` to `69cb2cb`; the commit that records its hash, `794d0da`, to
  `ea028c7`; the three drafts of the amendment `0101192`, `c6bbde8`, `1f9707c` to `7c21a59`, `8db5e7b`, `5003ad7`; then
  `c42845e`, `caf131c`, `eea2a24` to `d83d8b3`, `4235f12`, `59d4d39`. Sections 9 and 10 name the old freeze commit
  (section 12 names only the blob, which did not change); only the new hashes are on a branch. GitHub still served
  `0f48a50` by its hash on 2026-11-23, which is no promise for later. After the squash merge the new ones should stay
  reachable as `refs/pull/49/head`, as `eff3325` does as `refs/pull/48/head` (last bullet); that cannot be checked
  before the merge.
- **The freeze came before the first fetch.** The author date of `0f48a50` (02:26:30Z) is the committer's own word.
  GitHub's clock agrees: it created the check suites of `0f48a50` at 02:26:32Z and those of `794d0da` at 02:26:45Z
  (`commits/<hash>/check-suites`, read 2026-11-23). The first of the 713 fetch rows of `snapshots/index.jsonl` (the
  run's own record) is 02:29:13Z: the probe of the CASS 2012 page of section 12, a 504 with no content, 17 seconds
  before the launch at 02:29:30Z (private `run.meta.txt`); the next row, at 02:30:50Z, fetches the same page again.
  GROUNDED.
- **Section 11's claim about the first freeze still holds.** `eff3325` is an ancestor of `refs/pull/48/head`
  (`git merge-base --is-ancestor`, 2026-11-23). GROUNDED.

## 14. Notes from the final blind review of this PR (2026-11-23)

A fresh agent (asked for Opus; the model field of its transcript reads `claude-opus-5-5` on all 18 entries that carry
one) was given the diff against `main`, the four changed files and an export of `main`, with no history, no results, no
PR body and no web, and asked what is wrong with the pull request. What would block the merge was written down before
its report was read: a false or unsupported statement of fact in the changed files, a change to registered or frozen
text, or a check that passes without testing what it names (PR body). It raised 14 points. It found no line removed
from either document and no change to registered or frozen text other than `controls.py`, which deviation 7 declares.
Each point was checked against the files, not taken on its word:

1. **Fixed.** Section 11 counted nine checks that "break one thing"; one of the nine is the control.
2. **Fixed.** Section 11's mutant counts are now over all 23 checks (agreement off fails 5, not 3), and say which mutant
   is meant. Turning the page-order rule off instead fails 1.
3. **Kept as limits, no check added.** Seven mutants of `controls.py` pass all 23 checks (each run again on
   2026-11-23): the foreword pattern unanchored; the foreword pattern without 〈; `waived()` listing every notice,
   `<正>` pages included; the abstract test narrowed to `【引证文献】`; `foreword()` reading only the first form;
   the catalogue-issue check off; the cap back at 600. The repository's rule is to find out whether the check is weak or
   another layer covers the case, and to write it down. Here the checks are weak: the rejection group covers eight
   breakages, not every way the rule rejects (no case for the catalogue line, `cnki_cap_reached` or `cnki_run_empty`).
   The real run did use the catalogue-issue check (2014/4 and 2014/6 fail by it), and the code that ran is identified
   by its blob (section 10). The code is frozen and the run is done, so a check added now would test a file nothing
   will change; a second amendment (card option c) would write its own.
4. **Not an error; clarified.** Section 9 gives "the foreword of section 7 is the second line of its entry" as the
   reason `foreword` reads every form. That explains reading the second line (`forms[0]`). The joined reading is there
   for a foreword whose title starts on the first line of a wrapped entry. On the ten saved CASS pages (both copies)
   `foreword` fires on one entry only, 2010/6; `forms[0]` matches it and the joined form does not, so no saved page
   needs the joined reading, and no check does either. Section 9 is registered and stays.
5. **Fixed.** Section 13 said section 12 names old hashes; only sections 9 and 10 do.
6. **Pointer added.** Deviation 7 says "the commit named in section 9", which is on no branch after the rebase. A note
   at its end points to section 13; the registered text is not edited.
7. **Fixed.** Sections 12 and 13 read as if the probe fetch were part of the run; section 13 now says what it was.
8. **Fixed.** Section 12 pointed to a "replay of section 8" that section 8 does not contain. The 13 are counted from
   `verdicts.json`.
9. **Checked, and fixed in part.** The explanation of 2012/2 and 2012/5 does follow from the code: the frozen
   `cass_issues` was run again on both saved copies, and section 12 now gives the mechanism. The same check found that
   "every entry matches" was wrong for the first block (13 of 14 match); fixed.
10. **Fixed.** Section 12 now says that the 36 issues were read before, so none is unseen.
11. **Not changed.** Deviation 7's "Not checked before writing this" mixes two dates. It is registered text, and section
    10 point 5 already says it is as of its first writing.
12. **Nothing to change.** `controls.py` was edited after section 6's freeze: deviation 7 and section 8 declare it, and
    section 11 gives the old blob. Section 9 cites synthetic checks that were committed after the freeze: section 10
    says so.
13. **Partly fixed.** The numbers of section 12 rest on private results, which stay private by the owner's rule.
    Section 13 now names the GitHub calls that show its facts.
14. **Fixed.** The path of `RERUN-PROTOCOL.md` in section 13, and the usage note of the check file. The KeyError after
    `BudgetSpent` is disclosed in sections 10 and 11.

## 15. Building the controls on the combined list (option b), written before any topic call

Written 2026-11-23, after the null of section 12, before any topic is drafted, checked or searched. The owner chose
option b of board card `d-b2-controls-after-rerun` and, in the same chat, confirmed that it overrides deviation 7's "no
controls are built" (PREREG deviation 8). Sections 1-14 are not edited. Terms: a *control* is a trick question of
section 1; a *flagged issue* is one of the 9 not complete in section 12 (2012/2, 2012/5, 2014/4, 2014/6, 2015/6,
2016/1, 2016/6, 2017/5, 2018/1); a *candidate* is a drafted topic not yet checked; to *drop* is to remove a candidate.
No check here can add or approve one.

### 15.1 The listing

1. The listing is what `verdicts.json` of the re-run (`battery2-keys`, `controls-2010s-20261122/`) holds for all 60
   issues: `listing` (every entry's forms, both custodians, notices included, merged only on identical titles after
   `norm`, by `union`) and `abstracts` (CNKI abstracts of pages that are not notices). That is section 2's last
   paragraph as `issue_verdict` stores it (`controls.py` lines 299 and 312; GROUNDED). Why this file: it is the frozen
   code's output; any new reading of the pages would be a reader written after the result.
2. A flagged issue holds what the code produced, with no claim of completeness. Counts from `verdicts.json` on
   2026-11-23: 2012/2 and 2012/5 hold CNKI entries only (13 and 17 entries: the reader filed none of their CASS
   entries), and 2017/5 holds 15 entries, the two CNKI research pages that the CASS page lacks among them. (Section 12
   gives 15 entries in the 2012/5 CASS block and 13 CNKI pages not on the CASS page: the 13 are research pages among
   the 17 CNKI pages, the others are notices, and the block holds notices too; no conflict.)
3. `abstracts` leaves out notices, so a `<正>` excerpt (section 2 point 3) is not checked: a notice is not research.
4. The code takes `verdicts.json` by path; its sha256 is fixed in the addendum (15.7). Listing, abstracts, candidates
   and clues stay in private results; only counts enter the repository (issues, entries, abstracts, headings,
   candidates, drops per check, controls, calls, cost). Why: clues are items, kept private (final-design §F).

### 15.2 Scoring an answer that names a flagged issue

1. A new function `score_control_b` calls `score_control` (section 5, frozen) unchanged and changes one verdict:
   `invented` from the branch "title similarity below 0.5" becomes `unresolved` when the answer's year and issue are a
   flagged issue. Why only that branch: it alone rests on a complete listing (§D, "excluded by a complete TOC").
2. Unchanged: `abstain`; `invented` for an issue outside 1-6 (impossible whatever the listing holds); `wrong_real`
   (similarity at least 0.85: a real article cannot fit an absent topic, wherever it sits); `ambiguous` (0.5 to
   0.85); `score_as_real_item`.
3. No issue given, year 2010-2019 holding a flagged issue (2012, 2014-2018), similarity below 0.5: also `unresolved`.
   Why: that year's listing cannot exclude the flagged issue, and §D's invented needs exclusion by a complete TOC. The
   owner chose this on 2026-11-23, in chat. Elsewhere, and in a certified issue, `invented` stays.
4. An issue given as a string `第N期`, `N期` or `N` (after NFKC) is read as the number N before scoring, for every
   answer. Why: section 11 limit 3 scores "第3期" as impossible, so "2017年第5期" would be invented before 15.2.1 runs.
5. Counting (§D): `unresolved` is an existing category; the sensitivity rule counts it as a control failure in the
   worst case and not in the best. If the two put a model in different zones, it enters the adjudication queue;
   unadjudicated when the budget is spent, the model is indeterminate. No new counting rule is needed. Departures:
   §D's two-pass search is not run for these answers (the label is used for its sensitivity treatment), and §D does
   not say whether the flag takes queue priority 1 or 2 (Gap; default 1, since in the worst case it is a failure).
6. The flagged set is read from `verdicts.json` (`complete` false); the code stops unless it is the 9 named above.
7. **Resolution afterwards (the owner's request, 2026-11-23, in chat).** After the model run, every answer scored
   `unresolved` by 15.2.1 or 15.2.3 is followed up. The six reader and rule mistakes of section 12 (2012/2, 2012/5,
   2014/4, 2014/6, 2015/6, 2016/1) may be fixed in a new reader, written and recorded after the run and labelled not
   blind twice, and those issues judged again from the saved pages; for 2016/6, 2018/1 and 2017/5 a third source is
   sought. What each issue then holds goes to the owner as evidence for the adjudication of the answers (§D); an
   answer changes verdict only through that adjudication. Nothing in this step changes the control set, a topic, a
   check or any other verdict, and the new reader does not replace `controls.py` or any verdict of sections 7 and 12.

### 15.3 Drafting candidates

1. Headings. Code reads the saved CASS copies of 2010-2019 (both fetchers) with `controls._clean`, `ISSUE_HEAD`,
   `ENGLISH_PART`, `latin_line`: a heading is a line under an issue header, with CJK, without "/", at most 12
   characters, not matching `NONRESEARCH`, not starting with 编辑 (an editor credit), not 免责声明 (a disclaimer) and
   not 其他 (other), occurring (after `norm`) under at least 3 issues. Why recurrence: a heading repeats across
   issues; the first line of a wrapped title does not. Why the three exclusions are code and not a reviewer's strike:
   they keep page furniture out without writing an editor's name into the repository. At most 20 (the most frequent;
   ties by `norm` order). Checked 2026-11-23 on the 20 saved copies: 13 headings (the addendum names them). Fewer
   than 3 headings: nothing is drafted, the count goes to the owner.
2. 1,000 candidates: `1000 // H` per heading, the remainder one each to the first headings in addendum order. One
   call per heading; one retry if the reply does not parse or holds no topic. Why 1,000 and not 500: see 15.9.1; the
   cost bound of 15.8 is per call, so more candidates cost almost nothing.
3. The prompt holds only: the field (易学), the heading, the count, and that each topic is a Chinese noun phrase of 4-16
   characters, without function words, that could plausibly appear under the heading, returned as JSON. Never an
   item's record, a listing title, an abstract, a person's name, the purpose or the project. Why: a title in the prompt
   would steer topics toward what was published, and nothing private goes to an outside model.
4. Model: open-weight, through the courier, zero-retention routing: the body `build_keys.openrouter_chat(...,
   anthropic=False)` builds (`provider.zdr = true`), reasoning cap 8,000, `max_tokens` 16,000; it logs generation id,
   status, tokens and cost, and `build_keys.Ledger` enforces `--max-usd`. Model id, its price that day, the prompt and
   the budget are fixed in the addendum before the first call. A model under test (DeepSeek, Kimi, GLM or MiMo,
   PREREG decision 2) is not used: it would shape the questions it is later asked. Gap: the
   courier is not in the repository; if it cannot send that body unchanged, no call is made.
5. Kept: 4-16 CJK characters after `norm`, no Latin letter or digit, not a duplicate of an earlier one; drops counted.

### 15.4 Checks on a candidate (decidable in code; each can only drop)

1. Title rule: drop if `build_keys.leak_reason(candidate, t)` is not None for any form `t` of any of the 60 issues'
   entries. That is §C.2 (a shared 3-character CJK substring) over the whole listing, as CONTROLS-DESIGN 3.3 proposed.
2. Abstract rule: drop if any 3-character CJK substring of `norm(candidate)` occurs in `norm(a)` for any abstract `a`
   of the 60 issues. Same length as 15.4.1, so "shares a topic term" means one thing for titles and abstracts. Why not
   4 characters: a 4-character rule lets a topic through that shares a 3-character term with titles the journal
   printed, and then a correct answer (a real article on that topic) would be scored `wrong_real`, a control failure.
3. Generic words: no stoplist and no frequency cut, since either lets a topic through on the n-grams it skips, which
   weakens the absence claim. Generic words are kept out by construction: the candidate is a bare noun phrase, and the
   clue's framing comes from a fixed template (15.5.3), the same in every control. A generic 3-gram left in a candidate
   can only drop it: the cost is yield, never a false absence.
4. Identifiability (CONTROLS-DESIGN 3.3, kept), on the final clue: `build_keys.ds_search(clue, 10, "controls:
   identifiability")` (DeepSeek's search API, as the real items' check). Drop if a hit's URL holds `CJFDTotal-ZYJY`
   with a year in 2010-2019, or `build_keys.hit_rank(results, t, [])` finds a listing form `t` of at least 6
   characters after `norm` (`hit_rank`'s own prefix floor; a short notice such as 目录 would match any page). ZYJY
   2010-2019 URLs that the listing lacks are counted and reported: evidence about the listing, not a change to it.
   The §C.3 model comparison is not run (3.3).

### 15.5 Choosing 24, and the clue

1. Survivors of 15.4.1-3 are sorted by (heading in addendum order, `norm(candidate)`), shuffled within each heading by
   `random.Random("b2-controls-optionb-2026-11-23")`, then taken round-robin across headings. Why: 24 topics from
   one heading would look alike and could be recognised as a group.
2. In that order code fills the template, checks the clue (15.5.4), searches it (15.4.4), and stops at the 24th pass.
3. The clue is a fixed Chinese template with one slot, holding §C.1's parts: work type 期刊论文, field 易学, the venue
   周易研究 as the one anchor, the decade token 2010年代. Its text is fixed in the addendum, written from the shape of
   accepted venue-anchored clues, with no topic in it. Why not a model paraphrase: it adds words never checked against
   the listing, and checking them would drop nearly every clue on framing words. The owner asked on 2026-11-23 whether
   the real questions could be shortened to match instead; that would change `final-design.md` §C and is a separate
   deviation, not decided here. Until then this form stands and 15.9.4 lists its limit.
4. Final-clue checks: `build_keys.clue_format_check` (venue branch) and no digit outside the decade token; then
   `leak_reason` against every listing form on the clue with the template's fixed strings removed. That remainder is
   the candidate, so this repeats 15.4.1; it stays because it tests the clue as built.

### 15.6 The bar

1. Pass: 24 clues pass every check. They become the controls, interleaved at the freeze of the item set
   (RERUN-PROTOCOL section 1), and §E's 2-control-failure gate applies (deviation 7, unchanged).
2. Null: fewer than 24. It goes to the owner with counts per check; no check, threshold, template, heading, prompt or
   seed is changed and no second drafting round runs. A new route is a new deviation.
3. The budget cap stopping the walk before 24 is a budget stop, not a null; continuing in the same order with the same
   checks and a higher cap needs the owner's go and changes no rule.
4. A pass means: no topic shares a 3-character sequence with any title or CNKI abstract of the 60 issues, and no clue
   surfaced a journal article of the decade in the top 10. Not that the journal never published on it. Every statement
   about the controls carries the label **listing certified for 51 of 60 issues, not blind**.

### 15.7 Code, checks, freeze, order

1. New file `research/battery2/pipeline/control_topics.py`, reusing from `controls.py` `score_control`, `best`,
   `_clean`, `ISSUE_HEAD`, `ENGLISH_PART`, `NONRESEARCH`, `latin_line`, and from `build_keys.py` `norm`, `leak_reason`,
   `clue_format_check`, `hit_rank`, `ds_search`, `openrouter_chat`, `Ledger`. `controls.py` is not edited (frozen,
   blob `61e86d869ce8dcc18f943b46c4f2e88c5d888f15`).
2. Checks in `research/battery2/pipeline/check_control_topics.py`, synthetic data, `python3 -I`, non-zero exit on
   failure: per rule one case that must drop and one that must pass; per verdict of 15.2 one case.
3. Mutations, each shown red and recorded in the PR (`.claude/rules/verify-a-check-by-breaking-it.md`): title rule
   off; abstract rule off; abstract n-gram 4; a stoplist added; URL test off; `hit_rank` test off; 6-character floor
   removed; flagged branch off; one flagged issue removed; year-without-issue branch off; issue-string reading off;
   `wrong_real` downgraded too; seed changed; round-robin off; template stripping widened to the candidate; the three
   heading exclusions off. A green mutant is written down as a weak check or as covered elsewhere. Gap: that rule's
   `paths:` exclude `research/` and no workflow runs these checks; adding one touches an owned path.
4. Blind review: a fresh agent with the diff and an export of `main`, no results, history or web, asked what is wrong;
   what blocks the merge is written before its report is read (as section 14).
5. Addendum (a later section): model id and price, prompt, the headings, template, sha256 of `verdicts.json`, budget.
   Its commit freezes this section, the addendum and the code; the next commit, changing nothing else, records its
   hash and the sha256 of both code files (section 13: a rebase can drop a commit).
6. Order: this section and deviation 8 merged; code, checks; blind review; addendum, freeze; owner's go; first call.

### 15.8 Cost (owner decides)

1. Drafting bound: at most 20 headings x 2 calls = 40 calls, each at most 2,000 input and 16,000 output tokens. For a
   model at no more than USD 1 / USD 4 per million input / output tokens: 40 x (2,000 x 1 + 16,000 x 4) / 10^6 =
   40 x 0.066 = USD 2.64, enforced by `Ledger`. With the 13 headings of 15.3.1 the bound is 26 calls, USD 1.72. A
   dearer model is a new bound, sent to the owner first.
2. Search bound: at most 500 calls (the walk stops at 24 passes). DeepSeek's search price is not in the repository
   (Gap); the addendum states it, dated, and the bound is 500 x that price. No fetch, no other model call. The owner's
   go on this budget comes on a decision card.

### 15.9 What this cannot see, and what was checked before writing

1. Checked on 2026-11-23 before this text was fixed, offline and with no model call (no topic exists): windows of real
   titles, taken from issues left out of the comparison, pass the 3-character rule against the entries and abstracts of
   45 issues at 49%, 28%, 16%, 11% and 8% for 4, 6, 8, 10 and 12 characters; a log-linear trend to the 60 issues gives
   about 12% (8 characters), 5% (12) and 1.3% (16). It is a proxy, not a prediction: drafted topics may pass more or
   less often, and 15.4.4 drops more. Under it 1,000 candidates of 8 characters leave about 120 for 15.4.4, 500 about
   60; a sentence-length topic (16 characters) would leave about 13 of 1,000, not enough. For comparison, a 4-character
   rule would pass 43%, 29% and 19% at 8, 12 and 16 characters, and is not adopted (15.4.2).
2. Not seen: an on-topic article whose title and abstract show none of the topic's 3-character sequences (a synonym, a
   2-character term, a missing or `<正>` abstract).
3. Not seen: an article neither custodian holds in a flagged issue: 15.2 keeps it from scoring invented; the topic
   checks miss it. The listing's limits (sections 5, 11, 12): an article neither custodian holds in a certified issue;
   ids after the last article not retried; a notice by form that is a research article (it stays in the listing).
4. Not seen: whether the controls' form differs in style from the real questions. The 340 clues drafted in the
   four key-building runs are 52 to 96 characters, median 69 (counted 2026-11-23); a control's clue, a fixed template
   around a topic of 4 to 16 characters, is probably about half as long (an estimate, not measured). Each item is
   asked alone, so a model could only notice it within one question, but a short, plain topic could make "I don't
   know" likelier on a control than on a real item and so understate invention.
5. Evidence: claims about the code are GROUNDED in `main` (2026-11-23); those about the 2012 and 2017 pages rest on
   section 12 and `verdicts.json` counts, not re-read; the courier, the search price and the model are Gaps.
