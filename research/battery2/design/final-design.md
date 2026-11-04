<!-- merged by anthropic/claude-opus-5.5 via OpenRouter BYOK from 7 round-2 critiques, generation gen-1793773654-egriwSdWVh0Htzee6wuB -->

# Final pre-registered design: screening LLMs for bibliographic leads

## A. Key building without a team

1. **Primary record.** A page served by the record's custodian:
   - a journal's own table of contents (TOC) or article page;
   - a publisher catalogue page;
   - a library catalogue record (NLC, university OPAC, CiNii Books);
   - a CNKI, VIP or Wanfang item page showing full fields;
   - a page image of front matter.

   Snippets, citing papers, reference lists, encyclopedias and LLM output never qualify.
2. **Sampling.** Use the search API with random offsets beyond page 1, within journal TOCs (周易研究, 中国哲学史, 简帛, 出土文献, *Early China*, *T'oung Pao*) and publisher or catalogue subject lists. Fetch each record and store the snapshot, URL, identifier, query and date (retrieval A).
3. **Retrieval B must be independent.** It runs in a fresh session from a different custodian class, using a different route (ISSN plus issue browse, or ISBN; never the same title query). Two aggregators (CNKI, VIP or Wanfang) never count as an independent pair, because they repackage the same publisher metadata.
4. **Extraction.** A cheap LLM extracts fields. Code checks that each field appears verbatim in its snapshot. If not, the item is dropped.
5. **Comparison in code.** After normalisation (traditional to simplified, punctuation stripped, romanisation variants accepted), any mismatch in author, title, venue or year drops the item. Keys are never repaired.
6. **Recoverability gate.** The scoring search protocol must find the key from its own fields. This drops records the search tools cannot see, so retrieval blindness is not later scored as model harm.
7. **Drop rules.** An item is dropped if it has no second independent record, any field disagreement, an unfetchable source, a failed recoverability check or a failed clue check (C).

## B. Item set and negative controls

**Real items.** 300 tool-verified items, frozen before any model call, in six disjoint 50-item blocks. Each block is stratified identically on:

| Dimension | Split |
|---|---|
| Fame (CNKI citations or catalogue holdings) | 20% famous / 40% mid / 40% obscure |
| Type | 60% articles / 40% books or editions |
| Language | 80% Chinese / 20% English |
| Date | pre-2000 / 2000–2015 / 2016+ (about 15 items post-cutoff, also reported separately) |

Blocks 1–4 form the main set. Blocks 5–6 are reserved for extensions only.

**Negative controls.** 24 controls, interleaved with the real items and matched in style.
- **Issue probes.** Ask for an article on a plausible topic in an issue whose complete TOC two custodians agree on, with continuous pagination.
- **Author probes.** Pair a real scholar with a topic absent from two agreeing complete bibliographies.
- **Absence check.** Absence is established by code as non-membership in the extracted TOC or bibliography. It is never inferred from zero search hits.

## C. Question wording

1. **Template.** Work type, field, a topic paraphrased by an LLM from the record's abstract or keywords, exactly one anchor (author or venue), and a decade.
2. **Leakage check.** Code rejects any clue sharing a 3-character Chinese n-gram (or a 2-word English n-gram) with the title.
3. **Identifiability.**
   - The clue must retrieve the key in the search API's top 10.
   - A different-family LLM compares the top 10 against the clue and may add other fitting works as acceptable keys or drop the item. It never approves an item.
4. **Instruction.** "Give author, title, venue/publisher, year, volume/issue. If you do not know, say 'I don't know'; do not guess." Fakes are not mentioned.
5. **Run settings.**
   - No tools and no follow-up questions.
   - Production temperature, with reasoning set to minimal and a 250-token cap.
   - Item order shuffled per model.
   - Prompt frozen after testing on excluded items.

## D. Scoring

All verdicts below are made by code over snapshots. LLMs only extract fields from model answers, blinded to model identity, with evidence spans checked by code.

| Category | Rule |
|---|---|
| **Abstain** | "I don't know," an author-only guess, or topic talk with no title |
| **Answer** | Any asserted title, hedged or not |
| **Correct** | Author matches, title character similarity ≥0.85, venue matches |
| **Near-miss** | Author matches; title similarity ≥0.5 or venue matches; and searching the model's fields returns the key in the top 3 |
| **Wrong-real** | The model's fields match a different, fetched real record |
| **Invented** | Positive contradiction: excluded by a complete TOC or bibliography, an impossible volume or issue, or a hybrid of two fetched records |
| **Unresolved** | Not found by a two-pass protocol: (1) title+author, title-only and catalogue queries; (2) fetch the claimed issue's TOC |
| **Ambiguous** | Title similarity between 0.5 and 0.85 without retrieval, or a rule conflict. An LLM drafts a verdict for possible human review |

- **Harm** = wrong-real + invented. On controls, any wrong-real or invented answer is a control failure.
- **Denominators.** Harm rates are per answer; yield is per item. Year accuracy is reported separately.
- **Sensitivity rule.**
  - Each verdict is computed twice: with every unresolved and ambiguous flag counted as harm (worst case) and as non-harm (best case).
  - If both agree, no human review is needed.
  - If they disagree, those flags enter the adjudication queue.
  - Disagreements still unadjudicated after the budget is spent make the model indeterminate. An LLM-drafted verdict therefore never decides an outcome.

**The human's 20 adjudications,** blinded to model identity, each shown the snapshots and the LLM draft:
- **3** random audits of accepted keys, before the run.
- **2** audits of control-absence evidence, before the run.
- **2** random audits of code-confirmed harms, after the run.
- **13** flags whose flip would change a model's zone, ordered by priority:
  1. control failures that create the ≥2-failure rejection;
  2. sensitivity disagreements;
  3. block-breach harms.
- **Audit failure.** Any failed audit suspends the rule involved, and its verdicts become ambiguous.
- **Spare slots** go to random audits of "correct" verdicts.

## E. Decision rule (frozen and dated)

**Intervals.** One-sided 95% Clopper–Pearson throughout. Reference points: 0/19 harms gives an upper bound of 14.6%; 1/30 gives 14.8%.

**Reject, shown harmful,** if any of:
- the harm lower bound exceeds 10%;
- 2 or more confirmed control failures;
- **block breach:** in any block, harms exceed max(1, ⌊0.15 × that block's answers⌋), meaning accuracy does not hold across item sets.

**Reject, negligible yield,** if the upper bound on correct answers per item is below 5%.

**Admit** if all of:
- pooled harm upper bound ≤15%;
- no block breach;
- ≤1 control failure;
- lower bound on correct answers per item ≥5% (about 16 correct of 200);
- the verdict is robust under the sensitivity rule.

**"Swing while accuracy holds" test.**
- For every model, report each block's answer rate, a Fisher–Freeman–Halton test across blocks, and the max/min ratio.
- Label the model **"set-dependent rate"** if p < 0.05 or the ratio exceeds 2; otherwise **"stable."**
- This label never affects admission.
- The decision-maker's case is therefore tested directly. A model with heterogeneous answer rates, accuracy holding in every block (no breach) and non-negligible pooled yield is admitted.

**Rule validation.** Before freezing, simulate the rule (10,000 runs per profile) and record admission probabilities:

| Profile | Required outcome |
|---|---|
| Answer rate alternating 10%/30% by block, 2% harm | Admit |
| Answer rate 20%, harm 20% | Reject |
| Answer rate 3%, 0% harm | Negligible yield |
| 5% fabricator on controls | Admission probability reported |

If the first three outcomes are not achieved, thresholds are revised before freezing.

**Indeterminate.** Add reserve block 5 and recompute over all blocks; then block 6. A model still indeterminate is reported as **"not established."** This is not admission, and it is reported distinctly from "shown harmful."

**Ranking of admitted models.**
1. Rank by correct answers per 100 items, with near-misses as the tie-break.
2. Drop any model whose correct hits are all covered by a better admitted model.

## F. Threats and guards

| Threat | Guard |
|---|---|
| Bad keys | Independent custodians; code comparison; drop rather than repair; 3 audits |
| Search blindness scored as harm | Recoverability gate; unresolved handled by sensitivity rule only |
| Circular near-miss | Field condition required in addition to retrieval |
| API outage | Health check on keys before scoring; failed calls marked missing and rerun; searches cached |
| Fame memorisation or narrow coverage | Fame strata; report famous-minus-obscure gaps in answer rate and harm |
| Contamination | Post-cutoff items; items kept private; reserve blocks rotate into future runs |
| Prompt sensitivity | One paraphrase on 30 items; spread reported; never select the best template |
| Sampling noise | 2 extra samples on 40 items; unstable answers flagged |
| Judge bias | Code verdicts; blinded human; LLM never decides |
| Order or drift effects | Shuffle per model; log model versions and dates |

## G. Critiques not adopted

- **LLM classifies unresolved/wrong-real flags (Gemini):** forbidden by the hard constraint.
- **LLM semantic near-miss check (Gemini):** replaced by a code-checked field condition.
- **Human reviews only the top model's margin cases (Gemini):** would leave rejections unverified.
- **Per-stratum yield floors (Gemini, DeepSeek-v4.1):** would punish exactly the swing the decision-maker wants admitted; gaps are reported instead.
- **Control gate as a percentage of answered controls (Gemini):** a fixed ≥2 is already stricter for selective models.
- **No extension (DeepSeek-flash):** reserve blocks are tool-built and cost no human time.
- **Unresolved reported only, never harmful (DeepSeek-flash, mimo):** the sensitivity rule handles it without either ignoring it or assuming harm.
- **Issue-TOC-only controls (DeepSeek-flash):** author probes are kept, but only with two agreeing complete bibliographies.
- **Aggregators as corroboration only (Kimi):** too few primary records would remain; aggregator-plus-aggregator pairing is banned instead.
- **Three 40-item sets (Kimi):** four 50-item blocks give more power per block.
- **5 samples on every item, 400-item cap (Opus):** exceeds budget; 300 items already gives about 30 answers at a 10% answer rate.
- **Pooling controls into the harm bound (GLM):** double-counts and mixes pressure-testing with base rates.
- **Floor on answered items ≥20 (mimo):** answers include harms; a floor on correct yield is cleaner.
- **12 controls (mimo):** weakens the control gate.
- **Stop if audit error exceeds 2% (mimo):** 7 audits cannot estimate a 2% error rate.

## H. Cost

**Model under evaluation (per model).**
- 224 items, plus 80 repeat samples, plus 30 paraphrases: about 334 calls.
- Up to 100 more calls if extended.
- Roughly 120k input and 50k output tokens.
- Cost: about $0.05–0.10 for cheap models, up to about $1.50 for premium models.

**Tooling (shared).**
- About 2,500 cheap-LLM calls for extraction, clue drafting and scoring: about $0.30–0.50.
- Search and fetch calls are not counted against the model budget.

**Total.** About $3–5 for 8 models, roughly 2,700 evaluation calls plus tooling.

**Overrun rule.** If the projected cost exceeds $5, cut paraphrases first, then repeat samples, never items or controls.
