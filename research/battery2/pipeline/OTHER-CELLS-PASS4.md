# Battery 2 other cells, design pass 4: English articles only, probes only

Status: **probe plan, committed (with the frozen parser `other-cells-probe/kyoto4.py`) before any
pass-4 candidate was drawn or fetched.** Owner's verdict "a" on board card `d-b2-cells-pass4`, given in
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
