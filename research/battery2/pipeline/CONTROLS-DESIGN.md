# Battery 2 negative controls: design and feasibility probe

Written 2026-11-16, before any control is built and before the probe in section 4 fetches anything. The owner
marked negative controls "next" on the plan page (`steer/current`, version 3). Sections 1-4 are frozen once
committed; results and corrections go in later sections.

## 1. What the design asks for, and what this pool can give

`design/final-design.md` §B asks for 24 controls, interleaved with the real items and matched in style:

- **issue probes**: an article on a plausible topic in an issue whose complete table of contents (TOC) two
  custodians agree on;
- **author probes**: a real scholar paired with a topic absent from two agreeing complete bibliographies of
  that scholar;
- absence decided in code, as non-membership in the extracted TOC or bibliography, never from zero search hits.

Every real item is a 周易研究 article, 2012 or later, and every clue gives one anchor and a decade
(`design/final-design.md` §C.1). Two facts bear on the controls:

1. **No complete bibliography of any scholar is reachable.** CNKI author pages block non-mainland IPs
   (PATCH-5 record of 2026-11-09), and no other source tried lists a scholar's complete output. The design kept
   author probes "only with two agreeing complete bibliographies" (§G); that condition cannot be met.
2. **The two page readers do not give the same TOC.** Section 2.

## 2. Reader audit of the stored CASS TOC pages (exploratory, report-only)

Run 2026-11-16 on snapshots already saved on `battery2-keys` (no new fetch). The 13 yearly 周易研究 TOC pages on
`iwr.cass.cn` (2012-2024) each have a copy through DeepSeek's fetch and one through Moonshot's. Unit: an entry
line (holds `/` and CJK), compared after normalisation.

| Years | Pages | Lines only in the Moonshot copy | Lines only in the DeepSeek copy |
|---|---|---|---|
| 2012-2017 | 6 | 0 | 0 |
| 2018-2024 | 7 | 70 (4 to 21 per page) | 1 |

Example, 2021 issue 1: the DeepSeek copy lists 8 entries and goes straight from one section heading to the next;
the Moonshot copy lists 15. The seven missing lines are articles CNKI also holds (`CJFDTotal-ZYJY202101005` to
`011`). So the earlier reading "the CASS TOC lists only some articles" is wrong for this page: the page is
complete and one reader dropped lines.

What this does and does not show:
- Seen on these 13 pages only, on copies made 2026-11-08/09. Not a property of either fetcher elsewhere.
- No accepted key is affected: a missing record-B line can only drop an item, never pass one.
- `seed_from_toc.py` read the TOCs through DeepSeek, so seeding missed the dropped articles. They were never
  candidates; nothing was built from them.
- It bears on the two-readers rule the owner kept on 2026-11-15: on 7 of 13 pages one reader silently lost
  entries. A control's absence claim is exactly the case where a lost line turns into a false result.

## 3. Proposal

**3.1 All 24 controls are venue probes; author probes are not built.** Reason: section 1, fact 1. A venue
probe has the real items' own clue shape (work type, field, topic, the venue as the one anchor, a decade), so
it is matched in style by construction. An issue-level probe ("2021 issue 1") would carry a detail no real clue
carries, and a model could learn to treat that detail as a tell.

**3.2 Absence over a whole decade of the journal.** A control says "an article in 周易研究 in the 2010s (or
2020s) on topic T". The listing it is checked against is every entry of every issue of that decade.

- **Listing.** For each year, the union of the entry lines of the two readers' copies of the CASS yearly TOC.
  Why the union: an absence claim is safer against the longer list, and in section 2 one reader only ever lost
  lines (70 against 1).
- **A year is usable** when both copies open, all six issue headers are found in at least one copy, and every
  CNKI article page probed for that year (the `seed_from_toc.py` probes already saved) has its title in the
  union, except pages whose title marks them as notices (书讯, 简介, 选题, 征订, 稿约, 目录, 启事).
- **A decade is usable** when every year in it, up to the latest complete issue, is usable.

**3.3 Topics.** A model drafts candidate topics for the journal's field, from the journal's own section
headings, never from any item's record. Code rejects a candidate that shares a 3-character CJK n-gram with any
entry title in the decade's listing (the leakage rule of §C.2, applied to the whole listing). The identifiability
check of §C.3 runs on what is left: a candidate whose clue brings up, in the search API's top 10, an article of
the journal in that decade is dropped. Neither check approves a topic; each only drops.

**3.4 What a control failure is, decided in code.** An answer whose venue is 周易研究 and whose year falls in
the decade, and whose title is not in that decade's listing (after `norm`), is **invented**: a control failure
by code. An answer naming a title that is in the listing goes to the adjudication queue as a possible
wrong-real (the topic fit is a judgement; §D gives control failures first priority there). Any other answer is
scored as for real items.

## 4. Feasibility probe, and its bar

The stored pages cover 2012-2024. Missing for the two decades: 2010, 2011, 2025 and, if any issue is out,
2026.

- **Probe.** Find the CASS yearly TOC pages for 2010, 2011 and 2025 (and 2026 if listed), and fetch each through
  both readers. For those years, probe the CNKI article ids issue by issue as `seed_from_toc.py` does (same id
  pattern, same stop rule: four misses in a row after the fifth id, at most 25 ids per issue). Order: the 2020s
  years first, then 2010, then 2011. Then apply 3.2 to every year 2010-2025, using the saved CNKI probes for
  2012-2024.
- **Calls.** At most 250 fetches in all; when the cap is reached the probe stops, and every year not finished
  counts as not usable. No model call. DeepSeek's fetch price is not recorded (the same Gap as in PATCH-5).
- **Bar, fixed now.** Proposal 3 goes to the owner as buildable when **at least one decade is usable** under
  3.2. Otherwise the result is reported as a null, and the card offers fewer controls (from usable years only,
  with a narrower year span in the clue) or a deviation to the control count.
- **What it cannot see.** Whether the CASS page itself omits an article that both readers then agree is
  absent. The CNKI probe is the only check on that, and it only reaches articles CNKI numbers in sequence.

Saved responses go to the private branch `battery2-keys`, folder `controls-probe-2026-11-16/`.

## 5. Result (2026-11-16): null, no usable decade

**Calls.** 13 fetches (DeepSeek: 3, all HTTP 200; Moonshot: 10, of which 8 were HTTP 504, 1 was 404 and 1 was 200)
and 1 Exa search. No model call. No CNKI id was probed: once a year has only one copy, 3.2 makes it unusable,
and probing could not change that.

**Pages found.** The CASS index lists yearly pages for 2015-2024 on page 1. An Exa search found the 2011 page at
`iwr.cssn.cn/.../t20240928_5788107.shtml`; the 2010 page is `..._5788106.shtml` (its DeepSeek copy is headed
2010). **No 2025 page exists in the index**, read through both readers on 2026-11-16.

**By the rule of 3.2:**

| Decade | Outcome | Reason |
|---|---|---|
| 2020s | not usable | no 2025 page |
| 2010s | not usable | 2010 and 2011 have a DeepSeek copy only: Moonshot returned HTTP 504 on both pages, on both hosts, on a first try and on one retry 30 s later (8 calls; the first-try snapshots were moved aside, not deleted) |

Applied to the 13 years with two saved copies (2012-2024, using the CNKI probes already saved), **no year is
usable**: every year has both copies and all six issue headers, but between 3 and 18 CNKI probe pages per year
have a title that is neither in the union of entry lines nor marked as a notice.

**The bar (section 4) is not met: the result is a null.** Proposal 3 does not go to the owner as buildable.

**Read after the result; it changes nothing above.** Of 9 unmatched CNKI pages looked at by hand, 7 are not
articles but fall outside the notice list (obituaries, 悼念; conference reports; an editor's introduction; a
group photo), and 2 are articles whose TOC entry wraps the subtitle onto a second line. The line reader of 3.2
keeps only lines holding `/`, so it loses the main-title line of a wrapped entry. That is a fault in the reader
written for this probe, not evidence that the CASS pages leave articles out. Fixing either fault now, on the
pages that showed it, would shape the rule to a result already seen; the next step goes to the owner instead
(card `d-b2-controls-next`).

**Not checked.** Whether the 2010 and 2011 pages open through Moonshot at another time; whether any page
leaves out an article that CNKI does not number in sequence.

Saved responses: held in this session's scratchpad until they can be pushed to `battery2-keys`, folder
`controls-probe-2026-11-16/` (this session has read access only to that branch; see the PR).

## 6. Corrections after blind review (2026-11-16)

A fresh agent reviewed sections 1-5 against `main` (no web content). Sections 1-5 are left as written; these
corrections replace the sentences they name.

**When sections 1-4 were frozen.** Commit `a95b7ab` on this branch, pushed before the first probe fetch; section
5 is commit `5df672d`.

**The bar could not be met, and I could have known.** The CNKI condition in 3.2 (no unmatched non-notice page in
a year) fails for every year with saved probes. PATCH-5 had already recorded unmatched CNKI pages for these
years (notices, columns, obituaries), and before writing section 4 I had counted, from the same saved seed
logs, that no issue had zero unmatched pages. So the 2012-2024 part of the result was knowable before the
bar was set, and the null says nothing about whether controls can be built. What the probe did add: the state of
the 2010, 2011 and 2025 pages.

**Departures from `final-design.md` that section 3 did not name.** §B asks for a complete TOC that two
custodians agree on, with continuous pagination. Proposal 3 uses one custodian (CASS) read through two
fetchers, takes the union of the two copies rather than their agreement, and checks no pagination. 3.1 replaces
issue probes and author probes with venue probes, which §B does not define; §G kept author probes on a
condition. Any of this would need a PREREG deviation before a control is built. Since the result is a null,
none is proposed.

**Author probes.** Section 1 says CNKI author pages block non-mainland IPs, citing PATCH-5. That is not in
PATCH-5. The record (issue #33, 2026-11-09 17:09) says the CNKI article *detail* page blocks non-mainland IPs;
author pages were not tried. Whether a complete bibliography of a scholar is reachable is UNRESOLVED, so the
reason given for dropping author probes does not hold as written.

**Other sentences.**
- Section 2, "the page is complete": what is shown is that the DeepSeek copy lost 7 lines the Moonshot copy
  has. Whether the Moonshot copy lists every article of 2021 issue 1 was not checked.
- 3.2, "one reader only ever lost lines": the DeepSeek copy also had 1 line the Moonshot copy lacked.
- Section 2, "They were never candidates; nothing was built from them": CONTRADICTED. 6 of the 70 lost lines are
  accepted items, seeded from the owner's Kimi lists, not from the TOC. No key is affected: since deviation 4,
  every accepted item's record B is the Moonshot copy, which has those lines.
- Section 2, "the two-readers rule the owner kept on 2026-11-15": the rule is PREREG deviation 4 (2026-11-09).
  The 2026-11-15 hand-off on issue #33 records the owner saying it stays.
- Section 4, "the same Gap as in PATCH-5": PATCH-5's Gap is DeepSeek clue-call prices; DeepSeek fetch prices are
  a separate, also unrecorded, figure.
- Section 5, "No 2025 page exists in the index": only page 1 of the index was read, and the next id in sequence
  (`t20240928_5788121`) was not tried. Absence is not established; the 2020s fail on 2020-2024 anyway.
- Section 5: the Moonshot retry and the second host were decided after launch and are not in section 4. The
  Moonshot 404 is the index's page 2 (`index_1.shtml`), which returned "No text/markdown content".
- Section 5, "a fault in the reader written for this probe, not evidence that the CASS pages leave articles
  out": 9 of at least 39 unmatched pages were read, picked by hand. Supported: none of those 9 shows an
  omission. The reader also lacks the wrapped-subtitle handling that `build_keys.toc_entry` already has.

**For a later design, not acted on here.** 3.4 calls an answer invented on an exact title miss, while §D judges
titles by similarity, so a near-verbatim real title would count as a control failure; and §D makes any
wrong-real answer on a control a failure, which 3.4 softened. Section 4's bar never tested whether 3.3 leaves
any topics.

**Raw evidence.** The probe's snapshots are still only in this session's scratchpad. They go to `battery2-keys`
once this session can push there (asked on the PR); until then they can be lost if the session ends.
