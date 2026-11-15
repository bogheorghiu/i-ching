# Battery 2 other cells, design pass 2: probes only

Status: **probe plan (sections 1-5, committed before any candidate record was fetched) and its results (sections 6-9).** Owner's verdict "a" on board
card `d-b2-cells-without-pair` (2026-11-14; carried out from 2026-11-15). Method and rule as in
`OTHER-CELLS-DESIGN.md` sections 1 and 4; this file changes only what it says it changes. Nothing is
built. No model is called. Cap: 300 fetch calls for the whole pass, reachability included; if the cap is
reached, what is left unscored is reported as unscored. Chinese books 1987-1999 are out of scope: the
owner chose "do not build now" on 2026-11-15, and no arm here touches that cell.

Saved responses go only to the private branch `battery2-keys` of `bogheorghiu/delegation-results`,
never to this repository. Candidates are named here by identifier only, never with a clue.

## 1. What was seen before this was written (reachability, 2026-11-15)

66 fetch calls and 4 DeepSeek searches, to learn which hosts open and how; no candidate list was
fetched. Records touched, all excluded from every arm below:

- **Kyoto 東洋学文献類目 dataset** (`corpus.kanji.zinbun.kyoto-u.ac.jp/gitlab`). Through Moonshot the
  group page opens, and the GitLab API answers some calls: the project list (ids 10 papers 2001+,
  11 books, 14 journals, 15 metadata, 16 retro XML 1934-1980, 17 old 1981-2000, 18 old CHINA3), the
  READMEs (licence text only, no format description), and the repository trees (papers: `CHU001.txt`
  onward; old: `RUI0nn.txt`, `OBN00nnn.txt`, `JOURNAL1-3.txt`; journals: `journal1-4.txt`, `rjnl.txt`,
  `ruibangou.txt`; metadata: `00genres.txt` to `09journals.txt`). One file came through whole:
  `metadata/00genres.txt` (a genre table, 33 kB; encoding declared `utf-8-mcs-er`, rare characters as
  `&M-nnnnn;` entity references). Every other file asked for (`09journals.txt`, `rjnl.txt`,
  `ruibangou.txt`, `journal1.txt`) returned 502 or Moonshot's "security risk" refusal, three tries each.
  Web paths under `/-/` (tree, raw) returned 502; GitLab blob search returned 502. DeepSeek: failed.
  Direct access from this container: refused by the proxy. One Moonshot response escaped Markdown
  characters (`\#`, `\[`) in a raw text file.
- **Taiwan NCL 外文期刊漢學論著目次** (`data.gov.tw/api/v2/rest/dataset/16384`): metadata opens through
  both APIs. One CSV distribution, UTF-8, fields 篇名, 刊名, 著者, 原書作者, 出版年, 頁次, 分類號, 備註,
  摘要; coverage 1938-01-01 to 2001-12-31; `resourceAmount` 1000; download URL
  `https://www.ncl.edu.tw/OpenDataFile/0Q162567915924642807/47140e1f-36d1-405e-b6bb-a98e6c4d69d7`
  (not fetched). Publisher: the National Central Library's Center for Chinese Studies (from the
  dataset's own metadata, GROUNDED for who publishes it).
- **A journal's own back-issue list.** Searches for 《周易研究》's own site found a submission-agency site
  (`zyyj.llyj.net`, not the journal; it lists recent submissions, not back issues) and aggregators
  (CNKI, Wanfang, VIP, oriprobe). No journal-run site was found (Gap). For *Early China*, the
  publisher's own pages are Cambridge Core, already record A in pass 1.
- **CNKI static pages.** The issue page `cnki.com.cn/Journal/F-F5-ZYJY-1989-02.htm` opens through
  DeepSeek and lists titles and authors but no article links. `cnki.com.cn/Article/CJFDTotal-ZYJY198902001.htm`
  opens (an article of that issue, not the issue's first TOC line); the forms `CJFD8589-` and
  `CJFD1989-` return the site shell. Issue 1989/2 is excluded below.
- **HathiTrust** full-record API (`catalog.hathitrust.org/api/volumes/full/isbn/<isbn>.json`): 200
  through DeepSeek (empty for ISBN 9780231105804, already seen in pass 1); 502 through Moonshot.

## 2. Arms

Record A and record B always come through different fetch APIs (PREREG deviation 4). All enumerations
take the API's default order. Spent identifiers from pass 1 (`OTHER-CELLS-DESIGN.md` section 4) are
skipped.

| Arm | Cell | Enumeration | Record A (API) | Record B (API) | Route to B |
|---|---|---|---|---|---|
| E-ncl | English articles (*Early China*) | Crossref `journals/0362-5028/works?rows=40&select=DOI,title,author,issued,volume,page&filter=from-pub-date:1996,until-pub-date:2000` (DeepSeek) | Cambridge Core page `cambridge.org/core/product/identifier/<PII>/type/journal_article`, parser `camb` of pass 1 (DeepSeek) | NCL CSV, one file (Moonshot) | row whose 刊名 normalises to contain `earlychina` and whose 篇名 equals Crossref's title after `nrm`, or one is a prefix of the other |
| E-kyoto | English articles (*Early China*) | same candidates | same | Kyoto dataset files (Moonshot) | gate only, see below |
| C-old | Chinese articles before 2000 (《周易研究》) | CNKI issue pages `cnki.com.cn/Journal/F-F5-ZYJY-1996-01.htm` and `-1998-01.htm` (DeepSeek) | CNKI article pages `cnki.com.cn/Article/CJFDTotal-ZYJY{yyyy}{ii}0{nn}.htm`, nn = 01-04 for each issue (DeepSeek) | none found | none |
| Z-new/K | Chinese books 2000+ | union, in this order, of CiNii OpenSearch lists `subject=易経`, `subject=周易`, `clas=123.1`, each with `lang=chi&year_from=2000&year_to=2025&format=json&count=50` (DeepSeek) | CiNii `ncid/<id>.json` (DeepSeek) | K10plus SRU `recordSchema=marcxml` (Moonshot) | record A's first ISBN |
| Z-new/H | Chinese books 2000+ | same candidates | CiNii `ncid/<id>.json` (Moonshot) | HathiTrust full record (DeepSeek) | same |
| N-en/K | English books | union, in this order, of `subject=易経`, `subject=Yi jing`, `subject=I ching`, `clas=123.1`, each with `lang=eng&format=json&count=50` (DeepSeek) | CiNii (DeepSeek) | K10plus `marcxml` (Moonshot) | same |
| N-en/H | English books | same candidates | CiNii (Moonshot) | HathiTrust (DeepSeek) | same |

**Candidates.** First eight eligible entries per arm, decided from the enumeration alone. Books: the
entry has an ISBN and its NCID is not among pass 1's 37. E-ncl: the Crossref entry has `author` and
`page`. C-old: the eight ids above, no filter. Fewer than five eligible entries: "enumeration too thin".

**Why HathiTrust.** It is the one further library catalogue this session saw open (through DeepSeek
only), and with CiNii through Moonshot the pair keeps two APIs. HathiTrust's records come from member
libraries' catalogues; whether it counts as a library catalogue under deviation 1 is the owner's call,
asked only if an H arm is viable.

**E-kyoto gate.** The dataset's file layout is unknown, so no parser can be fixed now and this arm is
not scored. It asks one question: does any Kyoto data file come through Moonshot whole? Asked of six
files, three tries each: `ruimoku-old` `JOURNAL1.txt` and `RUI001.txt`, `ruimoku-papers` `CHU001.txt`,
`ruimoku-metadata` `09journals.txt`, `ruimoku-journals` `journal2.txt` and `rjnl.txt`, by the GitLab
API path `projects/<id>/repository/files/<name>/raw?ref=main`. "Whole" means status 200, a body over
1 kB that is not an error page, and no Moonshot `...` line. Open: reported with the file's size and
first lines, as material for a later pass with its own bar. Not open: E-kyoto is a null, and the lead
is closed for Moonshot.

**C-old.** No record B outside the aggregator class was found for 《周易研究》 before 2000 (Kyoto has no
entry under that name, pass 1; NCL covers foreign journals; CASS tables start in 2012). So the arm is
**not viable by the rule before any fetch**. Record A is still fetched, reported outside the rule, to
settle what pass 1 could not: whether the seed half (issue page plus id form) works for the 1990s.

## 3. Endpoint, rule, voids

- **A full / B full / both:** title, at least one author string, venue (journal) or publisher, and year,
  all non-empty, read by code from saved responses. Articles: as pass 1. Books, record B: MARC 245 `a`,
  100/700 `a` or 245 `c`, 264/260 `b` and `c`, outside the 880 fields (the strict reading of pass 1).
  New in this pass: a book's record B counts as full only if one of its 020 `a` values contains the
  ISBN asked for (pass 1 counted a record B without checking it was the same book). NCL record B: 篇名,
  著者, 刊名, 出版年. An NCL route that matches two rows counts as not yielding.
- **Rule (unchanged):** viable at 4 of 8 "both" or more; marginal at 2-3; not viable at 0-1, or when
  record B's host cannot be opened at all (a null, with the statuses). NCL file not opened, or not
  parseable as CSV with the four columns: E-ncl is that null.
- **Reported next to it, not part of the rule:** title and year agreement (pass 1's `nrm` comparison);
  each CiNii list's size (the seed-widening the owner asked for); the NCL file's row count and how many
  of its rows are *Early China*; 880-only fields.
- **Voids and retries:** a 401, 402 or 429 from a fetch API voids the run; a 5xx or "failed to fetch" is
  tried twice more, then counts as not yielding.

## 4. What a result obliges, and who decides

- Any viable arm whose record B is NCL, Kyoto or HathiTrust is a new custodian: it goes back to the
  owner as its own decision card on the i-ching board, with the evidence of who operates it, **before
  any item is built**. A viable K arm (K10plus is already a library catalogue under deviation 1) also
  goes to the owner as a card; this session builds nothing either way.
- Marginal, not viable, too thin and null arms are reported as such with counts and identifiers. No
  second parser pass, no swapped candidates, no re-derived success. A change to sections 2-3 after the
  first candidate fetch is recorded below with its reason before the arm it touches is scored.
- The report is a note in a PR to this repository and a comment on issue #33. The owner adjudicates.

## 5. Deviations from this plan

1. **2026-11-15, after the script was written and before any candidate fetch: "contains the ISBN
   asked for" counts the ISBN-10 and ISBN-13 forms of one number as the same ISBN.** Reason: CiNii
   gives one form and a MARC 020 often holds only the other; the plan did not say, and the literal
   reading would refuse a record of the same book. Digits and a final X are compared; qualifiers such
   as "(pbk.)" are ignored.
2. **2026-11-15, after all arms were scored (E-ncl: the NCL file returned 502 three times through
   Moonshot, a null): two looks outside the rule, which score nothing.** (a) The NCL file is fetched
   once through DeepSeek (up to three tries), to learn whether the host opens at all; record B through
   DeepSeek would break PREREG deviation 4, so E-ncl stays a null whatever it returns. (b) The Kyoto
   journal-index files that passed the gate (`rjnl.txt`, `journal2.txt`, already saved) are searched by
   code for the strings `Early China` and `周易研究`, to learn whether a later pass could route to those
   journals. No new Kyoto fetch, and no article record is read.

## 6. Results (scored by `other-cells-probe/probe_p2.py` from saved responses)

The candidates named here were seen by this session and are in a public file: **keep them out of any
item set.**

| Arm | Enumeration | Cands | A full | B full | Both | Verdict by the rule |
|---|---|---|---|---|---|---|
| Z-new/K (CiNii ds + K10plus ms) | 3 lists, 87 distinct, 45 eligible | 8 | 8 | 2 | **2 of 8** | marginal |
| Z-new/H (CiNii ms + HathiTrust ds) | same | 8 | 8 | 1 | **1 of 8** | not viable |
| N-en/K | 4 lists, 84 distinct, 68 eligible | 8 | 8 | 3 | **3 of 8** | marginal |
| N-en/H | same | 8 | 8 | 2 | **2 of 8** | marginal |
| E-ncl (Cambridge ds + NCL ms) | Crossref 1996-2000: 61 works, 40 returned, 23 eligible | 8 | 7 | 0 | **0 of 8** | null: NCL file 502 on 3 tries |
| E-kyoto (gate) | 6 files | - | - | - | - | gate open: 4 of 6 files whole |
| C-old | 2 issue pages | 8 | 0 | - | 0 | not viable before any fetch (no record B); record A also failed |

- **Seed lists (the widening the owner asked for).** Chinese books 2000+: `subject=易経` 19,
  `subject=周易` 126 (50 returned at `count=50`), `clas=123.1` 22; 87 distinct in the pages read, 45 with
  an ISBN and not spent. Pass 1 had 22. English books: `subject=易経` 2, `subject=Yi jing` 31,
  `subject=I ching` 54 (50 returned), `clas=123.1` 3; 84 distinct, 68 eligible. Pass 1 had 3. So
  English books are no longer "enumeration too thin"; later pages of `subject=周易` and `I ching` were
  not read.
- **Z-new/K.** K10plus gave a record with a title for 3 of 8 ISBNs (for the other 5 the parser read no title; the responses were not opened by eye); 2 have all four fields and the ISBN, one
  lacks a publisher. Title agreement 0 of 2 under `nrm`, year 1 of 2 (why the titles differ was not
  looked at: script, traditional against simplified, or a different book are all open).
  Candidates: BB2302541X, BB23013046, BB12558271, BD12942922, BB23914582, BD03128094, BC09665816,
  BB26442865.
- **Z-new/H.** HathiTrust returned a record for 1 of 8 (BB12558271, the same book K10plus has); titles
  disagree under `nrm`, years disagree.
- **N-en/K.** K10plus returned a four-field record for 5 of 8; **2 of the 5 do not carry the ISBN asked
  for** (BC10516096, BB29832800), so the rule's new same-book check refused them. Without that check the
  arm would read 5 of 8; with it, 3. The 3 agree with CiNii on title and year. Candidates: BD19743979,
  BC10516096, BC16051971, BB29832800, BB14409046, BA88523608, BA65069298, BD05472589.
- **N-en/H.** HathiTrust returned a record for 2 of 8 (both also in K10plus); both agree on title and
  year. The six with no HathiTrust record were not examined further.
- **E-ncl.** Record A through DeepSeek: 7 of 8 full (one Cambridge page gave no author line).
  Record B: the NCL file returned 502 three times through Moonshot, and (deviation 2a, outside the rule)
  DeepSeek's "failed to fetch" three times. So the file has not been read by either API; its row count
  and its *Early China* coverage are unknown (Gap). Candidates: DOIs 10.1017/s0362502800004296,
  10.1017/s0362502800003230, 10.1017/s0362502800004284, 10.1017/s0362502800003242,
  10.1017/s0362502800003278, 10.1017/s0362502800001012, 10.1017/s0362502800003291,
  10.1017/s0362502800004260.
- **E-kyoto gate.** Through Moonshot's view of the GitLab API: `ruimoku-old/RUI001.txt` (93 kB),
  `ruimoku-papers/CHU001.txt` (35 kB), `ruimoku-journals/journal2.txt` (156 kB) and `rjnl.txt` (128 kB)
  came through by the gate's definition; `ruimoku-old/JOURNAL1.txt` and `ruimoku-metadata/09journals.txt`
  got the "security risk" refusal three times. Three of the four needed three tries. The files are
  line-based mainframe records with `$`-prefixed subfield codes (in `RUI001.txt` in full-width
  characters); `CHU001.txt` came back inside a code fence; `rjnl.txt` had six Markdown escapes inserted
  by the converter. Whether any file is complete cannot be told: the API gives no size Moonshot will
  pass, and the host is unreachable otherwise. Deviation 2b: `rjnl.txt` has one line naming *Early
  China*, `journal2.txt` none; neither names 《周易研究》.
- **C-old.** The 1996/1 ids return a 192-character site shell, as pass 1's 1995/1 ids did. The 1998/1
  pages open with the 相似文献 block, but pass 1's self-citation parser read none of them (cause not
  examined: the arm cannot be viable, and a second parser pass is excluded). The issue pages opened;
  the TOC-line count in the script read 0, a regex written for another layout. So the seed half for the
  1990s is still unsettled, and the cell still has no record B.

## 7. What this means per cell (for the owner; this session decides nothing)

- **English articles.** Still no pair. The new fact is that Kyoto's dataset files now come through
  Moonshot (4 of 6, some after retries), and the journal index names *Early China*. That makes
  Cambridge (DeepSeek) + Kyoto file (Moonshot) a pair that keeps two APIs, which pass 1 could not
  offer. It is untested: a parser for the mainframe format, the route from the journal line to its
  articles, and completeness of a converted file are all open, and Kyoto would be a new custodian class
  needing a PREREG deviation. The NCL file did not open through either API.
- **English books.** The seed list is no longer the problem (68 eligible). Both record-B routes are
  marginal (3 and 2 of 8). K10plus often returns a record of another edition under the same ISBN query.
- **Chinese books 2000+.** Marginal through K10plus (2 of 8, title agreement 0 of 2); HathiTrust adds
  nothing (1 of 8). Most newer Chinese books are in neither catalogue.
- **Chinese articles before 2000.** No record B outside the aggregator class exists among the sources
  tried; the cell stays without a pair.
- **Nothing here is viable by the rule**, so no new-custodian card is required by section 4. One card
  goes to the board anyway, because the Kyoto gate opened and a next step is the owner's call.

## 8. Spend

176 fetch calls (66 reachability, 71 book arms, 36 article arms, 3 deviation 2a) and 4 DeepSeek
searches. No model was called. Cost per call is not visible to this session (Gap).

## 9. Not checked

- Completeness of any Kyoto file; the format of its records beyond the line shape; any article record
  in it.
- The NCL file's content (never opened).
- Why Chinese titles disagree between CiNii and K10plus / HathiTrust.
- Why the C-old parser read nothing on the 1998/1 pages.
- Later pages of the larger CiNii lists; random offsets (design A.2) instead of default order.
- Whether HathiTrust counts as a library catalogue under deviation 1 (owner's call, not asked, since no
  H arm is viable).
- The reachability observations rest on a few requests on one day; Moonshot's GitLab behaviour (502,
  then 200 on a retry) varied within minutes.
