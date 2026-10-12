# Evidence selection in language models

Does the way a language model reasons before choosing a test change how informative that test is?

**Status: two small experiments completed; the shipping task is closed.** In the first experiment, comparing possible test outcomes improved selection relative to summarizing the facts. In the follow-up, supplying the correct outcomes in a table increased informative choices from **4/24 to 24/24**. The proposed reasoning-harm effect did not appear.

This repository contains the experiment code, frozen protocols, exact scoring rules, raw model responses, and offline analyses. Both experiments used `gpt-4o-2024-08-06` at temperature 0. Each used 24 paired numerical variants of one task family.

## Task

A shipping calculator follows one of two rules: free shipping depends on either order price or order weight. Two observed orders fit both rules. The model states a tentative hypothesis, then chooses one of three new orders to test. Exactly one test distinguishes the rules; the other two produce the same fee under both rules.

Each condition receives the same saved initial response for that case. The score is whether the chosen test distinguishes the rules. The experiments do not execute the selected test or measure later belief revision. See the [worked example](docs/EXAMPLE.md).

## Experiment 1: instructions before selection

All 144 planned calls returned: 24 initial hypotheses, 96 selections, and 24 separate checks of predicted shipping fees. All 96 selections were parseable.

| Instruction | Informative choices | Rate |
| --- | ---: | ---: |
| Choose directly | 7/24 | 29.2% |
| Summarize the facts | 8/24 | 33.3% |
| Compare hypotheses and possible test outcomes | 20/24 | 83.3% |
| Explain the initial hypothesis | 11/24 | 45.8% |

The primary comparison, deliberation minus factual summary, was **+50 percentage points**: 13 paired gains and one loss. Its descriptive 95% paired bootstrap interval was [25.0, 70.8] points. Explaining the initial hypothesis performed worse than prospective comparison, but numerically better than the direct and factual-summary conditions. These results do not establish harm from explanation or reasoning.

**Scoring audit:** the original parser rejected all 24 competence responses because of formatting. A separately declared, uniform content audit found 23/24 cases with all six fees correct, or 143/144 fee predictions. Original responses, validity flags, and the `measurement_issue_review_invalid_outputs` decision remain unchanged. The content audit does not retroactively pass the original screen. See the [full audit](docs/SHIPPING_001_AUDIT.md) and [machine-readable content scores](results/shipping-001-content-audit.json).

## Experiment 2: supplied predictions

The follow-up used 24 fresh paired cases and 72 calls. Both conditions requested only the chosen test. One received the rules alone; the other also received a correct table of every candidate's outcome under each rule. The table did not label the informative test. All 72 responses were valid.

| Condition | Informative choices | Rate |
| --- | ---: | ---: |
| Rules only | 4/24 | 16.7% |
| Rules plus supplied predictions | 24/24 | 100% |

The paired difference was **+83.3 percentage points**, with 20 gains and no losses; the descriptive 95% paired bootstrap interval was [66.7, 95.8] points. The prespecified decision was `supplied_predictions_near_ceiling_stop_shipping_task`.

Correct supplied predictions were sufficient for perfect selection on these cases. Because the table also changes presentation and makes the comparison easier, this does not identify a unique internal bottleneck. See the [follow-up audit](docs/PREDICTIONS_001_AUDIT.md), [analysis](results/predictions-001-analysis.json), and [protocol](docs/PREDICTIONS_PROTOCOL.md).

## Scope and stopping decision

- These are two small experiments on one model and one task family. The paired cases are the units of analysis; individual responses are not independent replications.
- The initial guess favored the price rule in all 24 cases of each experiment, despite balanced hypothesis labels.
- Some factual summaries included test-selection reasoning, and requested explanation lengths did not produce equal realized lengths. The first experiment does not isolate an internal reasoning mechanism.
- Supplying outcomes combines precomputation, visibility, redundancy, and presentation. Answer-only output does not establish an absence of internal reasoning.

The original harmful-reasoning hypothesis was unsupported, and the follow-up reached ceiling with supplied predictions. Further expansion of this shipping task is not planned. The results are a bounded behavioral finding, with no claim of broad generalization or a new mechanism.

## Reproduce the saved analyses offline

Requires Python 3.10+ on macOS or Linux, with no third-party runtime dependencies. Run from the repository root. These commands make no model calls:

```bash
python3 -m evidence_selection_predictions audit-original \
  --input results/shipping-001.zip \
  --output runs/reproduce-shipping-audit

python3 -m zipfile -e results/predictions-001.zip runs/reproduce-predictions
python3 -m evidence_selection_predictions analyze \
  --output runs/reproduce-predictions/predictions-001
```

Use fresh output directories so existing analyses remain intact. Both ZIP files contain the original prompts, requests, responses, plans, and reports. Archive checksums and contents are listed in [results/README.md](results/README.md).

## Documentation

- [Original protocol](docs/PROTOCOL.md) and [supplied-predictions protocol](docs/PREDICTIONS_PROTOCOL.md)
- [Literature context](docs/LITERATURE.md)
- [Run instructions, offline simulations, and request handling](docs/RUNNING.md)

Live API execution is optional and incurs cost. It is not required to inspect or reproduce the archived analyses.
