# Supplied predictions: completed diagnostic

The `predictions-001` run completed all 72 planned calls on `gpt-4o-2024-08-06`, with no invalid responses or transport retries. It used 24 fresh paired numerical cases from the same shipping task family as the original experiment. Each case had one saved initial hypothesis and two independent selection continuations.

| Condition | Informative choices | Valid selections | Answer-only responses |
| --- | ---: | ---: | ---: |
| Rules only | 4/24 | 24/24 | 24/24 |
| Rules plus correct outcome table | 24/24 | 24/24 | 24/24 |

The primary paired difference was +83.3 percentage points, with 20 gains and no losses. The descriptive 95% paired bootstrap interval was [66.7, 95.8] points. These are 24 paired cases, not 48 independent selection observations. All cases share one task family, and generalization is untested.

Initial hypotheses favored the price rule in all 24 cases, while the H1/H2 labels were balanced 12/12. Supplied predictions yielded 12/12 correct selections in each diagnostic direction; rules only yielded 3/12 for high-price/heavy orders and 1/12 for low-price/light orders. These direction breakdowns are descriptive.

## Interpretation and decision

The table supplied each candidate's fee under each hypothesis; it did not explicitly identify the diagnostic test. Both conditions requested only a chosen test and received the same saved initial response. Correct supplied predictions were sufficient for perfect selection on this sample.

The intervention changes presentation, redundancy, and the need to calculate fees. It does not uniquely identify an internal bottleneck or establish that the initial hypothesis caused selection errors. The experiment does not execute the chosen tests or measure subsequent learning. Its 4/24 rules-only baseline should not be pooled with the original experiment's 7/24 direct baseline: they use different frozen cases and plans.

The prespecified decision was `supplied_predictions_near_ceiling_stop_shipping_task`. Further expansion of this shipping task is not planned. No claim of a new mechanism or publication-level novelty follows from the result.

## Verification

For this repository update, the original uploaded archive was checked against the frozen source and plan. All 72 raw provider responses were reparsed, and the saved requests, response text, completion status, model identity, and parsed selections matched. The six responses from the initial access check were unchanged in the full export.

All candidate fees were independently recomputed from the price and weight rules. The resulting diagnostic tests matched the saved oracle. Reanalysis reproduced the archived analysis exactly. No new model calls were made and no original run files were changed.

- [Original archive](../results/predictions-001.zip), SHA-256: `60f1c5832476396bb56ccffed4c58f7db5bb3391d050e278da6e76727cdfa4d9`
- Plan hash: `7820a170ba8d06dc2938a15f1cdbdbf681effbd06a8bc6c3abecbcbd2930cf51`
- Source hash: `7f6b1bb9f14aacb346ee9589c7280f39e3129a56ccb542996f2d16acfb780429`
- [Machine-readable analysis](../results/predictions-001-analysis.json)
- [Frozen protocol](PREDICTIONS_PROTOCOL.md)

To reproduce the analysis without API calls, run from the repository root using a fresh extraction directory:

```bash
python3 -m zipfile -e results/predictions-001.zip runs/reproduce-predictions
python3 -m evidence_selection_predictions analyze \
  --output runs/reproduce-predictions/predictions-001
```

Only the extracted working copy is analyzed. The original archive remains unchanged.
