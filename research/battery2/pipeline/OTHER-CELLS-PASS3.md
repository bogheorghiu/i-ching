# Battery 2 other cells, design pass 3: probes only

Status: **probe plan (sections 1-4, committed before any candidate record was fetched; section 5 records a deviation made after scoring) and its results (sections 6-9).** Owner's verdict "a" on board
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
  3 of 8 under both rules. All 3 agree with CiNii on title; 2 of 3 on year. The year mismatch
  (BA63609259: CiNii 2003, K10plus 2013 under another publisher, with the asked ISBN in both 020 and
  776) looks like an e-book record carrying the print ISBN, so the same-book rule passed a record that
  is probably another edition. Candidates: BC12520458,
  BB30912157, BB05903631, BB04650122, BD05884418, BA63609259, BA85884439, BA7372081X.
- **E-kyoto, record A.** Cambridge through DeepSeek: 7 of 8 full. The failure, 10.1017/s0362502800002212,
  is a book review the review filter missed (its "pp" sits inside markup, `402 pp</i>.`). Among the
  other seven are an obituary, two review articles and an annual scholarship summary: the
  author-and-page filter does not pick research articles.
- **E-kyoto, record B.** 58 `OU` files asked for, 56 opened (`OU030` and `OU058`: Moonshot "security
  risk", three tries each), 61 new calls (`OU001` was cached from reachability). The parser found one
  block with journal code `420300`, in `OU009` (year 2000), and matched none of the eight candidates.
  Candidates: DOIs 10.1017/s0362502800002212, 10.1017/s0362502800000675, 10.1017/s0362502800000638,
  10.1017/s0362502800007082, 10.1017/s0362502800007136, 10.1017/s0362502800001826,
  10.1017/s0362502800000687, 10.1017/s0362502800007161.
- **E-kyoto, the looks of deviation 1 (outside the rule; they change no score), as corrected by the
  blind review.** (a) The parser recognises no issue header in `OU009`, whose headers have the form
  `C2003-00095`; so the "one block of 319 records" is every article line of that file under the
  file's first `$j`. The dash form is used in 52 of the 56 opened files (from `OU007` on, and partly in
  `OU005` and `OU006`), so nearly every `420300` block was missed: the review found them in `OU011`,
  `OU014`, `OU023`, `OU032`, `OU033`, `OU037` and `OU039` (years 1998-2011). (b) **As run, the search
  was not the registered one:** the registration says `nrm` of the first 30 characters of the title;
  what ran was the first 30 characters of `nrm(title)`, which is not recorded anywhere before this
  correction. The registered form finds titles of 4 candidates in the saved files (…7082, …7136 in
  `OU023`; …0687 in `OU014`; …1826 in `OU037`) plus a false hit for …7161, whose first 30 characters
  are a recurring series title (the matches are the summaries for other years, not 2000). Crossref
  titles carry HTML markup, which `nrm` turns into letters; with the markup stripped, …0675 is also
  found (`OU014`). So **5 of the 8 candidate titles are in the dataset**; …2212, …0638 and …7161 were not
  found in the opened files. These looks have no saved script or output of their own; they reproduce
  from the snapshots.
- **A third parser defect, found by the blind review:** authors are `$A` in nearly all files (14,868
  `$A` lines against 836 `$a`, the latter almost only in `OU001-006`), and the parser reads only `$a`.
  With headers fixed, record B would still lack its author in about 52 files.
- **The reviewer's own rerun, reported as its finding and not as a score.** Outside the rule, the
  reviewer reran the registered route with all three fixes (both header forms, `$A`, markup stripped)
  and reports exactly one match, full on both sides, for …0675, …0687, …7082 and …7136: 4 of 8, the
  viable bar. This session did not rerun it. Section 4 forbids counting it: the parser was fixed by
  looking at this draw's results, so the same draw cannot test it.

## 7. What this means (for the owner; this session decides nothing)

- **English books:** marginal again (3 of 8, after 3 of 8 and 2 of 8 in pass 2). The limit is coverage
  (5 of 8 ISBNs absent from K10plus), not the same-book rule. Accepting 776 links would not have helped
  this draw.
- **English articles:** not viable by the rule, because the parser fixed in advance was written from
  one unrepresentative file (`OU001`) and misread the rest in three ways (header form, `$A` authors,
  Crossref markup). The dataset itself holds 5 of the 8 candidate titles, through a route that keeps
  two fetch APIs (Cambridge by DeepSeek, Kyoto by Moonshot), and a rerun with the three fixes reaches
  4 of 8 on this draw (the reviewer's figure, not a score). A pass 4 would need: the parser fixed on the
  files already seen and frozen before any new candidate is drawn; a fresh draw (these 8 are spent); a
  filter that keeps reviews, obituaries and summaries out; and its own bar. The `OU` files also hold
  blocks dated 1998-2000, so pass 2's window is partly reachable too. Kyoto would still be a new
  custodian class needing a PREREG deviation before any item is built.
- No arm is viable, so section 4 requires no card. One goes to the board anyway, because a pass 4 or a
  stop is the owner's call.

## 8. Spend

103 fetch calls: 17 reachability (11 tree listings, 6 file requests), 16 book arm, 70 article arm
(1 Crossref, 8 Cambridge, 61 Kyoto). No search, no model call. The deviation 1 looks made no call.
Cost per call is not visible to this session (Gap).

## 9. Not checked, and corrections to section 1

- Corrections to section 1 (left as registered), from the blind review: `OU001` is not representative
  (from `OU007` on, headers read like `C2003-00095` and authors are `$A`); the `OU` files also hold
  blocks dated 1998-2000; the `KIN` files are numbered 001-009 with one number absent; `ruimoku-old`'s
  tree was read to its third (full) page only, not "all pages"; `OU001` has 49 `$j` lines but 29
  distinct codes; `OBN00186` is 14.5 k characters (27.5 kB as UTF-8).

- Whether any `OU` file came through complete (no size to compare against).
- The 1981-2000 Western-article files (`OOBUN`): not opened.
- The reviewer's 4-of-8 rerun was not repeated by this session.
- A blind review ran (a fresh agent given the diff and the saved files): it found the two errors
  corrected above (the look (b) search and the parser's `$A` defect) and the smaller ones folded into
  sections 1 and 6.
