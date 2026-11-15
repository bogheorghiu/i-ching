# Battery 2 other cells, design pass 4: English articles only, probes only

Status: **probe plan (sections 1-4) and frozen parser `other-cells-probe/kyoto4.py`, committed before any
pass-4 candidate was drawn or fetched; results in sections 6-9.** Owner's verdict "a" on board card `d-b2-cells-pass4`, given in
chat on 2026-11-15. Method and rule as in `OTHER-CELLS-DESIGN.md` sections 1 and 4 and the pass-2 and
pass-3 notes; this file changes only what it says. Nothing is built, no model is called. Books are not
retried (owner's choice). Cap: 60 fetch calls. Saved responses go only to the private branch
`battery2-keys` of `bogheorghiu/delegation-results`. Candidates are named by identifier only.

## 1. What was done and seen before this was written

- **No new fetch.** The parser was fixed on the 56 `OU` files saved in pass 3 (Moonshot responses of
  2026-11-15). Fixes, all three found by pass 3's blind review: issue headers of both forms (a letter
  and six digits, or a letter, four digits, a dash and five digits); authors tagged `$a` or `$A`;
  Crossref titles stripped of HTML markup before `nrm`. Checked by code, structure only: no header-like
  line is left unmatched; 16,718 article records, 11,292 with title, author, year and journal code;
  **9 blocks with *Early China*'s code `420300`, 54 records, dated 1998-1999 to 2010-2011**
  (`OU009, 011, 014, 023, 032, 033, 037, 039`). This session did not read the titles in those blocks.
  Pass 3's blind reviewer did read some of them while checking pass 3; the pass-4 draw comes from
  Crossref's order, not from Kyoto, so that reading cannot steer which candidates are drawn.

## 2. The arm

| Arm | Enumeration | Record A (API) | Record B (API) | Route to B |
|---|---|---|---|---|
| E-kyoto4 | Crossref `journals/0362-5028/works?rows=100&select=DOI,title,author,issued,volume,page&filter=from-pub-date:1998,until-pub-date:2011` (DeepSeek) | Cambridge Core page by PII, parser `camb` (DeepSeek) | the saved `OU001-058` Moonshot responses of pass 3; `OU030` and `OU058`, which did not open then, are asked for again (Moonshot, three tries each) | as pass 3, with `kyoto4.ou_parse`: articles in `420300` blocks whose `$t` matches the markup-stripped Crossref title (`nrm` equal, or prefix with the shorter at least 15 characters); two or more matches count as not yielding |

**Candidates.** The first eight entries in Crossref's default order that have `author` and `page`, are
not among the 20 DOIs spent in passes 1-3, and whose markup-stripped title does not match (case-
insensitive) `\bpp\b|\bISBN\b|\bpress\b|\b(19|20)\d\d\.\s|in memoriam|obituary|summary of japanese
scholarship|\breview\b`. Why: pass 3's draw held a book review, an obituary, two review articles and an
annual summary, and the filter is meant to leave research articles. Fewer than five: "too thin".

**Record B full:** `$t`, the first author line, venue "Early China" (from the code, via `rjnl.txt`),
and the block's `$d`, all non-empty.

## 3. Endpoint, rule, voids

As before: A full, B full, both; **viable at 4 of 8**, marginal 2-3, not viable 0-1. Reported, not
part of the rule: title and year agreement (year: first four digits of `$d` against record A's year;
a block dated "2001-2002" counts as 2001); how many candidates have any `420300` record at all; and
how many of the 8 fall in years Kyoto's blocks cover. A 401, 402 or 429 voids the run; a 5xx or
"failed to fetch" gets two more tries, then counts as not yielding.

## 4. What a result obliges, and who decides

A viable result makes the Kyoto bibliography a new custodian class: it goes back to the owner as its
own decision card on the i-ching board, with evidence of who operates the dataset, **before any item
is built** (and a PREREG deviation would be needed). Anything else is reported with counts and
identifiers. No parser change after the draw, no swapped candidates, no re-derived success; any
deviation is recorded below with its reason before the result it touches is scored. Report: a note in
a PR here and a comment on issue #33.

## 5. Deviations from this plan

(none yet)

## 6. Results (scored by `other-cells-probe/probe_p4.py` from saved responses)

The candidates named here were seen by this session and are in a public file: **keep them out of any
item set.**

| Arm | Enumeration | Cands | A full | B full | Both | Verdict by the rule |
|---|---|---|---|---|---|---|
| E-kyoto4 | Crossref 1998-2011: 187 works, 100 returned, 14 eligible | 8 | 7 | 3 | **2 of 8** | marginal |

- **Record B.** 56 of 58 `OU` files read (the saved pass-3 responses); `OU030` and `OU058` refused
  again ("security risk", three new tries each). The `420300` blocks hold 54 records with years 1998,
  2000, 2001, 2003, 2004, 2005, 2007, 2008 and 2010 (first year of each block). The route found exactly
  one record for 3 of the 8 candidates and none for 5.
- **Record A.** Cambridge through DeepSeek: 7 of 8 full; 10.1017/s0362502800000985 gave no author line.
  That is the third candidate with a Kyoto record, so "both" is 2.
- **Agreement (reported, not part of the rule):** both "both" pairs agree on title and year.
- **Correction from the blind review: the route, not Kyoto, missed three of the five.** Kyoto's
  `420300` blocks do hold …7094 (`OU023`, 2004), …7264 (`OU011`, 2001-2002) and …1796 (`OU037`, 2007),
  each with title, author and year. The route missed them because the two titles differ: a misspelling
  in Crossref's title (…7094), a one-word slip in Kyoto's (…7264), and Chinese characters that Kyoto
  inserts into an English title and `nrm` keeps (…1796). Checked by this session too (similarity of the
  normalised titles 0.96, 0.98, and 1.00 with CJK characters removed). The other two misses, …064x and
  …7045, are **obituaries** (titled "Name (dates)"), which the filter did not catch, and are not in Kyoto
  under any code. So Kyoto holds all 6 research articles of the 8. The score stays 2 of 8: section 4
  forbids rescoring.
- Candidates: DOIs 10.1017/s036250280000064x, 10.1017/s0362502800007094, 10.1017/s0362502800007264,
  10.1017/s0362502800001796, 10.1017/s0362502800000985, 10.1017/s0362502800007045,
  10.1017/s0362502800002169, 10.1017/s0362502800000651.

## 7. What this means (for the owner; this session decides nothing)

- **Not coverage, but exact title matching, limited this draw.** Kyoto holds all 6 research articles
  drawn; the filter let 2 obituaries in; the route lost 3 of the 6 on small title differences.
- **That limit would not go away by loosening the route alone** (this session's reading, not the
  reviewer's): the design drops an item when its two records disagree on title (`final-design.md` A.5,
  "any mismatch drops the item"). Two of the three misses are real disagreements between the records
  (a misspelling on one side, a different word on the other), so they would be dropped at the
  comparison even if the route found them. Only the CJK case (…1796) is a reading problem that a
  normalisation rule (drop CJK characters from both titles before comparing) would fix without
  accepting disagreeing records. Counted that way, this draw would read **3 of 8**: still marginal.
  Getting above that means accepting near-equal titles as agreeing, which changes what a key
  guarantees, and is the owner's decision, not a parser fix.
- English books stay marginal for coverage (5 of 8 ISBNs absent from K10plus in pass 3).
- No arm is viable, so no custodian card is required. A card goes to the board with the real choice:
  close the four cells, or change the comparison rule (near-equal titles) and test it on a fresh draw.

## 8. Spend

15 fetch calls: 1 Crossref and 8 Cambridge (DeepSeek), 6 Kyoto retries (Moonshot); the other 56 Kyoto
files are pass 3's saved responses, reused without a new call. No search, no model call.

## 9. Not checked

- Whether the Kyoto files came through complete; the two refused files may hold *Early China* records.
- Which Western journals Kyoto indexes densely enough for a pair.
- The obituary filter's miss: pass 4's filter does not catch titles of the form "Name (dates)".
- A blind review ran (a fresh agent given the diff and the saved files): it confirmed every scored
  figure, the commit order and the scripts, and found the route's three misses and the obituaries;
  sections 6-7 are corrected from it. `probe_p4.py` was committed with the results, not before the
  draw (the plan froze only the parser); the reviewer found it implements section 2 exactly.
