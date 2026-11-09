# Battery 2: pre-registration

Frozen 2026-11-04, before any key is built or any model is asked. The design is `design/final-design.md` (merged by Claude Opus 5.5 from eight models' proposals and seven critiques; inputs in `design/`). This file records what the owner decided on top of it and wins where they differ.

## Owner's decisions (2026-11-04)

1. **The admission rule is frozen as designed** (final-design.md, section E). After the results, any threshold may be **raised, never lowered**, on any dimension, if the findings show the bar is affordable. A raised bar is recorded here with its reason before it is applied. Reason: what counts as "harmful" is hard to pin down in advance; tightening after seeing the data can only reject more, never rescue a model.
2. **Models under test run at their production setting**: `reasoning.effort = "max"` (DeepSeek, Kimi, GLM, MiMo Flash), no reasoning parameter for MiMo 2.6 Pro, non-Anthropic models via `:exacto` endpoints. This replaces the design's "minimal reasoning, 250-token cap"; the answer cap is raised so reasoning does not crowd out the answer.
3. **Keys are built by tools**, run by a headless agent on Claude through OpenRouter with `provider.only = ["anthropic"]` (the owner's Claude API key), with DeepSeek's search and fetch, and DeepSeek Flash 1017 for bulk extraction. This session (Claude Code) only writes the harness and reviews outputs.
4. **The owner adjudicates up to 20 items**, blind to model identity, each shown its saved evidence and a drafted verdict. Items are prepared so that adjudication needs at most an ordinary web search, never recall of hard-to-find details.

## Rule validation before the run

The simulation of section E ("Rule validation") runs before any model is asked; its output is committed here. If a required outcome fails, thresholds are revised and recorded before the run, never after.

## Deviations

1. **2026-11-04, before any key was built (owner's decision): two library catalogues from different institutions count as independent records.** Reason: in three test runs (keys-pipeline-test*, 0 keys kept), a book's searchable records were mostly other libraries' catalogues, which the design's custodian-class rule counted as one class; 12 of 35 candidates died on it in test 3. Each library catalogues separately, so two institutions (different registered domains, e.g. CiNii and a Chinese university OPAC) are independent enough for a key. Unchanged: CNKI, VIP and Wanfang still count as one class (they repackage the same publisher metadata), and booksellers are not records.

2. **2026-11-05, before any item was built from it (the owner's decision, conditional): a complete issue table of contents on a research institute's portal counts as record B for an article, if the record-A platform has a different parent institution.**
   - **The case.** Record A comes from a napstic issue page (`search.napstic.cn/literature/oaj/<journal>?activeYear=&activeIssue=`), classed `aggregator`. Record B comes from the yearly TOC on 中国宗教学术网 (`iwr.cass.cn/qknj/...`), a CASS institute portal.
   - **The condition** (the owner, 2026-11-05: "Only if not CASS-linked") is **met**. NAPSTIC (国家科研论文和科技信息高端交流平台) is operated by a unit directly under the Ministry of Science and Technology, not by CASS; its contact address is on `istic.ac.cn`, the domain of ISTIC (中国科学技术信息研究所):
     - `opaj.napstic.cn/files/国家科技期刊作品开放获取和中国首发协议.docx` says "甲方作为中国科学技术部直属事业单位，是NAPSTIC平台的运营服务方";
     - the napstic page `search.napstic.cn/literature/oaj/gwjckj?...` gives "Email: napstic@istic.ac.cn".

     Both were found by DeepSeek search on 2026-11-05; the snippets were read, the pages not fetched.
   - **The reason.** Tests 4–6 kept 1 item from 105 candidates. One napstic issue fetch yields about 10 records A, each with title, author, issue and pages, and the CASS TOC was fetched with status 200 (`research/battery2/pipeline/ISSUE-HARVEST-PROBE.md`).
   - **Unchanged.** Fields are compared in code, and any mismatch drops the item. Keys are never repaired. Aggregator + aggregator never counts.
   - **Correction on record.** The session's earlier belief that napstic is CASS-built came from model memory and is CONTRADICTED by the sources above.

3. **2026-11-08, before any battery item was built from it (session decision under the owner's deviation-2 condition, not a new owner decision; written alongside tests 7-8 the same day, whose result led to the verifier line below, see `pipeline/PATCH-5.md`): deviation 2's pairing also applies with a CNKI article page as record A, and both records are parsed in code.**
   - **The case.** Seeds come from a list of papers with candidate URLs (`pipeline/kimi/papers-2026-11-08-final.jsonl`, compiled by the owner's Kimi run). Record A is a `cnki.com.cn` article page (class `aggregator`), and only CNKI: `stage_s` takes no other record-A host, since no other platform's parent institution has been checked; record B is the CASS institute's yearly TOC (`iwr.cass.cn` / `iwr.cssn.cn`), as in deviation 2.
   - **The condition** ("Only if not CASS-linked") is **met**. CNKI's own pages say it was started by Tsinghua University and Tsinghua Tongfang, and that its publisher is under the Ministry of Education and run by Tsinghua:
     - `cnki.net/elibinfo/aboutUs.html`: "CNKI工程……由清华大学、清华同方发起，始建于1999年6月";
     - `cnki.net/gycnki/daobao/cnkidaobao31/daobao31_10.htm`: 中国学术期刊（光盘版）电子杂志社 "由国家新闻出版总署首批批准、教育部主管、清华大学主办".

     Both were found by DeepSeek search on 2026-11-08; the snippets were read, the pages not fetched.
   - **Why code, not the model extractor.** As fetched by the DeepSeek fetch tool on 2026-11-08, a CNKI page gives title (heading) and abstract; author, venue and issue appear only in CNKI's own catalogue line for the article under 相似文献. The TOC page lists every article of the year, and the 2016/2 section's issue header is missing from the fetched text. The model extractor would reject both as listings. So `cnki_entry` accepts only the first catalogue line under 相似文献, and only when its title equals the heading title and its year and issue equal those in the URL's CNKI id (e.g. `CJFDTotal-ZYJY201602002` → 2016/02); and `toc_entry` accepts a TOC line only when its title equals record A's; venue and year come from the TOC page header. Authors that a TOC separates by spaces are joined with "；" (separator only).
   - **Unchanged.** Title, author, venue and year are compared in code (`stage_d`) and any mismatch drops the item; the issue always comes from record A alone (the TOC's issue is not read). Recoverability, clue and verification stages run unchanged.
   - **First observation** (2026-11-08): for 《周易》“三驱”礼考释, CNKI's catalogue line gives 陈业新 and the CASS TOC gives 陈亚新; under the rules this item drops.
   - **The verifier is told.** Its prompt now says that an `institute_toc` record counts as an item record and that a seeded CNKI page's first 相似文献 line is CNKI's own record of the article; without that line, Opus flagged all four 2016/2 units `not_primary` (test 7).

4. **2026-11-09, before any further item is built (the owner's decision, 2026-11-09): the two records of an item reach the pipeline through different fetch APIs.**
   - **The reason.** Both records used to come through one fetch API (DeepSeek's), which returns its own conversion of the page, not the page. Whether that conversion involves a model is UNRESOLVED (DeepSeek's documentation host is outside this session's network). If one converter alters a field the same way on both pages, the code comparison agrees with itself and the error passes. Two converters from different companies cannot share such an error.
   - **The rule.** In the seeded intake of deviations 2-3, record A (the CNKI article page) is fetched through DeepSeek's fetch API and record B (the institute's table of contents) through Moonshot's. `stage_b` reads the fetcher from each record's saved snapshot and drops the item (`same_fetcher`) when they are the same. An intake for other sources follows the same rule or records its own deviation.
   - **Why this way round.** Probed 2026-11-09: for `cnki.com.cn/Article/CJFDTotal-ZYJY201602002.htm`, Moonshot returned 801 characters without the 相似文献 block that `cnki_entry` reads, and DeepSeek returned the page with it; for the `iwr.cass.cn` 2019 table of contents, Moonshot returned the entries and DeepSeek returned HTTP 502.
   - **What was observed about the converters** (not a proof): a plain-text page fetched twice through DeepSeek was byte-identical, and differed from a local copy of the same text only by 13 lines in which an angle-bracket span (`<https://…>`, `<year>`) had been removed; nothing was reworded (one page). On 20 items re-fetched through Moonshot on 2026-11-09, title and authors matched on 19 and the 20th page came back without its author line.
   - **Items accepted before this deviation** had both records through DeepSeek, except those whose table of contents is on `iwr.cssn.cn`. Before the item set is frozen, each one's record B is read again through Moonshot by the same `toc_entry`, and its title, author, venue and year are compared in code with the stored key. Fixed now, before that run: an item whose entry is absent, ambiguous or different is dropped and listed with its reason; none is repaired; a table of contents Moonshot cannot open leaves its items not re-checked, reported by count, and they stay out of the frozen set until it opens.
   - **Unchanged.** Fields are compared in code and any mismatch drops the item. The search API (recoverability, identifiability, footprint counts) still has one provider; a second search channel is not part of this deviation (Gap).
