# Remaining page-range lookup checklist

Final JSONL: `papers.jsonl`

These four values are verified start pages only. They must remain unchanged unless an opened source explicitly displays a complete page range. Do not infer an end page from the next article, a page count, a PDF URL, or citation conventions.

| JSONL line | Article | Authors | Article identifier | Current `pages` | Evidence needed to finish |
|---|---|---|---|---|---|
| 4 | 《易林》校补十则 | 余格格、周晟 | ZYJY201602005 | `32` | An opened article or issue page explicitly showing the full first–last page range. |
| 5 | 旅轩张显光的太极观 | 郑炳硕 | ZYJY201602006 | `37` | An opened article or issue page explicitly showing the full first–last page range. |
| 6 | 丁若镛与吴澄的《周易》解释方法比较 | 林在圭、张悦（译） | ZYJY201602007 | `45` | An opened article or issue page explicitly showing the full first–last page range. |
| 8 | 论毛泽东辩证思想的《周易》来源 | 史衍朋、高奇 | ZYJY201602009 | `64` | An opened article or issue page explicitly showing the full first–last page range. |

## Acceptance rule for any future update

1. Open the source page successfully; a search-result URL alone is insufficient if its content is not visible.
2. Confirm that the page concerns the exact article identifier/title above.
3. Copy the displayed complete range literally into `pages`.
4. If adding the page as a source, transcribe only visible `fields_seen` values and leave unseen fields as empty strings.
5. Re-run `python validate_papers.py` after editing.
