# Issue-level harvest: feasibility probe (2026-11-05)

Owner chose "harvest whole issues" (2026-11-05) after tests 4-6 gave 1 accepted item from 105 candidates. Before writing patch 5, these were checked with DeepSeek's own search and fetch tools (direct API).

## Observed
- **VIP (cqvip) journal pages are useless to the fetch tool.** `dianda.cqvip.com/Qikan/Journal/Detail?...` returned 321 characters of site chrome; `mqikan.cqvip.com/Journal/JournalSummary?...` returned 141. The issue lists load by JavaScript (test-1 snapshots `f_e18ee6f553aaf15b.json`, `f_100959c5e4cd7b98.json`).
- **napstic issue pages work.** `search.napstic.cn/literature/oaj/zhouyyj?page=1&activeYear=2024&activeIssue=6` was fetched with status 200 twice in tests 1-5 (pages 1 and 2). Page 1 holds 3,003 characters: journal 周易研究, ISSN 1003-3882, "2024年06 期", and per article the title, authors, page range, abstract and keywords.
- **Item pages fail where issue pages succeed.** On the same host, item pages `literature/periodical/010zhouyyj2024...` returned 404 in 9 of 13 fetches.
- **A second listing of 《周易研究》 issue contents exists.** `iwr.cass.cn/qknj/zhouyi/mulu/202409/t20240928_5788117.html` (中国宗教学术网, "《周易研究》2021年目录") was fetched with status 200 by the DeepSeek fetch tool, 2,655 characters. It lists each 2021 issue's articles as title/author, without page numbers.
- **The journal's own TOC PDFs are out of reach.** For 《出土文献》, `ctwx.tsinghua.edu.cn/__local/.../...pdf` (a TOC found by search) returned 404 from the DeepSeek fetch tool.
- **The journal's own site has no issue lists.** zhouyi.sdu.edu.cn fetches so far returned only "about" pages, no issue tables of contents.

## Open, for the owner
- **Classes.** napstic is classed `aggregator` (CLASS_RULES), so for an article it can be record A but not both records. iwr.cass.cn fits no existing class: it is neither the journal, an aggregator, a library nor a publisher. Under design A.1 a compiled TOC on an institute portal is not obviously a primary record. Decision needed: does such a TOC listing count as record B?
- **Independence.**
  - **GROUNDED** (CASS Library's own news page, `lib.cssn.cn/zx_107813/gzdt/202605/t20260514_5989835.shtml`, found by DeepSeek search 2026-11-05; snippet read, page not fetched): "国家哲学社会科学文献中心具体承建单位为中国社会科学院图书馆". Its site is ncpssd.org.
  - **Settled 2026-11-05 (CONTRADICTS the earlier belief):** `search.napstic.cn` is not NCPSSD. It is NAPSTIC (国家科研论文和科技信息高端交流平台), operated by ISTIC under the Ministry of Science and Technology. Sources: the agreement at `opaj.napstic.cn/files/国家科技期刊作品开放获取和中国首发协议.docx`, and "Email: napstic@istic.ac.cn" on a napstic page. So it shares no parent with iwr.cass.cn. The owner's decision is PREREG deviation 2.
- **Data quality, a signal for the code check.** The napstic 2024-06 page gives the author of an article on 清初关中学者 as "李颗". From model memory (UNRESOLVED), that scholar is 李颙, which would make this a character error in napstic's data. Exact code comparison against a second record would drop such an item, as intended. But it shows napstic text is not error-free.
