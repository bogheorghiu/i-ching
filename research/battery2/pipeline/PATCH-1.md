The script below (build_keys.py, which you wrote) ran on 34 candidates and kept 0. Drop reasons from dropped.jsonl:
- unfetchable_source 17: record A was a library OPAC (Kyoto, Stanford, Chinese university OPACs), JSTOR, a CNKI wiki page or a PDF; DeepSeek fetch could not read it.
- field_unverified 14: record A was a LISTING page (a journal's table-of-contents index, a CNKI "hotword" page, an OPAC search-result page, a Wanfang column listing), not one work's own record, so no complete author+title+venue+year entry matched verbatim.
- no_second_record 2, extraction_failed 1.

Fix, decided by the owner:
1. Use DeepSeek SEARCH results as snapshots where they carry a full record. The audit saw search hits from VIP (cqvip.com), Wanfang, CNKI and CiNii whose title/summary/snippet text contains author, title, journal, year, issue and pages (e.g. a VIP hit: 「试释周初青铜器铭文中的易卦 … 张政烺 出处：《考古学报》1980年第4期403-415」; a CiNii hit: 「出土數字卦文獻輯釋 賈連翔著 中西書局, 2020.8」). Save the search-result JSON as the snapshot; a fetch is optional, tried only when the hit lacks a field.
2. Accept as a record only an ITEM page: one work's own article page or catalogue record. Reject listing pages by URL pattern and by content (several different titles, search-result markers, TOC indexes). Candidates are then built from item records, not from listings: when a listing page is found, it may seed queries for its items, but it is never itself a record.
3. Independence (unchanged rule): the two records come from different custodian classes (CNKI/VIP/Wanfang aggregators count as ONE class; CiNii / NLC / university OPACs another; the publisher or journal site a third), reached by different queries.
4. Keep every other rule as it is: verbatim check in code, no repair, drop on mismatch.

Return ONLY the functions you change or add, each as its own ```python block, each block preceded by a line `### replace <function_name>` (or `### add <function_name> after <existing_function_name>`). Whole functions, not fragments. Then one short paragraph saying what changed. Do not return the whole script.

=== build_keys.py (numbered) ===
