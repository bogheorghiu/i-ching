# Battery 2: record pairs and intake for the cells the current intake cannot fill

Status: **design proposal with a small probe; nothing here is built into the pipeline.** Board item
`i-b2-other-cells`. Rules it works under: `../PREREG.md` (deviations 1-3; deviation 4, fetcher
independence, was merged while this note was being written) and `../design/final-design.md` sections A and B.
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

Record A and record B go through different fetch APIs (PREREG deviation 4). The assignment below is
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
reconciled in the probe). As run, the scripts were looser than this on titles: record A's title is cut
at its first " : ", and a title that is a prefix of the other counts as agreeing, so a short title can
agree with a longer, different one. A record with no original-script field cannot agree with a Chinese
title at all. The agreement counts are rough in both directions.

### Rule

- **viable**: "both" for at least half of the arm's candidates (4 of 8).
- **marginal**: 2 or 3 of 8.
- **not viable**: 0 or 1 of 8, or record B's host or index cannot be opened at all (reported as a null,
  with the HTTP statuses).

Why one half: the Chinese-article intake kept 133 of 277 seeds (48%) *after* every later stage
(`PATCH-5.md`, run 3, as counted then). Clue and verification stages will remove a further share here too, so a pair that
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

### Deviations from the probe plan (each written before the fetches it affects)

1. **2026-11-09, after the three book arms were scored (results in section 4), before any article-arm
   record was fetched: a second arm of record A for A-en.** The reachability copy of one Cambridge Core
   page through Moonshot holds the title line and the footnotes, with no author and no year. The arm is
   run as registered (record A through Moonshot). In addition, record A is fetched through DeepSeek and
   scored the same way, reported as **A-en/ds**, outside the rule: with it, both records would come
   through one fetch API, which PREREG deviation 4 does not allow.

2. **Recorded 2026-11-09 after a blind review of this note pointed it out (so after the data, and
   marked as such): section 2 is itself a departure from section 1.** Section 1 says a null arm is
   reported and the owner adjudicates. This session instead registered and ran a second book probe the
   same evening without the owner. It used new fetches, a different record schema and different
   candidates, and its bar was committed first, but the decision to run it was this session's. Its
   result is therefore **exploratory**: it does not overturn the first probe's nulls, and the owner has
   not accepted it as a test of anything.
3. **Also recorded after the review: things done outside the plan.** Record B of both article arms was
   never fetched or parsed by a script; what section 4 says about the Kyoto pages comes from this
   session reading individual responses, which the endpoint ("by code, never by eye") excludes. The
   A-zh-old ids were fetched through DeepSeek as well as Moonshot. Nine searches were made to find
   Kyoto URL forms. None of these scores anything.

## 2. Follow-up probe for books (pre-registered 2026-11-09, after the first book arms scored 0 of 8)

**Why a second probe, and why it is not a rescue.** All three book arms failed on one field: K10plus's
`recordSchema=dc` response has no `dc:publisher` element at all (tags present in a saved response:
title, contributor, date, description, format, identifier, language, relation, subject, type). So the
first probe measured the schema this session chose, and its verdict stands: that route is not viable.
One request (ISBN 9787101090093) showed that `recordSchema=marcxml` carries the publisher (field
264). This probe tests that different route on **different candidates**, with new fetches.

- **What had been seen when this was written.** The full 20-entry lists of both Chinese arms, with
  their ISBNs (they are the section 1 enumerations). That ISBN 7805693730 has a K10plus record (from
  the reachability pass); it is entry 12 of the 1987-1999 list and so a candidate here (BN07534574).
  One MARCXML response, for ISBN 9787101090093 (first-probe candidate BD20731693), which is where the
  field numbers below come from.
- **Arms and candidates.** B-zh-new and B-zh-old: entries 9 to 16 of the same eligible lists as in
  section 1 (the first eight are used up). B-en: the first eight eligible entries of
  `subject=易経&lang=eng&count=20` (the `clas=123.1` list had only 3 English entries; this enumeration
  has not been fetched before).
- **Record B.** K10plus SRU, `recordSchema=marcxml`, by record A's first ISBN, through Moonshot. Fields
  by regular expression over the saved text: title = 245 `a`; author = 100 `a`, 700 `a` or 245 `c`;
  publisher = 264 or 260 `b`; year = 264 or 260 `c`. For Chinese books the linked 880 fields
  (original script) are read the same way and preferred for the agreement count.
- **Endpoint, rule, voids, obligations:** as in section 1.

## 3. Reachability: which fetch API opens which host (observed 2026-11-09)

This container reaches no catalogue directly (every direct request failed before any HTTP status), so
every record goes through `api.deepseek.com/v1/tools/fetch` or `api.moonshot.ai/v1/tools/fetch`. Counts
are requests in this session; "failed" for DeepSeek means its 404 body `failed to fetch URL`. A status
seen once or twice says little about tomorrow.

| Host (what was asked) | DeepSeek | Moonshot |
|---|---|---|
| `ci.nii.ac.jp` (OpenSearch list, `ncid/<id>.json`) | 200, every time (40+ requests) | 200 (5 of 5) |
| `api.crossref.org` (journal works list) | 200 | 200 |
| `sru.k10plus.de` (SRU, `dc` and `marcxml`) | failed, 5 of 5 | 200, 40 of 41 (one 504) |
| `ndlsearch.ndl.go.jp` (OpenSearch) | failed, 3 of 3 | 200 for 20 of 21 lookups (one lookup 504 on all three tries) |
| `catalogue.bnf.fr` (SRU) | failed | 200 (0 records for the one ISBN asked) |
| `ruimoku.zinbun.kyoto-u.ac.jp` (Kyoto 東洋学文献類目) | 200, with 502 on about one request in three | 504, 6 of 6 |
| `cambridge.org` (article page) | 200, with author and copyright year | 200, title and footnotes only: no author, no year (4 of 4 article pages) |
| `doi.org` | 200 for a Cambridge DOI, failed for a Brill DOI | 502 |
| `brill.com` (journal overview) | 200 | 502 |
| `jstor.org` | failed | 403, "security risk" |
| `loc.gov`, `lccn.loc.gov` | failed; "No Connections Available" page | 504, 502 |
| `api.lib.harvard.edu` | failed | 502 |
| `catalog.hathitrust.org` (ISBN API) | 200 (empty for the one ISBN) | 502 |
| `opac.nlc.cn` | home page 200; ISBN search 502 | home page 200; ISBN search 502 |
| `data.gov.tw` (dataset page) | 200, but the download link is not in the text | 502 |
| `corpus.kanji.zinbun.kyoto-u.ac.jp/gitlab/Ruimoku` | failed | 200 |

Three things about the fetch APIs themselves, each n = 1 to a few, each UNRESOLVED as to cause:
- **Moonshot does not return XML as served.** In SRU responses it removes the space between an
  element name and its attributes (`<datafieldtag="245"ind1=...`), escapes underscores, and inserts
  lines holding only `...` (42 of them in one 7 kB MARCXML record). Whether text is dropped at those
  lines was not checked against the original (the host is unreachable any other way). A parser for
  these responses must be written against this converted form, and a field missing from it cannot be
  told from a field the converter dropped.
- **Moonshot's text of a Cambridge article page has no author and no year** as the probe's parser
  reads it, on all four article pages, while DeepSeek's text of the same URLs has both. The parser's
  author pattern was written from DeepSeek's layout; the blind recount, with its own parsing, also
  found no author line and no publication year in Moonshot's text. PREREG deviation 4 records a
  similar case (one of 20 pages re-fetched through Moonshot came back without its author line).
- **The two APIs returned different text for the same URL at the same minute:** the K10plus "about"
  page reads "etwa 250 Millionen Bestandsnachweisen" through DeepSeek and "etwa 260 Millionen"
  through Moonshot. One of them served an older copy, or the site serves variants. DeepSeek's copy of a
  Cambridge page carried a render date thirteen hours before the request. So a fetch may be a cached
  copy of unknown age; for bibliographic records that seldom matters, but it is a fact about
  "fetcher independence" worth knowing.

## 4. Probe results

Scripts read only saved responses. "A full" and "B full" are the endpoint of section 1. The candidates
named below were seen by this session and are in a public file: **keep them out of any item set.**

### Books

| Arm | Enumeration | Candidates | A full | B full | Both | Verdict by the rule |
|---|---|---|---|---|---|---|
| B-zh-new (K10plus `dc`) | 22 entries, 19 with ISBN | 8 | 8 | 0 | **0 of 8** | not viable |
| B-zh-old (K10plus `dc`) | 41 entries, 20 of the first 20 with ISBN | 8 | 8 | 0 | **0 of 8** | not viable |
| B-en (K10plus `dc`) | 3 entries | 3 | 3 | 0 | 0 of 3 | enumeration too thin |
| B-zh-new/2 (K10plus `marcxml`) | same list, entries 9-16 | 8 | 8 | 2 (0) | **2 of 8** (0 of 8) | marginal (not viable) |
| B-zh-old/2 (K10plus `marcxml`) | same list, entries 9-16 | 8 | 8 | 8 (7) | **8 of 8** (7 of 8) | viable by the rule as written; exploratory, and see section 5 |
| B-en/2 (K10plus `marcxml`) | 2 entries | 2 | 2 | 0 | 0 of 2 | enumeration too thin |

- **Two readings of section 2, both reported.** The plan says the original-script 880 fields are
  "read the same way and preferred for the agreement count"; it does not say whether a field found
  only in an 880 counts toward the field set. The probe script counted it; the figures in brackets
  are the strict reading (245, 100/700, 264/260 only), from the blind recount. Three records have
  their publisher only in an 880. The verdict changes for B-zh-new/2 and not for B-zh-old/2.
- **First probe, cause of the nulls:** no saved `dc` response holds a publisher element, in 14 records.
  The likely cause is that K10plus's `dc` schema has none; that Moonshot's conversion dropped it every
  time cannot be excluded from the saved text (UNRESOLVED). The other 5 of the 19 ISBNs had no K10plus
  record at all.
- **B-zh-new/2:** six of eight ISBNs have no K10plus record (an empty SRU response, 565 characters).
  The two found agree with record A on year; one of them on title (for BA63316330 K10plus returns a
  different title under the same ISBN).
- **B-zh-old/2:** all eight ISBNs have a K10plus record with all four fields; five carry the
  original-script (880) fields. Agreement under the probe's crude normalisation: **title 3 of 8, year
  6 of 8.** The probe does not say why the other titles differ (romanised against original script,
  traditional against simplified, subtitles, or a different book). One known cause of a real mismatch:
  ISBN 7805693730 is shared by a multi-volume reprint series, and K10plus returns another volume of it
  (seen in the reachability pass with the `dc` schema, and again here as BN07534574, which disagrees on
  both title and year). So the pair opens records for old books, and the comparison stage will then
  drop a share that this probe cannot size: at least the two year disagreements (2 of 8). The same
  kind of mismatch showed in the first probe: for BA81633630 both K10plus and the NDL return the
  parent set, not the volume CiNii describes.
- **Second custodian for record B (secondary measurement):** the National Diet Library's own catalogue
  had a full record for 2 of the 19 first-probe candidates (BA81633630 and BN14267128), no record for 16, and one lookup that returned 504 three times. It is not a second record B for Chinese books.
- Candidates: B-zh-new BA81633630, BD20731693, BD13182686, BB14892784, BB08537573, BA90059004,
  BA84281380, BA84279403; B-zh-old BA53798596, BN14267128, BN13011082, BN12710982, BN12370250,
  BN11489597, BN0972278X, BN08503827; B-en BA59890988, BA14308857, BA10720382; B-zh-new/2 BA66883097,
  BA65238668, BA64022299, BA6333309X, BA63316330, BA62363109, BA62362106, BA6222256X; B-zh-old/2
  BN08502438, BN08081759, BN07741626, BN07534574, BN07196314, BN07114127, BN06773809, BN04345305;
  B-en/2 BA56630131, BB04075567 (all CiNii NCIDs).

### Articles

| Arm | Candidates | A full (assigned API) | B full | Both | Verdict by the rule |
|---|---|---|---|---|---|
| A-en (*Early China*) | 4 (see below) | 0 of 4 through Moonshot | 0: no record B reached | **0 of 4** | **no verdict** (see below) |
| A-en/ds (outside the rule) | the same 4 | 4 of 4 through DeepSeek | 0 | 0 of 4 | none |
| A-zh-old (《周易研究》 1995/1) | 8 ids | 0 of 8 | 0 | **0 of 8** | not viable by the rule; the arm could not have scored (see below) |

- **A-en, enumeration.** The 1990-1995 window gave 12 eligible entries of the first 20 (124 in all);
  the 2010-2012 window gave **none** of 20 (all of volume 33), because none of those Crossref entries has an `author`. So
  the arm has four candidates. The plan's "too thin" clause speaks of fewer than five eligible
  *entries* and did not foresee one window coming back empty: read by candidates (4) the arm is too
  thin for a verdict; read by entries (12) it is "not viable", since no record B was reached. This
  note reports it as no verdict. Either way nothing here supports the pair. The candidates:
  DOIs 10.1017/s0362502800003862 (the page seen in the reachability pass; the rule returned it first),
  10.1017/s0362502800005009, 10.1017/s0362502800005010, 10.1017/s0362502800005034.
- **A-en, record A.** Through Moonshot: title and venue only, on all four. Through DeepSeek: title,
  first author, venue and copyright year on all four, and the title equals Crossref's.
- **A-en, record B.** The Kyoto bibliography's volume pages are the right shape: one line per article
  with author, title, journal, volume, pages and year (seen for two other journals, pages `A55S02574`
  and `C2010-00033`). But the route to them did not open: the entry `journal-name@ruimoku/rep.id=Early_China`
  exists and holds only the name; a journal's volume list is keyed by a numeric journal id that the name
  page does not give; the Turtle form of the name page returned 502 three times; and where a volume list
  did open (journal 208220), DeepSeek's text shows the volume names without their ids. So no *Early
  China* volume page was reached. Also unknown: whether the 1981-2000 editions are in this interface
  at all (its front page says 1934-1980 and 2001 onwards; the 1981-2000 data sits in an older search
  form).
- **A-zh-old.** The eight ids were this session's guess that 1995 pages follow the modern CNKI id
  form. They do not resolve: DeepSeek returns the same short CNKI site-shell page for all eight (no title,
  author or journal), Moonshot 502. (Fetching these through DeepSeek as well was not in the plan; it
  was done to tell a wrong id from a Moonshot failure, and scores nothing.) And
  the Kyoto entry for 《周易研究》 is empty (the journal does not appear to be indexed there). The
  arm was also assigned wrongly: PREREG deviation 4 (merged while this probe ran, and not read until
  after) records that Moonshot's text of a CNKI page lacks the 相似文献 block the parser needs, so
  record A through Moonshot would have failed with valid ids too. What the arm does show: the id
  guess was wrong, and Kyoto has no entry under that journal name. It shows nothing about a pair.

## 5. What is proposed, per cell

The owner decides each on a board card; this section is the reasoning behind the recommendations.

### Chinese books, 1987-1999: both records open, but few would survive comparison

- **Record A:** CiNii Books record, `https://ci.nii.ac.jp/ncid/<NCID>.json`, through DeepSeek. Class
  `library` (already in `CLASS_RULES`; PREREG deviation 1 names CiNii).
- **Record B:** K10plus record, `https://sru.k10plus.de/opac-de-627?...query=pica.isb%3D<ISBN>&recordSchema=marcxml`,
  through Moonshot. Class `library`. Operator, from its own page (`bszgbv.de/services/k10plus/`,
  fetched 2026-11-09 through both APIs): "K10plus betreiben BSZ und VZG eine gemeinsame Datenbank ...
  Hinter K10plus stehen die Bibliotheksdaten der Mehrzahl der deutschen staatlichen Universitäten und
  Hochschulen." GROUNDED for who runs it. That CiNii Books is run by Japan's National Institute of
  Informatics is from model memory: its "about" page returned 404 (Gap).
- **Independence.** Two library catalogues from different institutions and registered domains, which
  deviation 1 accepts. What deviation 1 did not consider, so it goes to the owner: **both are union
  catalogues**, and union catalogues take in records made elsewhere. One K10plus record seen in the
  reachability pass (an English book) carried a Library of Congress number and classification, a sign
  of a copied record; NACSIS-CAT also lets cataloguers copy from reference files (model memory,
  UNRESOLVED). For Chinese books the two networks are less likely to share a source than for English
  ones, but this was not measured. A check that code could make: MARC field 040 names the agency that
  made a record; a pair could be refused when both name the same one (the MARCXML has the field; CiNii's
  JSON has no equivalent, so the check is one-sided. Gap).
- **Seed route (no title query):** CiNii Books OpenSearch by classification, `clas=123.1` (Nippon
  Decimal Classification: the *Yijing*), `lang=chi`, a year window, paged with `count` and `p`. 41
  entries for 1987-1999 and 22 for 2000-2025: **the list is small.** Other class marks and subject
  headings would widen it; none was tried. The route to B is record A's ISBN.
- **Parser plan** (code, as `cnki_entry` and `toc_entry`): `cinii_book_entry(ncid)` reads
  `@graph[0]`: `dc:title[0].@value`, `dc:creator`, `dc:publisher[0].@value`, `dc:date`, and the ISBNs
  in `dcterms:hasPart`. `k10plus_entry(isbn)` reads, by regular expression over Moonshot's converted
  text, MARC 245 `a` (title), 100/700 `a` or 245 `c` (author), 264/260 `b` (publisher) and `c` (year),
  and the same subfields of the linked 880 fields. It accepts the record only if one of its 020 `a`
  values equals the ISBN asked for, and refuses an electronic-resource record (leader and 007; one such
  record came back for a print ISBN in the first probe). `stage_d` would need a change for
  books: the publisher in place of the venue, and original script compared with original script.
- **Why this is not yet a pair worth building** (from the blind review; this session agrees):
  - the endpoint counts a record B as full without checking it is the same book, and at least one of
    the eight is not (BN07534574), so 8 of 8 overstates;
  - the bar's own reason is the loss at the record stage, and the design drops an item on any title
    or year mismatch (`final-design.md` A.5). With title agreement at about 3 of 8, the pair fails the
    reasoning behind the bar while passing the bar as written. (That reasoning also overstated: at
    one half the cost per item doubles, not "several times".)
  - supply: 41 entries, 16 of them spent in this probe, leaves 25 under this class mark. At that
    agreement rate and the later stages' losses it is a handful of items against a design share of
    40% books.
  - parsing both records in code needs its own PREREG deviation (the design's A.4 has a model extract
    and code check; deviation 3 allows code parsers for CNKI and the institute table only), and
    `sru.k10plus.de` matches no entry of `CLASS_RULES` today.
- **What the probe does not show:** how many pairs survive the comparison (title agreed on 3 of 8
  under a crude rule); whether clues can be written for a book from a catalogue record that has no
  abstract; recoverability by the search tool.

### Chinese books, 2000 and later: marginal

Same pair, 2 of 8 (0 of 8 on the strict reading). Six of eight newer books are simply not in K10plus. A different record B is needed:
the National Library of China's catalogue would be the natural one, and its search page returned 502
through both APIs. No proposal; recorded as a cell without a pair.

### English books: no verdict

The NDC class and subject lists in CiNii hold two or three English books each, so the enumeration is
too thin to test a pair. An English-language seed list needs a catalogue that classifies in English
(Library of Congress `PL2464`, Harvard): both were unreachable through either API. For English books
the copied-record problem is also at its worst (see above). No proposal.

### English articles: no pair found; the nearest one needs both records through one fetch API

Record A has to be the journal's own page. For *Early China* only DeepSeek returns the author and year;
for *T'oung Pao* only DeepSeek opens Brill at all. The one independent record B found, the Kyoto
bibliography, also opens only through DeepSeek. So even with the Kyoto index solved, both records
would come through one API. PREREG deviation 4 asks an intake for other sources to follow its rule
"or records its own deviation before it builds an item", so that would be the owner's call, on
single-evening evidence about which API opens what. Three ways out, none tested:
1. Kyoto publishes the bibliography as a dataset (`corpus.kanji.zinbun.kyoto-u.ac.jp/gitlab/Ruimoku`:
   books and papers from 2001, journals and metadata from 1981, the 1981-2000 text files), and
   Moonshot opens that host. Reading record B from the dataset files would solve both the index and
   the fetch-API problem. Not tried: it needs the repository's file layout, and whether a raw file
   comes through a fetch API whole is unknown.
2. Taiwan's National Central Library publishes 外文期刊漢學論著目次 (tables of contents of some 400
   foreign sinology journals, from its printed quarterly, volumes 1-17) as open data
   (`data.gov.tw/dataset/16384`; fields 篇名, 刊名, 著者, 出版年, 頁次). It would be a library-made
   record B for pre-2000 English articles. Only its description page was fetched; the file was not.
3. Crossref's record as record A. It opens through both APIs and is clean JSON, but the publisher
   deposits it, so it is the publisher's record by another door, and for 2010-2012 it lacks authors. Usable as the seed list, as here; as a record it would need the owner's ruling.

A Kyoto volume page as record B would be a **new class** (a bibliography compiled by a university
institute from the journals it receives), the analogue of deviation 2's institute table of contents.
It needs a PREREG deviation before any item is built from it, and evidence of who operates it from its
own pages: the pages fetched name only the host (`zinbun.kyoto-u.ac.jp`), and the institute's site
returned 504 (Gap). No deviation is proposed now, because the probe gives it nothing to stand on.

### Articles before 2000, Chinese: not tested

The arm failed at its own enumeration. What a design needs first: the form of CNKI ids before 2000,
and a record B that covers those years (the CASS tables of contents start in 2012; Kyoto does not seem
to index 《周易研究》). A journal whose own site lists its back issues would give the ordinary
`journal_own` + `aggregator` pair with no deviation; none was looked for.

## 6. Repeating this

The owner wants an intake that can be run again when models change. What this note leaves for that:
- the enumeration URLs and the endpoint definitions in sections 1 and 2 are complete enough to rerun;
- the probe scripts are in `other-cells-probe/`, as they ran (`f.py` is the fetch wrapper with its
  cache; `probe.py`, `probe2.py` and `probe3.py` are sections 1, 2 and the article arms). Run them from
  an empty working folder outside the repository: they write every response to `snap/` there;
- the saved responses of this probe are on the private branch `battery2-keys` of
  `bogheorghiu/delegation-results`, folder `other-cells-probe-2026-11-09/` (commit 64f7fc9, pushed
  2026-11-10, after this note merged): every fetch response, the call log, the scripts with their
  result files, and the blind recount's scripts. They stay out of this public repository because they
  are catalogue records of possible items. Not saved: the results of the nine searches, only their
  queries;
- a rerun should take fresh candidates (later pages of the same lists), since the ones named in
  section 4 are spent.

## 7. Spend

261 tool calls: 115 fetches through DeepSeek, 137 through Moonshot, 9 DeepSeek searches. No model was
called. What a fetch or search call costs is not visible to this session (Gap), so the spend is stated
in calls.

## 8. Not checked

- Whether Moonshot's `...` lines stand for dropped text (section 3).
- Any record through both APIs for the same URL, except CiNii and Crossref lists (whose texts matched
  apart from Moonshot's code fence) and the Cambridge pages (which differed).
- Why titles disagree in B-zh-old/2; the size of the loss at the comparison stage.
- Clue writing, recoverability and verification for books: the probe stops at the two records.
- Other record-B candidates for Chinese books: NLC (502), Taiwan's NCL, Hong Kong union catalogues,
  WorldCat: none opened or none tried.
- Kyoto's dataset files and the Taiwan open-data file (section 5).
- The fame or holdings covariate: CiNii returns `cinii:ownerCount` (how many member libraries hold a
  book), which could serve the holdings split the design names; not examined.
- The reachability table rests on one to a few requests per host on one evening; "only DeepSeek opens
  Brill" and the like are single observations, not properties of an API.
- The seed route takes lists in the API's default order; the design (A.2) asks for random offsets.
- Left as they are in the scripts, which are kept as they ran: a copied CNKI pattern, unused imports,
  `sys.path` set to the working folder, and no guard against a rerun's lists overlapping.
- The two registration commits (c630f58, 6e096e0) are on the PR branch; after a squash merge their
  order is visible only in the PR's commit list.
