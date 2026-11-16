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
