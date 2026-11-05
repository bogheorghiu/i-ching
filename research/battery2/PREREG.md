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
   - **The condition** (the owner, 2026-11-05: "Only if not CASS-linked") is **met**. NAPSTIC (国家科研论文和科技信息高端交流平台) is operated by ISTIC (中国科学技术信息研究所), a unit of the Ministry of Science and Technology:
     - `opaj.napstic.cn/files/国家科技期刊作品开放获取和中国首发协议.docx` says "甲方作为中国科学技术部直属事业单位，是NAPSTIC平台的运营服务方";
     - the napstic page `search.napstic.cn/literature/oaj/gwjckj?...` gives "Email: napstic@istic.ac.cn".

     Both were found by DeepSeek search on 2026-11-05; the snippets were read, the pages not fetched.
   - **The reason.** Tests 4–6 kept 1 item from 105 candidates. One napstic issue fetch yields about 10 records A, each with title, author, issue and pages, and the CASS TOC was fetched with status 200 (`research/battery2/pipeline/ISSUE-HARVEST-PROBE.md`).
   - **Unchanged.** Fields are compared in code, and any mismatch drops the item. Keys are never repaired. Aggregator + aggregator never counts.
   - **Correction on record.** The session's earlier belief that napstic is CASS-built came from model memory and is CONTRADICTED by the sources above.
