<!-- merged by anthropic/claude-opus-5.5 via OpenRouter BYOK, generation gen-1793773244-VSjVM7h5pt5jWsc46O1m -->

# Merged evaluation design: LLM bibliographic-lead screening

## A. Item set

**Size.** Use 120 real items and 16 negative controls. Every model gets every item.
- The binding constraint is answers per model. Certifying harm below about 15% needs roughly 20–30 answers. A model that answers 25% of the time yields 30 answers from 120 real items.
- Model calls are cheap: 8 models × about 190 calls (items, paraphrases and repeats) is about 1,500 calls, a few dollars. Human key verification is the real cost, so items are capped at 120.

**Construction, key-first.**
- Randomly sample articles from journals' own tables of contents (周易研究, 中国哲学史, 简帛, 出土文献, *Early China*, *T'oung Pao*).
- Randomly sample books from catalogue subject headings and publisher lists, using search results beyond page 1.
- Snapshot each record with its URL. A second person re-pulls the record from an independent primary source.
- If the two sources disagree, drop the item. Never correct it. This prevents a repeat of the pilot's year error.

**Strata.** Hit these margins only; do not fill every cross-cell.

| Dimension | Split |
|---|---|
| Fame (fixed external proxy: CNKI citations or catalogue holdings) | 20% famous, 40% mid, 40% obscure |
| Type | 60% journal articles, 40% books or editions |
| Language | 80% Chinese, 20% English |
| Date | pre-2000 / 2000–2015 / 2016+, including about 10 items published after most models' cutoffs (reported separately) |

**Negative controls (16, about 12%).** Each is built so that non-existence is proven positively, not inferred from a failed search. Two types:
- **Author-bibliography probes.** Pair a real scholar with a plausible topic they never wrote on. Use only scholars whose complete bibliography is checkable (CNKI author page or CV).
- **Issue-level probes.** Ask for an article on a topic in a specific journal issue whose complete table of contents has been checked.

Controls are matched in style to real items, interleaved, and scored separately.

## B. Question wording rules

1. Use one fixed template that mirrors real pipeline queries:
   - work type, field, and a topic paraphrased from the record's own abstract or keywords;
   - exactly one anchor (author or venue, not both);
   - a decade, not a year.
2. Never use title words, distinctive searchable phrases, or more than one scored field.
3. **Identifiability check.** Run each description through the search API.
   - If it does not retrieve the key, rewrite or drop the item.
   - If several works fit, tighten the description or list every fitting work as an acceptable key.
4. A second reader checks each description against the record, which addresses the pilot's misdescription error. A clue found to be bad after the run voids the item for all models.
5. The instruction requests structured fields (author, title, venue/publisher, year, volume/issue) and says "If you do not know, say 'I don't know'; do not guess." It does not reveal that some works are fake.
6. No tools, no follow-ups. Freeze the prompt after testing it on excluded items.

## C. Scoring definitions

**Normalize first:** convert traditional to simplified, strip punctuation and subtitles, and accept pinyin or Wade-Giles variants. An LLM may extract and normalize fields, blinded to model identity, but never gives a verdict.

| Category | Definition |
|---|---|
| **Answered** | A title is asserted. Hedged answers count, because the pipeline will chase them. "I don't know," an author-only guess, or topic-level speculation counts as abstention. |
| **Correct** | Author, title (character similarity ≥0.85) and venue/publisher all match. Year (exact for journals, ±1 for books) is scored separately as detail accuracy. |
| **Near-miss** | Not correct, but author matches, and searching the model's own fields returns the key record in the top 3. Fully mechanical. |
| **Wrong-real** | The model's fields retrieve a real but different work. |
| **Invented (confirmed)** | Positive contradiction: the checked complete table of contents or author bibliography excludes it, the volume/issue is impossible, or it is a hybrid of two verified records. On controls, any specific record counts as invented. |
| **Unresolved** | Nothing found after a logged protocol (title+author search, title-only search, catalogue query), but no positive contradiction. |

- **Harmful** = wrong-real + invented + unresolved. Invented and unresolved are reported separately.
- **Usable** = correct + near-miss.
- Every answer is either usable or harmful, so a separate precision gate would be redundant.
- A human adjudicates, blind to model identity, every invented or unresolved flag, plus a random 15% of other verdicts.

## D. Pre-registered decision rule

Freeze items, keys, prompt and thresholds with a date before the first call.

**Statistics.**
- Harm upper bounds use one-sided 95% Clopper–Pearson. Zero harms in n answers gives an upper bound of 1 − 0.05^(1/n): 0/19 ≈ 14.6%, 0/30 ≈ 9.5%, 1/30 ≈ 14.8%.
- Lower bounds use Wilson 95%.

**Reject** if any of:
- the Wilson lower bound on harm exceeds 10% (the pilot's prolific inventor at 24/120 harms has a lower bound of about 13.8%);
- 3 or more of the 16 controls are invented (a true 5% fabricator reaches this only about 4% of the time);
- usable answers are fewer than 15 of 120 real items, meaning it contributes almost nothing.

**Admit** if both:
- harm upper bound is at most 15%, and
- usable answers number at least 15.

A selective model at a 25% answer rate with 0–1 harms in 30 answers passes.

**Indeterminate (neither).** Run one pre-registered fresh 60-item extension in the same strata. If the model is still indeterminate, reject it as "not established safe," which is reported distinctly from "shown harmful."

**Ranking of admitted models.** Rank by usable leads per 100 items. Then drop any model whose correct hits are all covered by a better admitted model.

## E. Threats and guards

| Threat | Cheapest guard |
|---|---|
| Fame memorisation | Fame strata; report the famous-minus-obscure gap |
| Training contamination | Post-cutoff items; keep items private; rotate 30% per future run |
| Bad keys or bad clues | Two primary sources; snapshots; void items for all models |
| Prompt sensitivity | Paraphrase 20 items; report the spread; never pick the best template |
| Sampling | Production temperature; 3 samples on 20 items; flag unstable answers |
| Judge bias | Mechanical matching; human adjudication of all harm flags, blinded |
| Retrieval drift | Cached search strings; identical protocol for all models |
| Model drift | Log version and date |
| Order effects | Shuffle items per model |
| Unfair controls | Positively proven absence only |

## F. Disagreements

1. **Item count.**
   - Options: 60 (mimo, deepseek-v4.1); 80 (kimi); 100 (gemini); 136–150 (opus, glm); 180 (deepseek-flash); 40-item screen followed by a fresh 120-item confirmation (gpt).
   - Recommendation: 120 + 16. Below about 100 items, selective models cannot reach 20–30 answers. Gpt's two stages need 160 verified items, which costs more verification time than the call money saved.

2. **What the question gives the model.**
   - Options: title + author, asking for the rest of the record (deepseek-flash); author + exact year + keywords (gemini); author + decade (mimo); one anchor + decade (opus); content only, with no creator (kimi, glm).
   - Recommendation: one anchor + decade. Giving the title tests record completion, not lead-finding. Giving no anchor makes many items unidentifiable.

3. **Which fields decide correctness.**
   - Options: title + author only (gemini); title + author + year (mimo); all four fields including year (deepseek-v4.1); author + title + venue, with year scored separately (opus, glm, kimi).
   - Recommendation: the last option. The pilot showed years are error-prone, even in keys.

4. **Near-miss definition.**
   - Options: field-based only (deepseek, gpt, kimi); retrievability at top 1 (gemini), top 3 plus an edit-distance limit (mimo), or top 5 (opus).
   - Recommendation: author match plus top-3 retrieval. It is mechanical, and the author condition keeps a near-miss meaning-preserving.

5. **How "invented" is established.**
   - Options: zero search hits counts as invented (gemini; opus, labelled "non-retrievable"); positive contradiction required, with failures left unresolved (gpt, kimi, mimo, deepseek-v4.1).
   - Recommendation: require positive contradiction, but count unresolved as harmful in the decision (gpt, mimo). This is honest about non-existence while matching opus's point that the pipeline cost is the same.

6. **Is wrong-real harmful?**
   - Options: the decision rests on inventions only (gemini, mimo admit rule); wrong-real is harmful (opus, gpt, deepseek, glm).
   - Recommendation: harmful. A misattribution can contaminate the ledger just as an invention can.

7. **Control design and count.**
   - Options: 4 false-premise variants (gpt); 8 issue-level probes (kimi); 10–20 author-topic probes (opus, gemini, glm); 12–60 recombinations of real author and real title (mimo, deepseek-v4.1, deepseek-flash).
   - Recommendation: 16 controls using author-bibliography and issue-level probes. Recombinations cannot prove absence. Four controls give no usable rate.

8. **Telling models that fakes exist.**
   - Options: yes (mimo); abstention permitted only (others).
   - Recommendation: abstention permitted only. Production prompts will not warn about fakes.

9. **Controls in the decision.**
   - Options: pooled into the invention rate (deepseek-v4.1); a separate gate (deepseek-flash, opus, mimo); report only (gpt, kimi).
   - Recommendation: a separate gate. It is the only direct test of fabrication under pressure.

10. **Thresholds.**
    - Options: point estimates only (gemini: ≥20% answer rate, ≥80% accuracy, ≤5% invention); invention = 0 (mimo); bounds-based with harm upper bound ≤10–20% (others).
    - Recommendation: bounds-based, harm upper bound ≤15%. Point estimates cannot separate skill from luck at n ≈ 20. A ≤10% ceiling needs about 30 clean answers, which only frequent answerers can supply.

11. **Coverage floor.**
    - Options: 12.5% yield (opus); 20% (gemini, kimi); a Wilson lower bound of 15% (deepseek-v4.1, gpt); 30 answers (glm); 33% (mimo).
    - Recommendation: 15 usable answers out of 120. It is stated in useful output rather than answers, and admits genuinely selective models.

12. **Binary versus three-zone rule.**
    - Options: binary (gemini, kimi, deepseek); indeterminate zone with a top-up or extension (glm, mimo); net-utility ranking with k = 3 (opus).
    - Recommendation: three zones with one extension. Utility weights hide uncertainty, while the extension costs only cents of calls.

13. **Temperature.**
    - Options: 0 (most proposals); production setting (opus, gpt).
    - Recommendation: the production setting, with repeat samples. The evaluation should measure deployed behaviour.

14. **Prompt sensitivity.**
    - Options: pick the better of two templates (gemini); use the worse result (opus); subsample audit (others).
    - Recommendation: freeze one template and audit on a subsample. Picking the best template biases results toward it.

15. **LLM role in judging.**
    - Options: none (deepseek, gemini); extraction only (opus, glm, kimi, mimo, gpt).
    - Recommendation: extraction only, with human adjudication of every harm flag. It is cheap, and verdicts stay human.

16. **Fame mix.**
    - Options: equal thirds (deepseek, kimi, mimo); 20/50/20 (gemini); 40/30/30 (glm); 20/40/40 (opus, gpt).
    - Recommendation: 20/40/40. The pipeline's value lies in non-famous works.

17. **Interval method.**
    - Options: Wilson (several); Clopper–Pearson (kimi, gpt); rule of three (glm, mimo).
    - Recommendation: Clopper–Pearson for harm upper bounds, because it is exact and conservative at zero harms. Wilson elsewhere.
