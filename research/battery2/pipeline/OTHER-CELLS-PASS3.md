# Battery 2 other cells, design pass 3: probes only

Status: **probe plan (sections 1-5, committed before any candidate record was fetched) and its results (sections 6-9).** Owner's verdict "a" on board
card `d-b2-cells-pass3`, given in chat on 2026-11-15. Method and rule as in `OTHER-CELLS-DESIGN.md`
sections 1 and 4 and `OTHER-CELLS-PASS2.md`; this file changes only what it says. Nothing is built, no
model is called. Cap: 300 fetch calls for the pass, reachability included. Chinese books 1987-1999 stay
out of scope (owner, 2026-11-15). Saved responses go only to the private branch `battery2-keys` of
`bogheorghiu/delegation-results`. Candidates are named by identifier only.

## 1. What was seen before this was written (reachability, 2026-11-15)

17 fetch calls through Moonshot, plus the pass-2 snapshots (already on the private branch).

- **Kyoto dataset layout** (GitLab API repository trees, all pages): `ruimoku-papers` (2001 onward)
  holds `CHU001-518` (Chinese), `WA001-184` (Japanese), `OU001-058` (Western languages), `KIN001-008`
  and a few supplement files; `ruimoku-old` (1981-2000) holds at least 270 `RUI` files (tree pages after the third not listed), `OBN00186-00199`,
  `OOBUN001-011`, `JOURNAL1-3`, `CYUKISO1`.
- **Formats.** From pass-2 snapshots: `RUI001.txt` (Chinese articles, full-width, numbered lines: an
  issue line `010`, `020 $j<journal code>`, `$g` volume, `$d` year, then `100 nnnnn` article lines with
  `$t` title, `$a` author, `$p` pages) and `rjnl.txt` (journal index: `$<code>$i..$a<name>% (<place>)`;
  *Early China* is code `420300`). Fetched now: `ruimoku-old/OBN00186.txt` (14 kB; Western **books**,
  `510`/`521`/`541` records, titles wrapped onto continuation lines, no `$j` codes) and
  `ruimoku-papers/OU001.txt` (29 kB; Western articles 2001 onward, half-width: an issue header such as
  a letter and six digits, then `$j` journal code, `$k`, `$g` issue, `$d` year; then an eight-digit
  article id line, `$t` title, `$a` author, `$z`, `$p` pages, `$b`, `$c`; 49 `$j` codes, none `420300`).
- **Not reachable:** `ruimoku-old/OOBUN001.txt` (502 three times) and `OOBUN011.txt` (Moonshot
  "security risk"). These are presumably the 1981-2000 Western articles; so pass 2's 1996-2000 *Early
  China* window cannot be paired with Kyoto now, and pass 3 uses 2001 onward.

## 2. Arms

| Arm | Cell | Enumeration | Record A (API) | Record B (API) | Route to B |
|---|---|---|---|---|---|
| E-kyoto | English articles (*Early China*, 2001-2009) | Crossref `journals/0362-5028/works?rows=40&select=DOI,title,author,issued,volume,page&filter=from-pub-date:2001,until-pub-date:2009` (DeepSeek) | Cambridge Core page by PII, parser `camb` (DeepSeek) | Kyoto `ruimoku-papers/OU0nn.txt` (Moonshot) | issue blocks whose `$j` is `420300`; the article in them whose `$t` matches Crossref's title |
| N-en/K776 | English books | the pass-2 N-en union (same four CiNii lists, read from the pass-2 snapshots, no new fetch); candidates are **eligible entries 9-16** (1-8 are spent) | CiNii `ncid/<id>.json` (DeepSeek) | K10plus SRU `marcxml` (Moonshot) | record A's first ISBN |

**E-kyoto candidates.** First eight Crossref entries in default order with `author` and `page` and whose
title does not match `\bpp\.|\bISBN\b` (case-insensitive), a filter added after pass 2 found book reviews
among the candidates. If fewer than five, "enumeration too thin".

**E-kyoto route, fixed now.** Files are read in order `OU001` ... `OU058` through Moonshot, up to three
tries each, and the scan stops when every candidate has a match or the files run out. Text is
NFKC-normalised. A line of a letter and six digits opens an issue block; its `$j` and `$d` lines give
journal code and year; an eight-digit line opens an article; `$t` and `$a` lines belong to the open
article; a line that is none of these is appended to the previous field (a wrapped title). A candidate
matches an article in a `420300` block when `nrm($t)` equals `nrm(Crossref title)` or one is a prefix
of the other and the shorter is at least 15 characters; two or more matches count as not yielding.
**Record B full:** `$t`, the first `$a`, venue "Early China" (from the code, via `rjnl.txt`), and the
block's `$d`, all non-empty. A file that does not open is counted and named; if no `420300` block is
found in any file read, E-kyoto is a null.

**N-en/K776 same-book rule, fixed now (the new rule the card names).** Record B counts as the same book
when an `020 a` value **or a `776 z` value** holds the ISBN asked for (ISBN-10 and -13 forms of one
number are the same, as in pass 2 deviation 1). Fields otherwise as pass 2 (245 `a`; 100/700 `a` or 245
`c`; 264/260 `b` and `c`; no 880). Reported beside it: the count under pass 2's 020-only rule.

## 3. Endpoint, rule, voids

As pass 2: A full, B full, both; viable at 4 of 8 or more, marginal 2-3, not viable 0-1 or record B's
host unopened (a null with statuses). Reported, not part of the rule: title and year agreement under
`nrm`; how many OU files were read and which failed; how many `420300` blocks were found and their
years. A 401, 402 or 429 voids the run; a 5xx or "failed to fetch" gets two more tries, then counts as
not yielding.

## 4. What a result obliges, and who decides

A viable E-kyoto would make Kyoto a new custodian: it goes back to the owner as its own decision card
on the i-ching board, with the evidence of who operates the dataset, **before any item is built**. A
viable N-en/K776 changes the same-book rule, so it also goes to the owner as a card. Anything else is
reported with counts and identifiers; no second parser pass, no swapped candidates, no re-derived
success. A change to sections 2-3 after the first candidate fetch is recorded below with its reason
before the arm it touches is scored. The report is a note in a PR here and a comment on issue #33.

## 5. Deviations from this plan

1. **2026-11-15, after both arms were scored (E-kyoto: 0 of 8; one `420300` block, in `OU009`, year
   2000, holding 319 parsed records): two looks outside the rule, which score nothing.** (a) Whether the
   319 records really belong to one *Early China* issue, or the parser ran past a block boundary it did
   not recognise: the lines of `OU009` around the block are read by code. (b) Whether any of the eight
   candidate titles occurs anywhere in the 56 saved `OU` files, under any journal code: `nrm` of the
   first 30 characters of each Crossref title, searched in `nrm` of each file. No new fetch.

## 6. Results (scored by `other-cells-probe/probe_p3.py` from saved responses)

The candidates named here were seen by this session and are in a public file: **keep them out of any
item set.**

| Arm | Enumeration | Cands | A full | B full | Both | Verdict by the rule |
|---|---|---|---|---|---|---|
| N-en/K776 | pass-2 union, 68 eligible; entries 9-16 | 8 | 8 | 3 | **3 of 8** | marginal |
| E-kyoto | Crossref 2001-2009: 137 works, 40 returned, 12 eligible | 8 | 7 | 0 | **0 of 8** | not viable |

- **N-en/K776.** K10plus answers `numberOfRecords` 0 for 5 of the 8 ISBNs; the other 3 records carry
  all four fields and the ISBN in 020 (two also in 776). So the new 776 rule changed nothing here:
  3 of 8 under both rules. All 3 agree with CiNii on title; 2 of 3 on year. Candidates: BC12520458,
  BB30912157, BB05903631, BB04650122, BD05884418, BA63609259, BA85884439, BA7372081X.
- **E-kyoto, record A.** Cambridge through DeepSeek: 7 of 8 full (one page, 10.1017/s0362502800002212,
  gave no title line).
- **E-kyoto, record B.** 58 `OU` files asked for, 56 opened (`OU030` and `OU058`: Moonshot "security
  risk", three tries each), 61 new calls (`OU001` was cached from reachability). The parser found one
  block with journal code `420300`, in `OU009` (year 2000), and matched none of the eight candidates.
  Candidates: DOIs 10.1017/s0362502800002212, 10.1017/s0362502800000675, 10.1017/s0362502800000638,
  10.1017/s0362502800007082, 10.1017/s0362502800007136, 10.1017/s0362502800001826,
  10.1017/s0362502800000687, 10.1017/s0362502800007161.
- **E-kyoto, the looks of deviation 1 (outside the rule; they change no score).** (a) `OU009` opens
  its issues with lines of the form letter, four digits, dash, five digits, which the plan's header
  pattern (letter and six digits) does not match. After that file's first header the parser saw no
  boundary, so the "one block of 319 records" is a misreading, and blocks in other files that use this
  form were missed too. (b) **The first 30 normalised characters of 4 of the 8 candidate titles occur
  in the saved `OU` files** (10.1017/s0362502800007082 and …7136 in `OU023`; …0687 in `OU014`; …7161 in
  `OU011`, `OU014` and `OU039`). So Kyoto's dataset holds at least half of these articles; the 0 of 8 is
  the parser's failure, not the dataset's. Under which journal code they sit, and whether their author
  and year fields are complete, was not read.

## 7. What this means (for the owner; this session decides nothing)

- **English books:** marginal again (3 of 8, after 3 of 8 and 2 of 8 in pass 2). The limit is coverage
  (5 of 8 ISBNs absent from K10plus), not the same-book rule. Accepting 776 links would not have helped
  this draw.
- **English articles:** not viable by the rule, and the rule was right to say so: the parser fixed in
  advance misread the files. But the probe also shows the dataset holds at least 4 of 8 candidate
  titles, through a route that keeps two fetch APIs (Cambridge by DeepSeek, Kyoto by Moonshot). A pass 4
  would need a parser that reads both header forms, written and tested on files already seen, a fresh
  candidate draw (these 8 are spent), and its own bar. Kyoto would still be a new custodian class.
- No arm is viable, so section 4 requires no card. One goes to the board anyway, because a pass 4 or a
  stop is the owner's call.

## 8. Spend

103 fetch calls: 17 reachability (11 tree listings, 6 file requests), 16 book arm, 70 article arm
(1 Crossref, 8 Cambridge, 61 Kyoto). No search, no model call. The deviation 1 looks made no call.
Cost per call is not visible to this session (Gap).

## 9. Not checked

- How many of the 58 `OU` files use the second header form, and what journal code the four found
  titles sit under (the looks of deviation 1 stopped at what it named).
- Whether the found Kyoto entries carry an author and a year in the fields record B needs.
- Whether any `OU` file came through complete (no size to compare against).
- The 1981-2000 Western-article files (`OOBUN`): not opened.
- A blind review of this note against the saved files (to be run before the PR leaves draft).
