# Source Texts — Original Chinese (卦辞 + 爻辞)

This reference carries the **original Chinese** of each hexagram so the skill can read from the source rather than recall line texts from memory. Backing data: `zhouyi-source.json` (this directory).

## Why this exists

- **Source before translation** — the nearest legible layer to the bare pattern.
- **Copyright** — Wilhelm / Huang / Lynn are copyrighted and must not be reproduced. The ~3,000-year-old Chinese is public domain: quote it, then translate *fresh*.
- **Provenance** — retrieval is generation; a line-text recalled from memory is reconstructed, not replayed (highest fabrication risk). Read it from here instead. **If an entry is missing, say so — never fill from memory.**

## Data format (`zhouyi-source.json`)

```json
{
  "source": "ctext.org (Chinese Text Project), Book of Changes, original text",
  "fetch_date": "YYYY-MM-DD",
  "method": "how the text was fetched and checked",
  "count_ok": 64,
  "note": "...",
  "gaps": [],
  "hexagrams": [
    {
      "kw": 1, "name_zh": "乾", "symbol": "䷀", "pinyin": "Qián",
      "slug": "qian", "url": "https://ctext.org/book-of-changes/qian",
      "judgment_zh": "元亨,利貞。",
      "lines_zh": ["初九:潛龍,勿用。", "...6 lines, bottom→top..."],
      "extra_line_zh": "用九:見群龍无首,吉。",   // only hex 1 (用九) and 2 (用六)
      "image_daxiang_zh": "天行健,君子以自強不息。"
    }
  ]
}
```

## How a reading uses it

1. After structural analysis (SKILL.md Step 2), at Step 3 look up the cast hexagram by `kw`.
2. Quote `judgment_zh`; for changing lines, quote the matching entry in `lines_zh` (index 0 = line 1, bottom).
3. Render a **fresh** English translation shaped by the structural reading already done — not a recitation.
4. Optionally show a literal character gloss for graph-level features (e.g. a doubled or negated title-character in a line).
5. The `image_daxiang_zh` (大象) is the *Image commentary's* prescription ("the superior person…"). Treat it as a response-layer, not the hexagram's bare statement — see SKILL.md "No Moralism" / "don't import 大象 as instruction."

## STATUS

**Complete.** `count_ok: 64`, `gaps: []`: all 64 records carry text. The JSON's own `method` and `note` fields say how the 26 formerly empty records were filled and the other 38 re-checked against ctext.

If a field is ever `null`, the skill must fall back to structural reading and **state that the source quotation is unavailable** — it must not substitute a remembered line text.
