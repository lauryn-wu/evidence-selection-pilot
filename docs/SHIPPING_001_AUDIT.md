# shipping-001: verified results and interpretation

Audited 2026-10-10. Model: gpt-4o-2024-08-06. All 144 planned calls returned,
without transport retries. All 96 selection outputs were parseable. This is one
model and 24 numerical variants of one task family.

The proposed reasoning-harm effect did not appear. Deliberation about possible
test outcomes substantially improved diagnostic selection in this pilot.

| Condition | Informative choices | Rate |
| --- | ---: | ---: |
| direct | 7/24 | 29.2% |
| facts | 8/24 | 33.3% |
| deliberate | 20/24 | 83.3% |
| explain | 11/24 | 45.8% |

## Paired comparisons

Positive differences mean more informative selections in the first condition.
The primary comparison was deliberate minus facts, not a contrast chosen after
seeing the results.

| Comparison | Difference (pp) | Descriptive 95% bootstrap interval | Gains / losses |
| --- | ---: | --- | ---: |
| deliberate - facts | +50.0 | [25.0, 70.8] | 13 / 1 |
| deliberate - direct | +54.2 | [29.2, 75.0] | 14 / 1 |
| explain - facts | +12.5 | [-4.2, 29.2] | 4 / 1 |
| explain - deliberate | -37.5 | [-58.3, -16.7] | 1 / 10 |

There are 24 paired cases, not 96 independent observations. The primary exact
McNemar p-value is 0.001831, exploratory and unadjusted. The bootstrap describes
these case variants; it is not evidence of generalization across task families.

Justification performed worse than prospective comparison but numerically better
than both direct and descriptive-summary baselines. This does not establish harm
from justification relative to those baselines, or a general harm from reasoning.

## Competence: preserve strict formatting and audit content separately

All 24 competence responses used Markdown code fences. Sixteen also represented
all six fees as quoted numeric strings. The strict original parser rejected all
24. The prompt contributed by showing quoted placeholders while requesting
numeric values. The original 0/24 competence score is therefore a strict-format
score, not a valid description of fee-prediction accuracy.

After the six-call check, and before continuing collection, a separate uniform
content audit was announced: remove a whole-response JSON code fence, interpret
plain numeric strings, and otherwise retain the original schema requirements.
No response was rerun, no wrong number was repaired, and no original flag changed.

| Measure | Strict original parser | Separate content audit |
| --- | ---: | ---: |
| Valid competence responses | 0/24 | 24/24 |
| Cases with all six fees correct | 0/24 | 23/24 |
| Correct fee cells scored | 0/144 | 143/144 |

The only incorrect fee is shipping-001, T2 under H1: the model predicted $6,
but the weight rule predicts $0. The 144 cells are not independent samples.
Among the 23 fully correct competence cases, selections were direct 7/23,
facts 8/23, deliberate 20/23, and explain 11/23. Separate competence performance
does not prove the predictions were represented correctly during selection.

The original automatic decision remains measurement_issue_review_invalid_outputs.
The content audit does not retroactively turn this into a passed original screen.
Its original paired-comparison JSON retains the strict competence subset;
supplementary content scores have explicitly separate fields.

## Raw-text observations

- Every initial guess selected the price rule: 24/24, despite H1/H2 labels being
  balanced. This is an observed preference; its internal cause was not identified.
- At least six facts responses included specific test-selection reasoning:
  shipping-003, 006, 008, 010, 014, and 021. Case 023 also stated a generic
  discriminability principle. These are manual descriptive annotations.
- All direct responses had no explanation. The requested 60-100-word range was
  met by facts 23/24, deliberate 7/24, and explain 11/24. Median word counts were
  92, 102, and 106; median completion tokens were 146, 145, and 134 respectively.
  Equal requested lengths did not enforce equal realized text.
- The four deliberate errors were shipping-001, 014, 016, and 022. Cases 001
  and 014 asserted an incorrect fee for the chosen test. Case 016 miscomputed
  the informative test and selected a test it described as having equal fees.
  Case 022 stated that T2 predicts $0 under both rules, then claimed that a $10
  outcome would confirm H2 and selected T2. That outcome is impossible under
  either supplied rule. These are observable inconsistencies, not a demonstrated
  internal mechanism or evidence that the written text caused the errors.
- Deliberate succeeded on 12/12 high-price/heavy diagnostic cases and 8/12
  low-price/light diagnostic cases. This is a post hoc descriptive slice.

## Provenance and reproducibility

All raw requests, saved parses, provider completion status, source identity, and
the frozen plan were verified. The original six smoke responses were unchanged
in the completed export. No source or raw run data was edited during the audit.

- [Original archive](../results/shipping-001.zip), SHA-256
  `6be41a130b998b73352708cec45d475db5543c9787e7124a38dc8c308852d48d`.
- Plan hash:
  `383bd6d3b8d6fb6154544469c07f9f7989745fb348fc58e03bcca347051e1b97`.
- Original source hash:
  `4f793f0e95dfb36fc554f85538ee133bcddb691e3a2da5114b0654ef70c0bb48`.

The [machine-readable content audit](../results/shipping-001-content-audit.json)
includes the scoring policy, every competence response, expected and interpreted
fees, unchanged strict scores, selection counts, and original paired comparisons.
The full original export is included and remains the source for all 144 requests
and responses. From the repository root, reproduce the separate audit using:

~~~bash
python3 -m evidence_selection_predictions audit-original --input results/shipping-001.zip --output runs/shipping-content-audit-001
~~~

This command makes no API calls and refuses to overwrite the original run or an
existing audit. The [completed follow-up](PREDICTIONS_001_AUDIT.md) used fresh cases
to test whether supplied correct predictions improve selection. It reached 24/24
with the table versus 4/24 with rules only, meeting its stopping rule. It is not
an expansion of the original reasoning-harm claim or a claim of publication-level novelty.
