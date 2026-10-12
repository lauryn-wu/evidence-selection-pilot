# Evidence selection in language models

This pilot studies how a language model chooses between tests of two competing
hypotheses. Comparing possible outcomes improved selection relative to
summarizing the facts. A follow-up supplied those outcomes in a table and
increased informative choices from 4/24 to 24/24. The original hypothesis that
reasoning would hurt selection was unsupported.

Both experiments used `gpt-4o-2024-08-06` at temperature 0, with 24 paired numerical
variants of a shipping task in each. The code, protocols, scoring rules, raw
responses, and analyses are included here. No further expansion of this task is
planned.

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

Comparing outcomes improved selection by 50 percentage points over summarizing
facts: 13 paired gains and one loss, with a descriptive 95% paired bootstrap
interval of [25.0, 70.8] points. Explaining the initial hypothesis did worse than
comparing outcomes, but numerically better than choosing directly or summarizing
facts.

The original parser rejected all 24 fee-prediction responses because of
formatting. A separately declared content audit applied the same parsing rule to
all responses and found 23/24 cases with all six fees correct, or 143/144 fee
predictions. The original validity flags and
`measurement_issue_review_invalid_outputs` decision are preserved; the audit
does not turn that decision into a pass. See the
[audit](docs/SHIPPING_001_AUDIT.md) and
[content scores](results/shipping-001-content-audit.json).

## Experiment 2: supplied predictions

The follow-up used 24 fresh paired cases and 72 calls. Both conditions requested only the chosen test. One received the rules alone; the other also received a correct table of every candidate's outcome under each rule. The table did not label the informative test. All 72 responses were valid.

| Condition | Informative choices | Rate |
| --- | ---: | ---: |
| Rules only | 4/24 | 16.7% |
| Rules plus supplied predictions | 24/24 | 100% |

The paired difference was 83.3 percentage points, with 20 gains and no losses
(descriptive 95% paired bootstrap interval: [66.7, 95.8] points). This met the
planned stopping criterion, `supplied_predictions_near_ceiling_stop_shipping_task`.

See the [follow-up audit](docs/PREDICTIONS_001_AUDIT.md),
[analysis](results/predictions-001-analysis.json), and
[protocol](docs/PREDICTIONS_PROTOCOL.md).

## Limitations

These experiments cover one model and one task family. Cases are paired across
conditions; individual responses are not independent replications. The model's
initial guess favored the price rule in all 24 cases of each experiment, despite
balanced hypothesis labels.

The first comparison does not cleanly separate kinds of reasoning: some factual
summaries included test-selection reasoning, and response lengths differed
despite the requested limits. In the follow-up, supplying a table both
precomputes the outcomes and changes how they are presented. It was enough for
perfect selection here, but that does not identify which internal step caused
the rules-only errors. Asking for just the answer also leaves internal reasoning
unobserved.

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

Live runs incur API costs; the saved analyses can be reproduced offline.
