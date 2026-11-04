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
