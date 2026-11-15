# Battery 2 other cells, design pass 2: probes only

Status: **probe plan, committed before any candidate record was fetched.** Owner's verdict "a" on board
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
