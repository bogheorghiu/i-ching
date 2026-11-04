# Calibration run 1: is model memory of Chinese bibliography worth asking? (pre-registration)

Written 2026-11-04, before any model was asked. Committed before the run; nothing below changes after it. A deviation decided after launch is appended under "Deviations", with its reason, before scoring.

## Question

Do the lead models of `docs/research-method.md` step 2, asked cold, recall the venue and year of five works whose records the 2026-11-02 audit already settled?

## Arms

All through OpenRouter, `"provider": {"zdr": true}`, temperature left at the provider default, one request per question per arm (owner's roster, 2026-11-04):

1. `deepseek/deepseek-v4.1-flash-1017:exacto`, `reasoning: {"effort": "max"}`
2. `deepseek/deepseek-v4-pro:exacto`, `reasoning: {"effort": "max"}`
3. `moonshotai/kimi-k3.1-pro:exacto`, `reasoning: {"effort": "max"}`

If an arm rejects `max`, it is re-run once with `xhigh`, and that is recorded. If an arm has no ZDR `:exacto` endpoint (an error, no fallback), it is void and reported as void.

## Questions (as sent; no venue, year or title is given)

The prompt is in `run.py` (`PROMPT`). Each asks for the bibliographic record as JSON (author, title, venue, year, issue, pages, url, search_terms), and says that 不知道 / null is an acceptable answer.

1. Zhang Zhenglang's article that first identified numerical sequences on early Zhou bronze inscriptions as Yi hexagrams.
2. Jia Lianxiang's article on the number systems (用数体系) of excavated numerical hexagrams.
3. Li Zongkun's article arguing that numerical diagrams and yin-yang line hexagrams are two separate systems.
4. Adam C. Schwartz's English-language article on numbers and hexagram pictures in excavated texts, published in a Hong Kong sinology journal.
5. Jia Lianxiang's book collecting and annotating excavated numerical-hexagram documents.

## Answer keys (from the audit's `REGISTER.md` and verifier reports; personal-use-tools branch `archive/i-ching-audit-2026-11-02`)

| Q | Venue key (any alias matches) | Year | Also recorded, not scored |
|---|---|---|---|
| 1 | 考古學報 / 考古学报 / Kaogu xuebao | 1980 | no. 4, pp. 403–415 |
| 2 | 周易研究 / Zhouyi yanjiu | 2014 | no. 6, pp. 29–32 |
| 3 | 中央研究院歷史語言研究所集刊 / 历史语言研究所集刊 / BIHP / Bulletin of the Institute of History and Philology | 2006 | 77(2): 279–318 |
| 4 | Bulletin of the Jao Tsung-I Academy of Sinology / 饒宗頤國學院院刊 | 2018 | no. 5, pp. 47–85 |
| 5 | (a book: venue not scored; publisher is a Gap in the register) title contains 数字卦 or 數字卦 | 2021 | 《出土数字卦文献辑释》 |

## Scoring (mechanical, in `score.py`)

Per answer:

- **don't-know**: the model says 不知道 / unknown, or gives no venue and no year.
- **confirmed**: venue matches a key alias (case-insensitive substring after removing spaces; for Q5, the title test) **and** year equals the key.
- **fabricated**: not confirmed, gives a title, and a DeepSeek search for that exact title returns no result whose title or snippet contains the given title's first eight characters (CJK) or first four words (Latin).
- **wrong**: everything else that is not confirmed.

## Ship rule

Per arm, over the answers that are not don't-know (the "leads given"):

- the arm **stays** in step 2 iff confirmed ≥ 60% of leads given **and** fabricated ≤ 20% of leads given, and it gave at least 3 leads;
- otherwise it is dropped from step 2.

If no arm stays, step 2 is dropped and the pipeline starts at retrieval. The bar is the owner's to change, but only before this file is committed; after that, a changed bar applies to the next run, not this one.

## What this run cannot show

N = 5 per arm. It can show a gross failure (an arm that invents records) or a clear pass; it cannot rank arms that are close. The five works were chosen because the audit settled them, which favours well-cited works; recall of obscure items will be worse. "Fabricated" depends on DeepSeek search coverage: a real item it fails to find is scored fabricated (errs against the model).

## Records

`results/` gets, per request: the raw response, the OpenRouter generation ID, the cost from the generation record, and the DeepSeek search request and response used for the fabricated test.

## Deviations

(none yet)
