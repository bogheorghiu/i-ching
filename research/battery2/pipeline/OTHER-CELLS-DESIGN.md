# Battery 2: record pairs and intake for the cells the current intake cannot fill

Status: **design proposal with a small probe; nothing here is built into the pipeline.** Board item
`i-b2-other-cells`. Rules it works under: `../PREREG.md` (deviations 1-3; deviation 4, fetcher
independence, is being written by another session) and `../design/final-design.md` sections A and B.
No answer keys are in this file: probe candidates are named by catalogue identifier, DOI or issue, never
with a clue.

## 1. Probe pre-registration (written and committed before any candidate record was fetched)

**What was already seen when this was written (2026-11-09).** A reachability pass: one or two requests per
host through each fetch API, to learn which hosts open and what a record looks like. It touched four
records chosen by hand (ISBN 9780231105804 in CiNii, K10plus and BnF; ISBN 7805693730 in NDL and K10plus;
DOI 10.1017/s0362502800003862 on Cambridge Core; Kyoto volume page `A55S02574`). None of these is a probe
candidate unless the enumeration rule below returns it, and the rule was fixed without regard to them.
The reachability results are in section 3.

**Why pre-register.** The probe decides whether a pair goes to the owner as "viable". Without a bar fixed
first, a thin result can be read as promising afterwards (rule `preregister-ship-decision`).

### Arms (one per cell), with the fetch API each record is assigned to

Record A and record B go through different fetch APIs (the coming deviation 4). The assignment below is
forced by which API opens which host (section 3).

| Arm | Cell | Seed enumeration (no title query) | Record A (fetch API) | Record B (fetch API) | Route to B |
|---|---|---|---|---|---|
| B-zh-new | Chinese books, 2000+ | CiNii Books OpenSearch, `clas=123.1&lang=chi&year_from=2000&year_to=2025&count=20` | CiNii Books record `ci.nii.ac.jp/ncid/<id>.json` (DeepSeek) | K10plus SRU record, `recordSchema=dc` (Moonshot) | ISBN from record A |
| B-zh-old | Chinese books, 1987-1999 | same, `year_from=1987&year_to=1999` | same | same | same |
| B-en | English books | same, `lang=eng`, no year limit | same | same | same |
| A-en | English articles (*Early China*) | Crossref works list for ISSN 0362-5028, windows 1990-1995 and 2010-2012, `rows=20` | Cambridge Core article page by Crossref's PII (Moonshot) | Kyoto 東洋学文献類目 journal-volume page (DeepSeek) | journal, then volume, in the Kyoto journal index |
| A-zh-old | Chinese articles before 2000 (《周易研究》) | CNKI ids `ZYJY199501001`...`008` (first eight of 1995 issue 1) | CNKI article page (Moonshot) | Kyoto journal-volume page for that issue (DeepSeek) | journal, then volume |

Secondary measurement, reported but not part of the rule: for the three book arms, the same ISBN is also
looked up in the National Diet Library's own catalogue (`ndlsearch.ndl.go.jp/api/opensearch?isbn=...&dpid=iss-ndl-opac`,
Moonshot), to see whether a second record-B custodian exists.

### Candidates

Per arm, the **first eight** entries of the enumeration in the API's own default order that pass the
arm's eligibility filter, decided from the enumeration response alone:
- book arms: the entry carries at least one ISBN (route B needs it);
- A-en: the Crossref entry has an `author` and a `page` (this drops front matter, abstracts lists and
  notices); the first four eligible from each window;
- A-zh-old: all eight ids, no filter.

If an enumeration returns fewer than five eligible entries, the arm is reported as **"enumeration too
thin"** and gets no viability verdict.

### Endpoint

For each candidate, read from the saved fetch responses by code (JSON paths and fixed regular
expressions written into the probe script), never by a model and never by eye:
- **full field set from A**: title, at least one author or editor string, venue (journal) or publisher,
  and year, all non-empty;
- **full field set from B**: the same four, from record B;
- **both**: both of the above for the same candidate.

Reported next to it, not part of the rule: how many "both" candidates agree on title and on year after
`norm`-style normalisation (case, punctuation and spaces removed; traditional and simplified not
reconciled in the probe).

### Rule

- **viable**: "both" for at least half of the arm's candidates (4 of 8).
- **marginal**: 2 or 3 of 8.
- **not viable**: 0 or 1 of 8, or record B's host or index cannot be opened at all (reported as a null,
  with the HTTP statuses).

Why one half: the Chinese-article intake kept 133 of 277 seeds (48%) *after* every later stage
(`PATCH-5.md`, run 3). Clue and verification stages will remove a further share here too, so a pair that
loses more than half its seeds at the record stage alone would cost several times more per item than the
existing cell.

### What voids a fetch, and what does not

- An auth or billing status (401, 402, 429) from a fetch API voids the run; it is repeated later.
- A 5xx or "failed to fetch" on a record is retried up to two more times; if it still fails, the
  candidate counts as **not yielding** (a null), because an intake that cannot open its record does not
  yield an item either.

### What a result obliges, and who decides

A "viable" arm goes to the owner as a proposed pair (and, where the pairing is new, a proposed PREREG
deviation) on a board decision card. A "marginal" or "not viable" arm is reported as that, with its
counts and identifiers; this session does not re-derive a success from the same fetches (no second
parser pass to rescue an arm, no swapping candidates). Any change to this section after the probe starts
is recorded under "Deviations from the probe plan" with its reason, before the affected arm is scored.
The owner adjudicates; this session only reports.
