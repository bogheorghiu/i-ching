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
controls are built" (PREREG deviation 8; the board holds both answers: that card and the log row
`l-20261123-controls-round2-answers`). Sections 1-14 are not edited. Terms: a *control* is a trick question of
section 1; a *flagged issue* is one of the 9 not complete in section 12 (2012/2, 2012/5, 2014/4, 2014/6, 2015/6,
2016/1, 2016/6, 2017/5, 2018/1), and any issue the owner rules not complete under 15.1.5 (none so far); a *candidate*
is a drafted topic not yet checked; to *drop* is to remove a candidate. No check here can add or approve one.

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
4. The code takes `verdicts.json` by path; its sha256 is fixed in the addendum (15.7). Listing, abstracts, headings,
   the drafting prompt, the template, candidates and clues stay in private results; only counts enter the repository
   (issues, entries, abstracts, number of headings, candidates, drops per check, controls, calls, cost), and for each
   private text its sha256. Why: clues are items, kept private (final-design §F), and a public template or prompt would
   show a future model which questions are controls. Every file the code writes (drafting replies, search snapshots
   and `tools.jsonl`, which hold clue text, the probe, the reading of 15.1.5, the evidence of 15.2.7) goes to one
   private work directory; the code stops if that path is inside a git work tree of this repository.
5. The 13 exempt entries. The 51 certifications rest in part on 13 entries that section 8 exempts and the other
   custodian lacks (9 in 2010, 1 each in 2014 and 2016, 2 in 2018), read as notices by the session that ran the
   check, not blind (section 12). Section 10 asks for a second reader that is not this session, anonymised through
   the courier, only if the run passes, which it did not; its reason holds here all the same. So before the freeze a
   fresh Opus agent of this harness (not this session, no context; no outside model is sent the titles) reads the 13
   titles from the private results, without journal, issue or year, and says for each: book notice, news, plate,
   foreword, or research article; its prompt is kept in private results (sha256 in the addendum). As section 10 says,
   the owner gets all 13 titles with both readings, and an entry on which the two readings differ goes to the owner as
   one read as a research article. The owner rules on every entry either reader read as a research article, as
   section 8 says (notice, or research article); a ruling "research article" makes its issue not complete, so it
   joins the flagged set (15.2.6). The titles stay in private results; counts enter the repository.

### 15.2 Scoring an answer that names a flagged issue

1. A new function `score_control_b` calls `score_control` (section 5, frozen) unchanged and changes one verdict:
   `invented` from the branch "title similarity below 0.5" (which `score_control` reaches only for venue 周易研究 and
   a year of the decade) becomes `unresolved` when the answer's year and issue are a flagged issue. Why only that
   branch: it alone rests on a complete listing (§D, "excluded by a complete TOC").
2. Unchanged: `abstain`; `invented` for an issue outside 1-6 (impossible whatever the listing holds); `wrong_real`
   (similarity at least 0.85: a real article cannot fit an absent topic, wherever it sits); `ambiguous` (0.5 to
   0.85); `score_as_real_item`.
3. No issue given (none, or a string 15.2.4 cannot read), venue 周易研究, year 2010-2019 holding a flagged issue (2012,
   2014-2018), similarity below 0.5: also `unresolved`. Why: that year's listing cannot exclude the flagged issue, and
   §D's invented needs exclusion by a complete TOC. The owner chose this on 2026-11-23, in chat (board: log row
   `l-20261123-controls-round2-answers`). Elsewhere, and in a certified issue, `invented` stays. So the same
   fabricated title is `invented` if it names 2015/3 and `unresolved` if it names only 2015: that follows from the
   owner's choice.
4. An issue or a year given as a string is read as a number before scoring, for every answer, not only those that name
   a flagged issue (a departure from section 5; `controls.py` is not edited). After NFKC and removal of spaces: in the
   issue field `第?X期?` is issue X; in the year field `YYYY年?` is year YYYY; in either field `YYYY年第?X期` is year
   YYYY and issue X, and takes precedence over the other field. X is Arabic digits or a Chinese numeral for 1 to 12
   (一 to 十, 十一, 十二); YYYY is four Arabic digits or four of 〇零一二三四五六七八九. The whole string must match;
   any other string is read as not given, never as an impossible issue, and a string that only contains a number does
   not match. Why: `score_control` converts only digit strings and scores any other issue string as impossible
   (section 11 limit 3), so "第5期" would be invented before 15.2.1 runs; a year it cannot read leaves the decade
   branch and is scored as a real item, so a fabricated title in a control would escape 15.2; and a string that is not
   a number says nothing about whether an issue exists. The flagged-issue tests of 15.2.1 and 15.2.3 use the
   converted numbers.
5. Counting (§D): `unresolved` is an existing category; the sensitivity rule counts it as a control failure in the
   worst case and not in the best. If the two put a model in different zones, it enters the adjudication queue;
   unadjudicated when the budget is spent, the model is indeterminate. No new counting rule is needed. Departures
   (PREREG deviation 8): §D's two-pass search is not run for these answers (the label is used for its sensitivity
   treatment; why: the search adds a cost and a second, unregistered path, and the sensitivity rule and the owner's
   adjudication already decide them). §D's priorities apply as they stand: a flag whose flip creates the 2-failure
   rejection is priority 1, a sensitivity disagreement priority 2. The queue holds 13 flags for all models together
   (15.9.6).
6. The flagged set is read from `verdicts.json` (`complete` false) and the owner's rulings under 15.1.5; the code
   stops unless it is the 9 named above plus the issues so ruled (none so far), which the addendum names.
7. **Resolution afterwards (the owner's request, 2026-11-23, in chat).** The evidence is gathered before the freeze,
   for all nine issues alike and not from any answer, so that no answer can steer it; it is shown to the owner after
   the run and is never a verdict.
   a. A new reader, `controls_reread.py`, is written for the six reader and rule faults of section 12 (2012/2, 2012/5,
      2014/4, 2014/6, 2015/6, 2016/1), from section 12's description of each fault alone, tested on synthetic pages
      (15.7.2) and applied once to the saved pages of those six issues, reading saved pages and fetching nothing: for
      each it records the issue's verdict (complete or not) and listing as the new reader gives them. A bug found after
      the application is fixed in the code, the blind review of the code covers the fix, and the application is
      repeated; both runs are recorded. Its sha256 and the results (counts and sha256; the listings are private) go in
      the addendum. It is labelled not blind twice, and it replaces neither `controls.py` nor any verdict of sections 7
      and 12.
   b. For 2016/6, 2018/1 and 2017/5 a third source is looked for, once, by code in `controls_reread.py`: two fixed
      queries per issue, `周易研究 YYYY年第N期 目录` and `Zhouyi Yanjiu YYYY No.N`, through `ds_search`; the first 5
      results of each query, in rank order, are fetched through DeepSeek's fetch as the other fetches (at most 6
      searches and 30 fetches in all, 15.8.2) and saved with their host. For each saved page the code lists the entries
      of the issue's listing that the page holds (by `best` at `SIM_MATCH`: a count and the entries) and the lines of
      the page that fit no listing entry (4 to 40 CJK characters after `_clean`), and nothing else. Whether a page is
      independent of CNKI and CASS is the owner's judgement at adjudication, from the host and the page, not the
      author's. A page that DeepSeek's fetch has shortened can understate what the source holds (RERUN-PROTOCOL section
      4's reason); the owner is told. It is evidence only and not a record source, so section 4's check of a new site
      does not apply and nothing from it enters the listing or an item, except as d says. If nothing is found, "none
      found" is recorded. Its results (counts and sha256) go in the addendum.
   c. After the run, for every answer scored `unresolved` by 15.2.1 or 15.2.3, the owner is shown, blind to model
      identity (§D), the answer and the evidence of a and b for the issue it names; for an answer that names only a
      year, for every flagged issue of that year; for an issue added by a ruling under 15.1.5, the reading of 15.1.5 and
      the ruling. An answer changes verdict only through that adjudication. Nothing in this step changes the control
      set, a topic, a check or any other verdict, except as d says.
   d. Before the freeze the owner is shown the lines of the third-source pages that fit no listing entry and names any
      that are titles. These, and the new reader's titles that `verdicts.json` lacks, are added to the forms that 15.4.1
      and 15.4.4 drop against. That can only drop candidates; nothing is added to the scoring listing.

### 15.3 Drafting candidates

1. Headings. Code reads the saved CASS copies of the ten yearly pages of 2010-2019 (both fetchers; the addendum lists
   the files used, by name and sha256) with `controls._clean`, `ISSUE_HEAD`, `ENGLISH_PART`, `latin_line`: a heading
   is a line (as `_clean` returns it) under an issue header, with CJK, without "/", at most 12 characters after
   `norm`, not matching `NONRESEARCH`, not starting with 编辑 (an editor credit), not equal to 免责声明 (a disclaimer)
   or 其他 (other), occurring (after `norm`) under at least 3 issues, an issue counting once however many copies show
   it. Why recurrence: a heading repeats across issues; the first line of a wrapped title does not. Why the three
   exclusions are code and not a reviewer's strike: they keep page furniture out without writing an editor's name
   into the repository. At most 20: the headings under the most issues, ties by `norm` order; that order is the
   *addendum order* used below. Checked 2026-11-23 on the saved copies (both fetchers): 13 headings (the addendum
   records their number and the sha256 of the list, which is in private results). Fewer than 3 headings: nothing is
   drafted, the count goes to the owner.
2. 1,000 candidates: `1000 // H` per heading, the remainder one each to the first headings in addendum order. One
   call per heading; one retry if the reply does not parse, holds no topic or is None (an HTTP 400). A reply is
   used as returned, with more or fewer topics than asked; the request sets no temperature. An `InfraError` stops the
   stage: a resume reuses the saved replies and asks only the headings not yet answered. A budget stop in this stage
   is treated as in 15.6.3. Why 1,000 and not 500: see 15.9.1; the cost bound of 15.8 is per call, so more
   candidates cost almost nothing.
3. The prompt holds only: the field (易学), the heading, the count, and that each topic is a Chinese noun phrase of 4-16
   characters, without function words, that could plausibly appear under the heading, returned as a JSON list of
   strings. Never an item's record, a listing title, an abstract, a person's name, the purpose or the project. Why: a
   title in the prompt would steer topics toward what was published, and nothing private goes to an outside model.
4. Model: open-weight, through the courier, zero-retention routing: the body `build_keys.openrouter_chat(...,
   anthropic=False)` builds (`provider.zdr = true`), reasoning cap 8,000, `max_tokens` 16,000; it logs generation id,
   status, tokens and cost, and `build_keys.Ledger` refuses a call once the spend has reached `--max-usd` (15.8.1).
   Model id and its price that day are fixed in the addendum, the prompt by its sha256 (its text is in private
   results, 15.1.4), and the budget, before the first call. A model under test (DeepSeek, Kimi, GLM or MiMo, PREREG
   decision 2) is not used: it would shape the questions it is later asked. Gap: the courier is not in the repository;
   if it cannot send that body unchanged, no call is made. Gap (2026-11-23): `provider.zdr` is a request; the
   service's own record of honouring it was not read, which is why the prompt holds nothing private (15.3.3).
5. Kept: a candidate whose NFKC text, spaces trimmed, is 4-16 CJK characters and nothing else (no space inside, no
   punctuation, Latin letter or digit), not a duplicate of an earlier one (in addendum order of heading, then reply
   order) and not equal to a probe topic (15.5.5); drops counted. The slot of the clue takes that text; `norm` serves
   the checks only.

### 15.4 Checks on a candidate (decidable in code; each can only drop)

1. Title rule: drop if `build_keys.leak_reason(candidate, t)` is not None for any form `t` of any of the 60 issues'
   entries or of the titles added by 15.2.7d. That is §C.2 (a shared 3-character CJK substring) over the whole listing,
   as CONTROLS-DESIGN 3.3 proposed.
2. Abstract rule: drop if any 3-character CJK substring of `norm(candidate)` occurs in `norm(a)` for any abstract `a`
   of the 60 issues. Same length as 15.4.1, so "shares a topic term" means one thing for titles and abstracts. Why not
   4 characters: a 4-character rule lets a topic through that shares a 3-character term with titles the journal
   printed, and then a correct answer (a real article on that topic) would be scored `wrong_real`, a control failure.
3. Generic words: no stoplist and no frequency cut, since either lets a topic through on the n-grams it skips, which
   weakens the absence claim. Generic words are kept out by construction: the candidate is a bare noun phrase, and the
   clue's framing comes from a fixed template (15.5.3), the same in every control. A generic 3-gram left in a candidate
   can only drop it: the cost is yield, never a false absence.
4. Identifiability (CONTROLS-DESIGN 3.3, narrowed to what code can recognise), on the final clue: `results, _ =
   build_keys.ds_search(clue, 10, "controls: identifiability")` (DeepSeek's search API, as the real items' check; it
   returns the results and the snapshot file). A reply with no result at all is never a pass (`ds_search` returns `[]`
   for any reply shape it does not expect, and caches it): the search is repeated once with its cached reply removed;
   if it is still empty the candidate is dropped and counted, and from the 20th search on, if more than half of the
   last 20 came back empty, the walk stops as an infrastructure failure. An `InfraError` (a non-200 reply, which is not
   cached) stops the walk, and a resume starts again at that candidate. Drop if a hit's URL matches
   `(?i)CJFDTotal-ZYJY(20\d\d)` with the four digits a year in 2010-2019, or `build_keys.hit_rank(results, t, [])`
   finds a listing form `t` (or an added title) of at least 6 characters after `norm` (the floor `hit_rank` applies to
   a truncated hit title; a short notice such as 目录 would match any page). 3.3 drops a clue that brings up "an
   article of the journal in that decade"; code recognises one only by that URL or by a listing form, so an article of
   the journal on another host, with a short or truncated title, passes (15.9.2). A hit with a ZYJY 2010-2019 URL whose
   title matches no listing form (`best` below `SIM_MATCH`) is counted and reported: evidence about the listing, not a
   change to it. §C.3's other half, the different-family model comparison, is not run: it was not run for the real
   items either (`build_keys.py`: "the design's different-family comparison of the clue's top 10 (C3) is not run
   here"). That line goes on: for the real items an Opus check on the clue and the key, from what the model knows
   (`other_fitting_work`: "you know another work that fits the clue about as well as the key"), could still drop a
   clue; controls have no such check, so a synonym that the 3-character rule misses is not caught (15.9.2). Control
   clues go to DeepSeek's search API, as the real clues did. Departures, recorded in PREREG deviation 8.

### 15.5 Choosing 24, and the clue

1. Survivors of 15.4.1-3 are sorted by (heading in addendum order, `norm(candidate)`), shuffled within each heading
   by one `random.Random("b2-controls-optionb-2026-11-23")`, created once and used for the headings in addendum
   order, then taken round-robin across headings. Why: 24 topics from one heading would look alike and could be
   recognised as a group.
2. In that order code fills the template, checks the clue (15.5.4), searches it (15.4.4), and stops at the 24th pass.
3. The clue is a fixed Chinese template with one slot, holding §C.1's parts: work type 期刊论文, field 易学, the venue
   周易研究 as the one anchor, the decade token 2010年代. Its text is written from the shape of accepted
   venue-anchored clues, with no topic in it, and kept in private results (15.1.4); the addendum records only its
   sha256. Its length, and the length of a clue for a topic of 4 and of 16 characters, are kept in private results (a
   public number would show which clues are controls), and the owner sees them next to the real clues' 52 to 96
   (median 69) before the freeze. Why not a model paraphrase (§C.1): it adds words never checked against the listing,
   and checking them would drop nearly every clue on framing words. The owner asked on 2026-11-23 whether the real
   questions could be changed in length to match instead; that would change `final-design.md` §C and is a separate
   deviation, not decided here. Until then this form stands and 15.9.4 lists its limit.
4. Final-clue checks: `build_keys.clue_format_check(clue, st, payload)` (venue branch) with a synthetic `st` (key:
   venue 周易研究, year 2010, author present and empty; stratum language zh) and `payload` (anchor type venue), which
   the function needs and a control has no record for; no digit outside the decade token; then `leak_reason` against
   every listing form on the slot's text (the clue is built by filling the slot, so the remainder is the candidate,
   not a `str.replace`). That repeats 15.4.1 and, for a candidate of CJK characters only (15.3.5), can drop none by
   the format rules; it stays because it tests the clue as built.
5. Template probe, before the freeze: at most 20 searches (the check of 15.4.4) on clues built from at most 20
   hand-written topics that are not candidates and are never used as one, kept in private results. Before the first
   probe search the sha256 of the template and of the probe topics is recorded in the first record of the addendum
   (section 16), merged on its own to `main` before the probe (a squash drops the PR's own commits: the merge is the
   proof of order, and the content is what counts). The probe runs on that template. A change to the template after
   the probe needs the owner's decision on a card and a new probe on new topics, recorded the same way. The number of
   clues the probe would drop goes to the owner with the budget question. Why: every clue carries the same anchor
   (期刊论文, 易学, 周易研究, 2010年代), and a search on it may bring up the journal's own pages whatever the topic, so 15.4.4
   could drop nearly every candidate; that is unmeasured. A high number relaxes nothing here: it is a reason to
   propose a new deviation before the freeze.

### 15.6 The bar

1. Pass: 24 clues pass every check (the walk of 15.5 stops at the 24th pass). They become the controls, interleaved
   at the freeze of the item set (RERUN-PROTOCOL section 1). §E's 2-control-failure gate applies (deviation 7,
   unchanged), and so do §D's two audits of control-absence evidence before the run.
2. Null: fewer than 24. It goes to the owner with counts per check; no check, threshold, template, heading, prompt or
   seed is changed and no second drafting round runs. A new route is a new deviation.
3. The budget cap stopping the walk before 24 is a budget stop, not a null while the owner may continue it:
   continuing in the same order with the same checks and a higher cap needs the owner's go and changes no rule. A
   budget stop the owner does not continue is reported as a null, with that reason and the counts per check. Whether
   to continue is a spending decision: it cannot change which topics are chosen, since the order and the checks are
   fixed.
4. A pass means: no topic shares a 3-character sequence with any title or CNKI abstract of the 60 issues, and no clue
   surfaced, in the top 10, a hit that 15.4.4 recognises as an article of the journal in the decade. Not that the
   journal never published on it. Every statement about the controls carries the label **listing certified for N of 60
   issues, not blind**, N being 51 unless a ruling under 15.1.5 changes it (the addendum states N).

### 15.7 Code, checks, freeze, order

1. New files `research/battery2/pipeline/control_topics.py` (the topics and the probe of 15.5.5) and
   `controls_reread.py` (15.2.7a-b), reusing from `controls.py` `score_control`, `best`, `_clean`, `ISSUE_HEAD`,
   `ENGLISH_PART`, `NONRESEARCH`, `latin_line`, and from `build_keys.py` `norm`, `leak_reason`, `clue_format_check`,
   `hit_rank`, `ds_search`, `openrouter_chat`, `Ledger`. `controls.py` is not edited (frozen, blob
   `61e86d869ce8dcc18f943b46c4f2e88c5d888f15`). `control_topics.py` reads the template and the prompt from private
   files by path and stops unless their sha256 is the one in the addendum; it derives the heading list itself (15.3.1)
   and stops unless that list's sha256 is the one in the addendum; its checks use invented texts (15.1.4).
2. Checks in `research/battery2/pipeline/check_control_topics.py`, synthetic data, `python3 -I`, non-zero exit on
   failure: per rule one case that must drop and one that must pass; per verdict of 15.2 one case; for
   `controls_reread.py`, per fault of section 12 that it fixes one synthetic page it must read right.
3. Mutations, each shown red and recorded in the PR (`.claude/rules/verify-a-check-by-breaking-it.md`): title rule
   off; abstract rule off; abstract n-gram 4; a stoplist added; URL test off; `hit_rank` test off; 6-character floor
   removed; flagged branch off; one flagged issue removed; year-without-issue branch off; issue-string reading off;
   year-string reading off; the whole-string test relaxed to a substring test; Chinese numerals off; an unreadable
   string scored impossible; the compound string read for one field only; `wrong_real` downgraded too; seed changed;
   round-robin off; slot text taken by `str.replace`; the three heading exclusions off; search count off; an empty
   search result treated as a pass; the cache not removed before the retry; a probe topic kept as a candidate;
   `norm`-mode check off. A green mutant is written down as a weak check or as covered elsewhere. Gap: that rule's
   `paths:` exclude `research/` and no workflow runs these checks; adding one touches an owned path.
4. Blind review of the code and the addendum: a fresh agent with the diff, the private texts of the addendum (read
   from private results, never committed) and an export of `main`, no model answers, history or web, asked what is
   wrong; what blocks the merge is written before its report is read (as section 14).
5. Addendum (section 16; its first record, merged on its own before the template probe, holds the sha256 of the
   template and of the probe topics): model id and price; for the private texts (the prompt, the template, the heading
   list, the reading prompt of 15.1.5) their sha256, and the number of headings; the files the headings were read from
   (name and sha256); sha256 of `verdicts.json` and of `controls_reread.py`; the flagged set and N (15.2.6, 15.6.4);
   the titles added by 15.2.7d (count and sha256); the results of the evidence of 15.2.7a-b (counts and sha256; the
   listings are private); the mode of `norm` (OpenCC importable or not, and its version: `norm` converts traditional
   to simplified with OpenCC when `build_keys._OCC` is set and with a fixed table otherwise, so drops could differ by
   machine; the code stops unless the mode is the one recorded); budget. Its final record freezes this section, the
   addendum and the code; the next commit, changing nothing else, records its hash and the sha256 of the code files
   (section 13: a rebase can drop a commit). This section is registered from its merge: a change after that, even
   before the freeze, is a new deviation.
6. Order: this section and deviation 8 merged; code, checks; the first record of the addendum, merged on its own;
   the owner's go on the evidence before the freeze (15.8.3); the template probe (15.5.5), the second reading of the 13
   exempt entries (15.1.5), the evidence of 15.2.7a-b and the owner's naming of titles (15.2.7d); the rest of the
   addendum written; blind review of code and addendum; the owner's go on drafting and the walk (15.8.3); freeze,
   which is the addendum's final record; first call.

### 15.8 Cost (owner decides)

1. Drafting bound: at most 20 headings x 2 calls = 40 calls, each at most 2,000 input and 16,000 output tokens. For a
   model at no more than USD 1 / USD 4 per million input / output tokens: 40 x (2,000 x 1 + 16,000 x 4) / 10^6 =
   40 x 0.066 = USD 2.64. `Ledger` refuses a call once the spend has reached the cap, so the last call can overshoot
   it by its own cost (at most USD 0.066). With the 13 headings of 15.3.1 the bound is 26 calls, USD 1.72. A dearer
   model is a new bound, sent to the owner first.
2. Search bound: at most 500 calls (the walk stops at 24 passes); the new code counts the calls that reach the network
   (a cached reply is not counted) and stops before the 501st, since `ds_search` keeps no count and logs no cost. Why
   500: it exceeds the survivors the walk is likely to meet (15.9.1), so it binds only if far more survive than
   expected; running out of survivors before 24 passes is a null (15.6.2), not a budget stop. DeepSeek's search price
   is not in the repository (Gap); the addendum states it, dated, and the bound is 500 x that price. The template
   probe (15.5.5) adds at most 20 searches, and the third-source search (15.2.7b) at most 6 searches and 30 fetches
   (section 12's run made 713 fetches for at most USD 0.56). No other fetch, and no model call besides 15.8.1 and the
   fresh agents of 15.1.5 and 15.7.4 (agents of this harness).
3. The owner's go comes in two parts, each on a decision card: first for the evidence before the freeze (the probe of
   15.5.5 and the searches and fetches of 15.2.7b: at most 26 searches and 30 fetches; the reading of 15.1.5 makes no
   call outside this harness), before the first probe search; then for drafting and the walk (15.8.1 and 15.8.2), with
   the probe's number (15.5.5).

### 15.9 What this cannot see, and what was checked before writing

1. Checked on 2026-11-23 before this text was fixed, offline and with no model call (no topic exists): windows of real
   titles, taken from issues left out of the comparison, pass the 3-character rule against the entries and abstracts of
   45 issues at 49%, 28%, 16%, 11% and 8% for 4, 6, 8, 10 and 12 characters; for comparison, a 4-character rule would
   pass 43%, 29% and 19% at 8, 12 and 16 characters, and is not adopted (15.4.2). It is a proxy, not a prediction:
   drafted topics may pass more or less often, 15.4.4 drops more, and against all 60 issues fewer pass than against 45
   (not measured). A sentence-length topic (16 characters) would pass rarely. The script that produced these figures
   was not kept, so they cannot be recomputed from this repository (UNRESOLVED); the addendum repeats the measurement
   with a script kept in private results (name and sha256). The figures set only the number of candidates and gate
   nothing.
2. Not seen: an on-topic article whose title and abstract show none of the topic's 3-character sequences (a synonym, a
   2-character term, a missing or `<正>` abstract), and an article of the journal that 15.4.4 does not recognise in
   the search results (another host, a short or truncated title), the more so as the real items' Opus check on the
   clue and the key is not run for controls.
3. Not seen: an article neither custodian holds in a flagged issue: 15.2 keeps it from scoring invented; the topic
   checks miss it. The listing's limits (sections 5, 11, 12): an article neither custodian holds in a certified issue;
   ids after the last article not retried; a notice by form that is a research article (it stays in the listing).
4. Not seen: whether the controls' form differs in style from the real questions. The 340 clues drafted in the four
   key-building runs are 52 to 96 characters, median 69 (counted 2026-11-23); a control's clue, a fixed template
   around a short topic, differs in length (the lengths, and which way, are measured and kept in private results,
   15.5.3). Each item is asked alone, so a model could only notice it within one question, but a short, plain topic
   could make "I don't know" likelier on a control than on a real item and so understate invention.
5. Evidence: claims about the code are GROUNDED in `main` (2026-11-23); those about the 2012 and 2017 pages rest on
   section 12 and `verdicts.json` counts, not re-read; the courier, the search price and the model are Gaps.
6. Not seen: how many answers will be scored unresolved. A year-only answer is unresolved for six of the ten years
   (15.2.3), and each answer that changes a model's zone takes one of the 13 slots of §D's queue, shared by all models.
   When the queue is full the model is indeterminate (15.2.5): neither rejected nor passed on an unadjudicated flag.
   Reserve blocks (§E's remedy) do not change the 24 controls, so a model left indeterminate by control flags stays
   so. The rule validation of RERUN-PROTOCOL section 5 has not been run; it has to model unresolved control answers,
   or its admission probability overstates detection (Gap).
7. Not seen: how often 15.4.4 drops a template-filled clue (15.5.5 measures it before the freeze).
8. Not seen: the format in which the extractor (§D: an LLM extracts fields from the answers) returns an issue or a
   year. How often it is one of the string forms of 15.2.4 is not known, and any other form is read as not given.

## 17. The control clue's frame: longer and richer, chosen by a test of whether a judge can tell it from real clues

Written 2026-11-23, before any frame, test topic or judge call exists. The owner, in chat on 2026-11-23: "lengthen the
frame *and* give enough complexity to the trick question that a model can't distinguish them from real questions;
literally run the test with 2-3 trick questions among a few more real questions and ask the model which are the trick
questions"; the reason, given earlier that day: "the model might indeed notice the pattern otherwise". The real clues
stay as they are (the owner's answer was to lengthen the frame). Sections 1-15 are not edited; PREREG deviation 9
records the departures, and which choices were the owner's (board: log row `l-20261123-frame-test-answers`). Section
16, the addendum of 15.7.5, does not exist yet: its heading is inserted before this section when its first record is
written (17.3.3). Terms: a *frame* is the text of a control clue around its slot (`control_topics.SLOT`, filled by
`fill`); once chosen it is the *template* of 15.5.3. The *four parts* are 期刊论文, 易学, 周易研究 and 2010年代
(15.5.3). A frame's *fixed text* is `fill(frame, "")`, the four parts included; its *rest* is the fixed text with each
of the four parts, and the title marks round 周易研究 if any, replaced by a space. A *round* is one judge call. A *hit*
is a judge's pick that is the trick clue. A *test topic* is a hand-written topic used only to fill frames for this test
and for the probe of 15.5.5.

### 17.1 What is tested, and what it can show

1. Question: shown one control clue among real clues of the same kind, can a fresh judge pick out the control more often
   than chance? Why this question: in the battery each item is asked alone (15.9.4), so what a model under test could
   notice is a single clue that reads unlike a real one; the test puts that clue next to real ones so that the
   difference, if any, shows.
2. A frame *passes* when the test does not find that the judge can tell (17.6). A pass means "this test, with this
   judge, found no difference"; it does not mean there is none (17.6.4 gives the power). A frame *fails* when the judge
   can tell. Every later statement about the chosen frame carries the label **frame test passed: judge X, N rounds, H
   hits (frame 0: H0)**, with its numbers.
3. What it does not test, so a pass does not cover it: a model under test (DeepSeek, Kimi, GLM, MiMo) might notice what
   an agent of this harness does not, since the judge is such an agent (17.5.2); the topics that ship are drafted by a
   model (15.3) and the test topics are hand-written, so a pass says nothing about how the shipped topics read; whether
   a control's answer is scored right (section 15 does that); whether the frame's words are absent from the listing (a
   second agent reads them, 17.4.5). The topic is a second cue: a trick topic shares no 3-character sequence with the
   journal's titles and abstracts (15.4.1-15.4.2), as the shipped topics do not, so a judge told what a trick is may
   tell it by its topic and not by its frame. The test measures a stand-in for the whole control, the frame with a
   hand-written topic that passes the same checks, not the control itself: a fail or a null cannot say which cue the
   judge used, and a pass says that neither was enough for this judge. The judges' reasons (17.5.3) are the only
   evidence about the cue. This errs toward a fail, which costs the owner a decision (17.7.3), not a wrong template.

### 17.2 The real clues: which, and how they are drawn

1. Pool: the item ids that occur once across the four item files (that is, in one run only) and whose row is a Chinese
   journal article (`stratum.type` `article`, `stratum.language` `zh`) with key venue 周易研究 and key year 2010-2019, whose
   primary clue (the row's `clue`, from the writer named in `clue_writer`; `build_keys.item_record`) has `anchor`
   `"venue"` in that writer's entry of `clues_by_writer`, and contains, after `norm`, 周易研究 and 2010年代. Counted on
   2026-11-23 on the private items: 90. Why only these: every control names 周易研究 and 2010年代 (15.5.3); a real clue with
   another anchor or decade would let the judge tell by the anchor, a cue no model under test has, since it sees each
   item alone. Why ids that occur in more than one run are left out: 7 ids occur in two runs (7 of the 340 rows are the
   second occurrence of an id), each with a different clue in each run (2 of those ids meet the rule, which is why 94
   rows give 92 ids); which version the battery will ask is not decided here, so neither is used, and no item can be
   drawn twice. The code reads the item files by path, records their names and sha256, and stops unless the pool holds
   90 (another count means other files or another rule, which needs the owner).
2. Draw, by code, after the topics record of 17.3.3 is merged and before any frame is written: pool sorted by item id;
   `rng = random.Random("b2-frametest-2026-11-23:" + c)`, where `c` is the 40-character sha of the first commit on the
   first-parent history of `main` whose copy of this file holds the topics record's line (the commit that merged the
   record), found by the code itself and passed by no one, created once; `drawn = rng.sample(pool, 80)`; then
   `rng.shuffle(topics)` on the 20 test topics in the order of their file; then `pos = [0, 1, 2, 3, 4] * 4` and
   `rng.shuffle(pos)`. Round r (0 to 19) holds `drawn[4r:4r+4]` in that order, with the trick clue (test topic r in the
   frame under test) inserted at index `pos[r]`. The code stops if no commit holds the line. Why a seed: no person
   chooses which real clue sits next to which control. Why that commit: it is unknown to everyone, the author included,
   until the record is merged, and the topics are fixed before the record, so no list of topics can be written, reworded
   or chosen for the draw it will get; and it is the first commit that holds the line, so a later commit cannot be
   picked to re-roll the draw. Why one draw for every frame: the frames are then compared on the same real clues, topics
   and positions, so a difference between frames is the frame's. Why the positions are balanced (each of the five holds
   the trick in 4 rounds) and not drawn one by one: a judge with a habit of picking one position scores exactly 4 of 20,
   the chance level, so a habit cannot make a frame fail.
3. Use: 80 of the 90 in the rounds, each in one round; the 10 not drawn go, sorted by id, to the frame writer (17.4.1)
   and to no round. All 90 are used, none in two roles. Why the writer gets only undrawn clues: a frame copied from a
   clue the judge also sees would echo it, a cue that has nothing to do with style.

### 17.3 The test topics

1. The 20 test topics are the probe topics of 15.5.5 (hand-written, never a candidate, never a control; 15.3.5 already
   drops a candidate equal to one, `control_topics.keep`). Why the same list: 20 is `PROBE_MAX`, one topic per round
   fits it, and no second list needs its own exclusion from the candidates (which would change `keep`).
2. Each is 4-16 CJK characters (`control_topics.TOPIC`), five in each of the lengths 4-6, 7-9, 10-12 and 13-16, and each
   survives 15.4.1 and 15.4.2 against the listing of 15.1.1 (`control_topics.survivors`; the titles that 15.2.7d names
   come later and are not in it, and a test topic that shares a sequence with one is still a test topic; the checks run
   before section 16 exists, on the listing file as given, and the code checks that file's hash and the `norm` mode
   against the topics record once it exists). Why the length bands: the frame must read like a real clue at every slot
   length a candidate can have. Why the two checks: a test topic that a real article covers would read as real and make
   a frame look better than it will be with the topics that ship, which all pass these checks. The author may rewrite a
   topic until it survives; this happens before the topics record, so no rewriting can see which real clue a topic will
   meet, and uses counts only.
3. The list is a private file in one canonical form (UTF-8, one topic per line, LF, no blank line, no space round a
   topic, one final LF); the code refuses any other form, so that whitespace cannot change its hash. Its sha256 is
   recorded as `probe-topics-sha256`, the label 15.5.5 uses, in a record of its own, the *topics record*, with
   `verdicts-sha256` and `norm-mode` (the listing and the rule for `norm` that the topic checks use) and
   `writer-prompt-sha256`, `checker-prompt-sha256` and `judge-prompt-sha256` (the prompts exist by then, reviewed with
   the script, and are pinned before any agent is asked); this record is merged on its own before the draw, and its
   merge commit seeds the draw (17.2.2). No later record repeats a label of this record, since the code takes the last
   value of a label and compares nothing; the script stops if a label it reads stands twice with different values.
   Before any record of this section is merged, a fresh agent recomputes each hash in it from the private files and
   reports each as equal or not; one that is not is a stop (17.7.5).

### 17.4 The frames

1. Writer: one fresh Opus agent of this harness (no knowledge of this test), given only: the four parts every frame
   holds (周易研究 as the one anchor; 15.5.3); one slot `{topic}` for a Chinese noun phrase of 4-16 characters; the length
   rule of 17.4.3; that the frame names no person, text, school, period or idea of 易学 and no topic (only words for what
   an article does: examines, traces, compares, assesses, and the like); and the 10 undrawn real clues as examples of
   style, with the instruction not to reuse any of their topic words. It returns frames 0-3 as a JSON list. The writer's
   prompt is kept in private results, sha256 recorded (17.8.2). A later request to the writer (17.4.3, 17.4.5) is a new
   fresh agent given the same inputs and, for each frame to be rewritten, its number and the reason it failed. Why an
   agent and not the author: the author's frame of 15.5.3 is the one under suspicion; a fresh writer that sees only
   style examples carries no knowledge of the listing. No template text exists before this section is carried out
   (15.5.3 has the author write one; none has been written), so the writer writes all four frames.
2. The four frames. Frame 0 (positive control, 17.7.1): the short sentence 15.5.3 describes, the four parts and the slot
   with the fewest ordinary words that make a sentence. Frames 1-3: longer and richer, each in a different structure:
   frame 1 a plain sentence lengthened with one clause saying what the article does; frame 2 two such clauses; frame 3
   the topic not at the start of the clause that holds it, as abstract paraphrases often place it. Why three, and why
   they differ in structure: the owner asked for longer and richer, which leaves the form open; three tries are enough
   to find one if the idea works and few enough that the test stays small (17.6.5 gives the cost in false passes). These
   descriptions of structure are public and carry no wording; the chosen frame is reported by its number only.
3. Code checks each frame: `control_topics.check_template` (the slot exactly once; a 16-character topic passes
   `bk.clue_format_check`, which rejects a Chinese clue over 120 characters); the four parts all present; no digit
   outside 2010年代 (as `clue_check`); the rest holds no title mark (《》〈〉) and no Latin letter; the frame ends with the
   full stop 。 (all 90 clues of the pool do, none holds a Latin letter, and 83 write the venue between title marks,
   which the rest rule allows round 周易研究 only); for frame 0 the fixed text is at most 40 characters, so that it is
   short; for frames 1-3 it is 56 to 72 characters. Why the title-mark and Latin rule: it stands where a "no second
   anchor" check would, since the venue branch of `clue_format_check` looks only for an author and a control has none
   (15.5.4's synthetic key), so it cannot fire; whether a frame names a person, another venue or a topic is for the
   checker (17.4.5). Why 56-72: the clue for a topic of 10 characters, the middle of 4-16, is then 66 to 82 characters,
   about the median of the 160 venue-anchored accepted clues (72; the pool's 73; all real clues: 69; counted
   2026-11-23), and the clue for any topic of 4-16 stays inside 60 to 88, inside 53 to 96, the range of the 160 (all
   real clues: 52 to 96), and under the 128 characters at which `build_keys.ds_search` cuts a query, so the search of
   15.4.4 never truncates it. Why the 160: in the battery a control sits among all real items, and the venue-anchored
   clues are the real clues of a control's kind. The bounds are public and equal what real clues show, so they tell a
   reader nothing about which clues are controls; a frame's own length stays private (15.5.3). A frame that fails gets
   one new request to the writer; a second failure drops it.
4. A second slot is not part of this test (17.9).
5. The frame's fixed words are not checked by 15.4 or 15.5.4, which read only the slot's text (`clue_check` applies
   `title_hit` to `slot_text`; 15.5.4). A richer frame adds words that no check compares with the listing, the risk
   15.5.3 names. So code lists, privately, every 3-character CJK sequence of each frame's rest (a space where a part
   was, so that no sequence spans a join) that occurs in a listing title or abstract (the rules of 15.4.1-15.4.2), with
   counts. A second fresh Opus agent of this harness (never the writer, never a judge) gets the frames, the content rule
   of 17.4.1 and that list as data, and returns per frame a verdict (passes or flagged, with the reason) and an English
   gloss of the fixed text; its prompt is kept in private results, sha256 recorded (17.8.2). A flagged frame is treated
   as one that fails 17.4.3 (one new request to the writer, then the code checks and this check again; a second failure
   drops it; a frame that was already rewritten for a failed code check is dropped when flagged). The owner gets the
   glosses, the verdicts and the counts per frame, in English, in chat only (private, never in the repository), and may
   ask to strike a frame before the record of 17.8.2; no one edits one. Why an agent and a gloss: the owner reads no
   Chinese (chat, 2026-11-23), so the gloss is the only form in which a person can check a frame; and a generic word
   (研究, 思想) will match titles, so a code rule would drop every frame, while a reader can tell a word of method from a
   topic. Why words of method do not weaken the absence claim: they narrow which article fits, they do not add a topic;
   a frame that adds a topic is the case the checker flags.
6. Dropped and struck frames. A frame is dropped when it fails twice (17.4.3, 17.4.5) and struck when the owner strikes
   it. If frame 0 is dropped or struck, the test stops before any judge call as **null: frame 0 not kept**; if no longer
   frame is kept it stops before any judge call as **null: no longer frame kept**, since frame 0 alone shows nothing
   about a longer one (17.7.3). Otherwise the frames kept are judged in their order (17.7).

### 17.5 A round

1. Five questions: four real clues and one trick clue (the frame under test, filled with a test topic), as 17.2.2 orders
   them, numbered 1 to 5. Why one trick question and not the owner's first "2-3": all controls share the frame, so two
   trick clues in one round would share its whole fixed text (56 characters or more for a longer frame), which two real
   clues are unlikely to share (UNRESOLVED: not measured); the judge would find them by the repetition, a cue no model
   under test has, since it sees each item alone (15.9.4). The owner chose this form in chat on 2026-11-23, on a
   question that gave the reason and the numbers, and that offered two tricks of one frame and one trick from each of
   three frames instead (the numbers of all three are in `frame_power.py`). Why five: four real questions are "a few
   more" than one, 20 rounds then use 80 of the 90 real clues, and chance stays at 1 in 5.
2. The judge: a fresh agent of this harness per round, never the writer: model `claude-opus-5-5`, effort `medium` (the
   model and the effort the harness gave its agents on 2026-11-23, read from their transcripts); a judge of another
   model or a lower effort is a change that needs a new deviation, since a weaker judge catches less and lets frames
   pass. It is started by an `Agent` call of the default agent type with the model `opus` and no other option (no
   `effort`, so the harness default applies, and its tools are not withdrawn: a tool call other than its return channel
   voids the round, 17.5.3), whose whole prompt is the round's prompt as the script wrote it; it is never a continuation
   of another agent. Fresh means no knowledge of this test or of an earlier round; it does carry the standing
   instructions the harness gives every agent, which the blind review of 17.8.1 reads in a judge's transcript (whether
   they bear on this test is a Gap until then, 17.11.5). It is told: these five questions each ask a model to name a
   journal article; four describe real articles that 周易研究 published in 2010-2019; exactly one is a trick question,
   describing a topic on which 周易研究 published nothing in 2010-2019, so it has no correct answer; answer from the text
   alone, without tools or search; return JSON `{"pick": n, "reason": "one sentence in English"}` (English because the
   owner reads it, 17.5.3). Nothing else: no listing, no frame, no word about how trick questions are made. Why tell it
   the count and the definition: a known count makes chance exact (1 in 5), and the definition is that of section 1 (a
   topic on which the journal published nothing in the decade), so the judge looks for what a control is. A model under
   test is told no such thing (§C.4: fakes are not mentioned), so a judge that is looking is the harder case: a frame
   that passes has passed more than the battery asks, and a frame that fails may still go unnoticed by a model that is
   not looking. The prompt around the questions is kept in private results, sha256 recorded (17.8.2).
3. What counts is read in code from the artifacts, the judge's transcript (tool calls; model and effort per turn; first
   user message; answer). The first user message is the `message.content` string of the transcript's first row of type
   `user`; the harness keeps its own reminders in separate rows. An agent hands its answer back through a tool call of
   its own, `SubagentHandback`, whose `message` is the answer; the answer is that of the last such call, or the text of
   the agent's last turn if it made none, and the ledger's copy of it must equal it (17.5.4). A round is void if the
   judge made any tool call other than `SubagentHandback`, if its model or effort is not the one of 17.5.2, if the first
   user message is not the round's prompt, or if `pick` in the answer is not an integer from 1 to 5 (not 0, 6 or a
   string). A void round is run once more, once, with a new fresh agent. A second void counts against what the frame is
   for: as a hit for frames 1-3 (it can only make a frame fail) and as a miss for frame 0 (it can only make the positive
   control fail). More than 3 of a frame's 20 rounds void at the first attempt is a stop (17.7.5): nothing is scored for
   that frame, since it is the judge or the harness that is failing and not the frame. If a transcript lacks a field the
   rules read (the model, the effort, the tool-call blocks, the first user message), scoring stops too and does not call
   the round void (the fields were present in the transcripts of this session's agents on 2026-11-23). The `reason` is
   kept privately, shown to the owner after the result, and decides nothing; a frame designed from the reasons is
   data-driven and needs a new deviation.
4. Every run is accounted for, the judges', the writer's and the checker's. The script writes the prompt of each round
   and of each request to the writer and the checker; each run is recorded as it ends in a private ledger (what it was
   for, agent id, time, reply), whose sha256 is reported with the counts. Scoring (for the writer and the checker, the
   closing of the frames) stops unless the transcripts folder holds one transcript for each recorded run and no other
   transcript whose first user message is one of the test's prompts: a run left out of the ledger, such as a frame run
   twice with one result kept or a writer asked again until the frames suit, would show. The first user message of each
   writer and checker transcript must equal the request the script wrote, so that a prompt changed after the review
   shows. This catches accidents, not intent: the folder is the harness's, held by the person who runs the test, and the
   repository gets only counts and the ledger's hash, so the check is for the private results' reader. Why: only counts
   are public, so the ledger and the transcripts must let a reader of the private results rebuild H.

### 17.6 The statistic and the decision rule

1. Per frame: H = hits in 20 rounds. Chance: 1/5 per round, so H is binomial(20, 0.2) if the judge cannot tell.
2. The judge can tell, and the frame fails, iff H >= 7. Otherwise the frame passes. `frame_power.py` computes 7 as the
   smallest t with P(H >= t) <= 0.10 at chance (P = 0.087; at 6 it is 0.196); the script recomputes it from that file
   and stops unless it is 7.
3. Why 0.10 and not 0.05: the costly error is a false pass, a frame that a model could notice used in all 24 controls; a
   frame wrongly failed costs only a try of the next one. A lower bar for "can tell" buys power against that error.
4. Power (`frame_power.py`): a judge whose pick is the trick 30%, 40%, 50%, 70% or 90% of the time is caught with
   probability 0.39, 0.75, 0.94, 0.9997, 1.0000. So a judge right 70% or 90% of the time is all but certain to be
   caught; one right 40% of the time (twice chance) passes a frame one time in four. A pass therefore excludes a strong
   difference, not a weak one; the label of 17.1.2 carries H so a reader can judge.
5. Trying up to three frames: if each were as detectable as a 40% judge, the chance that at least one passes is 0.58
   (0.16 at 50%). The stopping rule of 17.7 (first pass wins, no choosing among passes) avoids picking the luckiest of
   several, but not this. Stated, not corrected: a larger test is not what the owner asked for.
6. Nothing else enters the decision: not the reasons, not which real clues were picked when wrong, not a comparison of
   frames. Why: the rule must not read any real clue's content, and every extra reading is a new chance to call a frame
   good. H is reported as it comes, with frame 0's beside each other frame's. A very low H (1 or none of 20; chance
   0.07) would show a cue read the wrong way round; it changes no rule, and the owner is told.

### 17.7 Order, stopping, and a null

1. Frame 0 first (positive control). It is the short sentence 15.5.3 describes, the case the owner said a model might
   notice. If H < 7 for frame 0, the test cannot see the difference it was set up to see: it stops, frames 1-3 are not
   judged, and this is **null: frame 0 not caught** (17.7.3). Why: without it, a pass of a long frame could mean only
   that this judge cannot tell even the short one apart. It shows that the test can see a difference between a
   control and real clues, not that the frame is its cause (17.1.3), and not a small one: a judge right 35% of the time
   catches frame 0 with probability 0.58, and a frame as detectable as frame 0 then passes with probability 0.42
   (`frame_power.py`); so a pass whose H is near frame 0's is no evidence that the frame is better, and the label of
   17.1.2 carries both.
2. Then frames 1, 2, 3 in that order, 20 rounds each, the next only if the one before fails. The first frame that passes
   is chosen and no later frame is judged. Why a fixed order and first pass: choosing the best of several results would
   pick the luckiest. The script enforces the order from its own record of scores: a frame is not offered unless the
   frames before it have the scores this rule needs, since the judge calls are agent calls that it cannot make itself.
3. A null chooses nothing. There are five: **null: frame 0 not kept** and **null: no longer frame kept** (17.4.6, before
   any judge call), **null: frame 0 not caught** (17.7.1), **null: no longer frame passed** (every longer frame judged
   failed) and **null: stopped** (17.7.5). Each goes to the owner with H for each judged frame. No frame is edited,
   written anew, or judged again, no threshold or round form changes, and no further frame is tried without a new
   deviation recorded before its data. The owner decides the route: frame 0 as the template of 15.5.3, where it was
   kept, with the limit of 15.9.4 and this test's numbers beside it (section 15 as it stood before this section; after
   *no longer frame passed* it is a frame the judge could tell, so the limit is stated with every result; after *frame 0
   not caught* the test showed nothing about it); the second slot (17.9); a test of the topics alone, in which the trick
   is a real clue with its topic replaced by a test topic, which says whether any frame could pass (17.1.3; a new
   deviation); shortening the real clues, which the owner asked about and did not choose; or no controls.
4. A change after the first judge call (a judge failing to start, the harness changing model) is recorded as a new
   deviation in `PREREG.md`, with its reason, in a pull request merged before the rounds it affects are run or scored.
5. A stop is the script's refusal to go on, not a null, and nothing is scored or chosen. The stops: the pool is not 90
   (17.2.1); the topics file is not in its canonical form or fails its checks (17.3); no commit holds the topics
   record's line (17.2.2); the threshold recomputed from `frame_power.py` is not 7 (17.6.2); a record's hash is not
   equal to its file, whether the script or the fresh agent of 17.3.3 finds it (17.3.3, 17.8.2); a transcript lacks a
   field the scorer reads, or the ledger's copy of an answer differs from the transcript's (17.5.3); the ledger and the
   transcripts disagree (17.5.4); more than 3 of a frame's 20 rounds are void at the first attempt (17.5.3). The cause
   is written in the PR. A cause in the infrastructure (the harness changed its model or effort; a judge cannot run) may
   be put right and the frame's 20 rounds run again from the start, only under a deviation merged before them (17.7.4),
   the earlier runs staying in the ledger; any other cause goes to the owner. A stop that is not put right, and the
   owner's withholding of the go on the judge calls (17.8.1), end the test as **null: stopped**, with the cause, and the
   owner decides the route as after any null (17.7.3).

### 17.8 Where this sits in 15.7.6, and what a pass changes

1. Order (inserted into 15.7.6 between "code, checks" and "the first record of the addendum"): this section and
   deviation 9 merged, and the code of 15.7.1, which the script imports; the script of this test, its checks, and the
   three prompts (writer, checker, judge, with their placeholders) written, blind-reviewed as 15.7.4 says (the reviewer
   is given the prompts, from private results, and a judge's standing instructions as a transcript shows them), and
   merged; the 20 test topics written and checked (17.3); the topics record (17.3.3) merged; the draw (17.2.2); the
   frames written and checked (17.4.1-17.4.3) and read by the second agent (17.4.5); one dry round, a judge started as
   17.5.2 says on invented clues, whose transcript the script's reader must find valid (so that the rules of 17.5.3 are
   known to fit this harness before any real round); the owner reads the English glosses and counts in chat and gives
   the go for the judge calls, on a decision card; the record of 17.8.2, merged on its own; frame 0, then frames 1-3 as
   17.7 says; the result, counts only, to the PR and the owner. On a pass, 15.7.6 continues at "the first record of the
   addendum", with the chosen frame as the template.
2. The record, before the first judge call, as lines `- \`label\`: \`value\`` after the topics record in section 16 (the
   form `control_topics.registered` reads, and the `## 16.` heading is written with the topics record, which makes that
   the first record of section 16, this one the second, and the one 15.5.5 and 15.7.5 describe the third, merged on its
   own before the probe as 15.5.5 says). Labels: `seed-commit` (the commit of 17.2.2), `drawn-sha256` (the drawn ids in
   draw order, one per line), `pool-file-1-sha256` to `pool-file-4-sha256` (the item files), `pool-count` (90),
   `frame-0-sha256` to `frame-3-sha256` (each frame kept), `judge-model`, `judge-effort` and `threshold` (7); the
   prompts' hashes stand in the topics record (17.3.3). The seed is the one of 17.2.2. What exists only after the judge
   calls (the ledger, the results, the transcripts) is reported with the counts (17.5.4), not recorded here. The record
   is merged on its own: a squash keeps the content, and the merge before the first call is the proof of order (as
   15.5.5).
3. A pass: the chosen frame becomes the template of the third record (15.5.5, 15.7.5); its `template-sha256` there must
   equal the `frame-N-sha256` recorded for it in 17.8.2, which the script checks before the probe. Its lengths go to the
   owner next to the real clues' (15.5.3).
4. Unchanged for the chosen frame: the template probe of 15.5.5 (at most 20 searches on clues from the probe topics,
   which are the test topics; the number of clues 15.4.4 would drop goes to the owner with the budget question; a high
   number is a reason for a new deviation before the freeze, never a relaxation); 15.5.4; 15.4.4 (a longer clue is a
   different search, so the probe's number may differ from what the short frame would give); every check of 15.4 on the
   slot's text; the walk, the seed and the bar of 15.6. A template change after the probe needs the owner's decision and
   a new probe on new topics (15.5.5); the new topics are also test topics, so it needs a new test of this section on
   the new frame with them.
5. Checks for the test's script: synthetic data, no network, `python3 -I`, non-zero exit on failure; per rule of
   17.2-17.7 one case that must pass and one that must fail. Mutations, each shown red and recorded in the PR
   (`.claude/rules/verify-a-check-by-breaking-it.md`): pool count not enforced; an id kept that occurs in two runs; a
   pool condition off (the stratum, the venue, the year, the anchor, or either string after `norm`); the topics file
   accepted in another form; the five-per-band rule off; the survivors check off; the seed without the commit; the seed
   taken from a later commit; the draw with replacement; positions drawn one by one; a round with two tricks; a real
   clue in two rounds; an undrawn clue in a round; the length bounds off, for frame 0 and for frames 1-3; the full-stop
   rule off; the four-parts check off; the digit check off; the title-mark and Latin rule off; a 3-character sequence
   taken across a join; `check_template` off; a frame kept after its second failure; a frame kept that the checker
   flagged; a frame already rewritten and then flagged kept; a struck frame kept; frame 0 judged when no longer frame is
   kept; frames 1-3 judged after frame 0 was not caught; a frame judged after an earlier one passed; frames out of
   order; a second void counted as a miss for frames 1-3, or as a hit for frame 0; more than one re-run of a void round;
   a `pick` of 0, 6, a string or a boolean accepted; a tool call not voiding; `SubagentHandback` voiding; a wrong model,
   a wrong effort or a wrong first message not voiding; the answer taken from the ledger and not the transcript; a
   missing transcript field counted as a void; more than 3 void rounds scored; a run left out of the ledger not caught,
   for a judge, the writer or the checker; the first message of a writer or checker transcript not compared; a recorded
   run without a transcript not caught; a label stated twice with different values accepted; the threshold not
   recomputed, or 8 for 7; a verdict not read from the count of hits; scoring that reads clue text. The scorer checks
   the order of frames from its own record, since the judge calls are not the script's. A green mutant is written down
   as a weak check or as covered elsewhere.

### 17.9 Fallback: a second slot (not part of this test; the owner's decision)

If the owner chooses this route after a null, a new deviation would let a frame hold a second slot, filled with a
drafted aspect (such as a method or a source type) instead of fixed words, so that each control's framing differs. It
changes: 15.3.3 (the prompt drafts pairs), 15.3.5 and 15.5.1 (keeping and ordering pairs), 15.4.1-15.4.2 and 15.5.4
(applied to each slot's text), 15.5.3 (one slot), and the parts of `control_topics.py` and its checks that build, check
and order a clue from one slot. It needs its own test of this section on new frames before any data.

### 17.10 Privacy and cost

1. Private (the work directory of 15.1.4, which the code refuses inside a work tree of this repository,
   `control_topics.guard_workdir`): the test topics, the frames, the writer's, checker's and judge's prompts, the 90
   pool clues and the draw, every round as shown, every judge reply and transcript, the ledger and the results, the list
   of 17.4.5, the checker's verdicts and glosses (the glosses reach the owner in chat only, since a gloss restates the
   frame). The repository gets counts (pool, drawn, frames dropped by code, by the checker or by the owner, rounds,
   voids, H per frame) and each private text's sha256. Why: a public frame or topic would show a future model which
   clues are controls (15.1.4).
2. No outside model sees a real clue. Calls, all agents of this harness: the writer 1 (at most 5, with one new request
   per frame, 17.4.3); the checker 1 (at most 5, with the re-checks of 17.4.5); judge rounds 20 for frame 0 plus 20 per
   frame tried, at most 80, and at most one re-run per round, so at most 160; at most 170 in all, besides one dry round
   (17.8.1), one fresh agent per record to recompute its hashes (17.3.3; at most three) and the blind reviewers of
   17.8.1 (15.7.4's). No money is spent outside the harness.

### 17.11 What was checked before writing, and what was not

Dated 2026-11-23; no frame, topic or judge exists. The scripts named here are kept in private results, with their
sha256 in PR 54.
1. GROUNDED (counted on the private item files with the rule of 17.2.1 as written; counts only): the pool is 90; 7 ids
   occur in two runs, each with a different clue; 94 rows meet the rule and give 92 ids; the 160 venue-anchored clues
   are 53 to 96 characters (median 72), the 90 of the pool 54 to 96 (median 73); all 90 carry 期刊论文, 85 carry 易学, 83
   write the venue between title marks, all 90 end with 。 and none holds a Latin letter.
2. GROUNDED: the bar and the power are the exact sums of `frame_power.py`, recomputed by direct tail sums and by 400,000
   simulated tests; a judge with a fixed position habit scores exactly 4 of 20 under the balanced positions of 17.2.2,
   and a lopsided one fails a frame less often than chance (0.070 against 0.087, simulated).
3. GROUNDED: the names this section cites exist in the code of PR 53 (read 2026-11-23: `control_topics.py`,
   `build_keys.py`); the transcripts of this session's agents hold `message.model`, `effort` and `perTurnEffort` (model
   `claude-opus-5-5`, effort `medium`); the first row of type `user` of a transcript holds the prompt as a string and
   equals it, the harness's reminders being separate rows of type `attachment`; an agent returns its answer through a
   `SubagentHandback` call whose input is `message` (read 2026-11-23 on the transcripts of four agents).
4. UNRESOLVED: whether 5 topics of each length band survive 15.4.1-15.4.2. A pilot of the same day, with topics the
   author wrote for it and then discarded, found survivors against the real listing in every band when it kept clear of
   the journal's own vocabulary (10 of 12 candidates at 4-6 characters, 19 of 27 at 7-9, 11 of 19 at 10-12, 10 of 18 at
   13-16); the topics that ship were drafted by another route.
5. Gap: how a model under test reads the frames; how much of a judge's pick is the topic and how much the frame
   (17.1.3); that the code finds a pool of 90 in the files it reads (it stops unless it does); what the harness's
   standing instructions for agents hold (the blind review reads them).
