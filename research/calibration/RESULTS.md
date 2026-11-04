# Calibration run 1: results (2026-11-04)

Scored mechanically by `score.py` under `PREREG.md`, unchanged after the run. Raw responses, generation IDs, OpenRouter cost records and the DeepSeek search log are in `results/`. No deviations.

| Arm | Q1 | Q2 | Q3 | Q4 | Q5 | Leads | Confirmed | Fabricated | Rule | Cost |
|---|---|---|---|---|---|---|---|---|---|---|
| deepseek-v4.1-flash-1017:exacto | confirmed | confirmed | confirmed | fabricated | wrong | 5 | 3 (60%) | 1 (20%) | **stays** (exactly at both limits) | $0.0054 |
| deepseek-v4-pro:exacto | confirmed | don't-know | wrong | fabricated | wrong | 4 | 1 (25%) | 1 (25%) | dropped | $0.0328 |
| kimi-k3.1-pro:exacto | confirmed | don't-know | don't-know | don't-know | don't-know | 1 | 1 | 0 | dropped (fewer than 3 leads) | $0.0853 |

All 15 requests used `reasoning.effort = "max"` on a ZDR `:exacto` endpoint; none fell back.

**Decision under the pre-registered rule:** step 2 of `docs/research-method.md` keeps DeepSeek V4.1 Flash 1017 only. V4 Pro and Kimi K3.1 Pro are dropped from step 2 on this evidence.

## Observations (not used to change any score)

Recorded so a later run can test them; none of them moves a verdict above.

- **Q4 "fabricated" is partly a scorer artifact.** V4 Pro's title, "Between Numbers and Hexagrams ...", begins like the real article's title as the audit recorded it; DeepSeek search did not find it, so the rule scored it fabricated (PREREG.md said this errs against the model). Both DeepSeek arms gave the wrong venue ("Journal of Chinese Studies"), so neither would have been confirmed anyway.
- **Q5's key year may itself be wrong.** Both DeepSeek arms answered 中西书局, 2020, and V4 Pro gave the exact title 《出土数字卦文献辑释》. The key's 2021 comes from the audit register, which gives no publisher (a Gap). Until the book's own record is read, Q5 counts as wrong for both arms.
- **Kimi K3.1 Pro abstained four times out of five, and invented nothing.** Under this rule that drops it. For a lead step where a fabrication costs more than an abstention, its behaviour may be the more useful one; that is a question for the next bar, not a re-reading of this one.
- **Flash passed at the margin**, on N = 5 well-cited works. This shows the arm is not grossly unreliable; it does not show it is reliable on obscure items.

## Key audit after run 1 (2026-11-04): the pre-registration was wrong in two places

Checked through DeepSeek search against records that are the fact's own or close to it; raw responses in `keycheck/search.json`.

- **Q5 key: CONTRADICTED.** The key said 2021 (from the audit register, which gave no publisher). The records say 中西书局, August 2020, ISBN 978-7-5475-1691-1: CiNii's catalogue record (ci.nii.ac.jp/ncid/BC09213224, "中西書局, 2020.8"), the publisher's own page (shsjcb.com, bkid 280204), and a review in *Dao* (link.springer.com, 10.1007/s11712-021-09808-6: "Shanghai: Zhongxi Shuju, 2020"). GROUNDED: 2020.
- **Q4 question: misdescribed.** The work is A. C. Schwartz, "Between Numbers and Images: The Many Meanings of Trigram Li 離 in the Early Yijing", *Bulletin of the Jao Tsung-I Academy of Sinology* 5 (June 2018), 47–85 (the author's CV at HKBU; cited so in *Bamboo and Silk* 5, 2022). The prompt described it as an article "on numbers and hexagram pictures in excavated texts", which is the footnote the audit used, not the article's subject. The venue key stands; the question pointed models at a topic, not at this article.
- **Q1, Q2, Q3 keys: GROUNDED.** Q1 by VIP's record (《考古学报》1980年第4期 403–415); Q2 by Tsinghua's own list (《周易研究》2014年06期); Q3 by Academia Sinica's repository (第77本第2分，頁279-318, 2006-06).

What it obliges: the pre-registered verdicts above stand as the record of what the rule said; the owner decides whether the corrected-key table below replaces them. Lesson carried into run 2: every key is checked against its own record **before** the run, and every question is checked to describe the work it means.

## Run 1b: MiMo 2.6 Flash, MiMo 2.6 Pro, GLM 5.3 (original keys, as pre-registered)

| Arm | Q1 | Q2 | Q3 | Q4 | Q5 | Leads | Confirmed | Fabricated | Rule | Cost |
|---|---|---|---|---|---|---|---|---|---|---|
| mimo-v2.6-flash:exacto | confirmed | don't-know | don't-know | don't-know | don't-know | 1 | 1 | 0 | dropped (< 3 leads) | $0.0009 |
| mimo-v2.6-pro:exacto (no reasoning param) | wrong (《考古》) | don't-know | don't-know | don't-know | confirmed (2021) | 2 | 1 | 0 | dropped (< 3 leads) | $0.0035 |
| glm-5.3:exacto | wrong (1984) | don't-know | don't-know | don't-know | don't-know | 1 | 0 | 0 | dropped (< 3 leads) | $0.0198 |

## All six arms with the corrected keys (Q5 = 2020), labelled: not the pre-registered verdict

Q4 is also adjudicated by hand where the owner's rule (2026-11-04: a near-right title is not an invention) applies: V4 Pro's "Between Numbers and Hexagrams" for "Between Numbers and Images", wrong venue, counts **wrong**, not fabricated. Flash's Q4 ("Numbers and Hexagram Pictures in the Shanghai Museum ...", 2015, wrong venue) stays **fabricated**.

| Arm | Confirmed / leads | Fabricated | Abstained | Under the same bar |
|---|---|---|---|---|
| deepseek-v4.1-flash-1017 | 4 / 5 | 1 | 0 | stays |
| deepseek-v4-pro | 2 / 4 | 0 | 1 | dropped (50%) |
| kimi-k3.1-pro | 1 / 1 | 0 | 4 | dropped (< 3 leads) |
| mimo-v2.6-flash | 1 / 1 | 0 | 4 | dropped (< 3 leads) |
| mimo-v2.6-pro | 0 / 2 (Q5 now wrong: 2021) | 0 | 3 | dropped |
| glm-5.3 | 0 / 1 | 0 | 4 | dropped |

Five answers per arm cannot separate "abstains often but is right when it answers" from luck. That is run 2's job.
