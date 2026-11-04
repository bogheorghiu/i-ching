# Research method for Chinese-language sources (proposal)

**Status: a proposal, 2026-11-03. The owner may change any part of it.** It sits outside `plugins/`, so it does not ship. The open work it leads to is tracked in this repository's issues, not here.

## Why a method at all

The skill's facts about the Chinese text and its history come from Chinese scholarship (journals such as 周易研究 and 考古學報, excavation reports, critical editions). Much of it is hard to reach from outside China: behind CNKI, in printed books, or on sites such as ctext.org that ask automated readers not to scrape them. The 2026-11-02 claims audit showed what goes wrong without a method: a model can describe an article confidently and in detail, and the details can still be invented.

## Principle: a model's memory gives leads, never evidence

What a model "remembers" about a Chinese article is a reconstruction: for a model, recalling and generating are the same act, separated only by confidence. It becomes evidence only when a retrieval tool brings back the record itself: the database entry, the PDF, the ctext page.

DeepSeek and Kimi agreeing from memory confirms nothing. They learned from much the same Chinese web, so their errors are correlated, and two copies of one mistake read like corroboration.

## Pipeline

1. **Pre-register the question.** Before any model is asked, write down what result would confirm the claim, what would disconfirm it, and what a null result looks like. A null is reported as a null.
2. **Leads from memory.** Ask DeepSeek V4 Pro (`deepseek/deepseek-v4-pro`), DeepSeek V4.1 Flash (`deepseek/deepseek-v4.1-flash-1017`) and Kimi K3.1 Pro (`moonshotai/kimi-k3.1-pro`) through OpenRouter, each cold, with no hints. These are the owner's choice of 2026-11-03. Every request sets `"provider": {"zdr": true}`, OpenRouter's per-request zero-data-retention switch (OpenRouter docs, "Provider Routing" and "Zero Data Retention", read 2026-11-03: it restricts routing to ZDR endpoints, plus "Safety Retention" endpoints unless the account is set to ZDR only). Whether each of these three models has a ZDR endpoint at all is UNRESOLVED until the first request. If one has none, the request fails rather than falling back, and that is recorded.
   - Ask for: author, title, journal, year, issue, pages, where it is online, and Chinese search terms.
   - Allow 不知道 ("don't know") and never penalise it. A model that says it doesn't know has given more than one that invents.
   - Record every OpenRouter generation ID; the owner can pull the logs by them.
3. **Retrieval through DeepSeek's tool API.** `POST https://api.deepseek.com/v1/tools/search` with a JSON body `{"query", "count", "need_content"}`, and `POST https://api.deepseek.com/v1/tools/fetch` with `{"url"}`. In the audit, the search found records in Chinese databases (维普 / VIP, 万方 / Wanfang) that ordinary web search did not. This API offers no zero-retention guarantee, so it gets only public, academic queries, never private data. For a `.doc` or `.pdf` at a public URL, a document parser (such as the Unstructured connector, which parses files at public `https://` URLs) is tried first. The first test case is Jia Lianxiang 2014's attachment `shuziguayongshu.doc`, linked from `ctwx.tsinghua.edu.cn/kxyj/xswk/zgjbyj/2.htm`. In the audit, fetch tools returned binary for it, DeepSeek fetch returned 404, and the sandbox proxy refused the host.
4. **Whatever is closed to agents** (ctext, CNKI, printed books) goes to the owner: in a browser, or in the Kimi app. The app, not only the model, searches the Chinese web from inside it and reads long PDFs, and the owner has used it before to reach Chinese-language data that is hard or impossible to get cheaply from outside China. Agents do not get around ctext's notice to automated readers.
5. **A ledger.** For each lead: the quote, URL, date, tool, request or generation ID, how it was read (raw bytes, or through an extractor), and a tier per claim (GROUNDED / UNRESOLVED / CONTRADICTED, Gap for a needed piece that is missing). Anything that came only from memory stays marked "lead".

## Cost

A script runs the whole loop (leads, search, fetch, ledger), and Claude only judges at the end, so Claude usage goes to judgment, not to fetching. The script can run as a scheduled task in a Claude Code cloud environment with the API keys as that environment's secrets, which is also how the DeepSeek key leaves the claude.ai Project document it sits in today (tracked in an issue). An alternative is Hermes Agent, which documents a `web-deepseek` plugin; whether the owner's install has it is unverified.

## The assumption it rests on

That DeepSeek's and Kimi's memory of Chinese bibliography is good enough for their leads to be worth what they cost. This is tested cheaply before anything relies on it: a pre-registered calibration run on five questions whose answers the audit already settled. If the leads fail the bar fixed before that run, step 2 is dropped and the pipeline starts at retrieval.
