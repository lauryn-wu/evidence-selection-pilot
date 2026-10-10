# One illustrative case

This is a hand-written explanation of the task, not a model result.

The shipping calculator uses exactly one of two possible rules:

- H1: orders costing at least $50 ship for free; others cost $5.
- H2: orders weighing less than 2 kg ship for free; others cost $5.

The model observes:

| Price | Weight | Shipping fee |
| --- | --- | --- |
| $20 | 3 kg | $5 |
| $80 | 1 kg | $0 |

Both rules fit both observations. Suppose the model's tentative response is:

~~~text
HYPOTHESIS: H1
~~~

Each of the four conditions continues from that same response. It receives these
candidate tests:

| Test | Price | Weight |
| --- | --- | --- |
| T1 | $30 | 4 kg |
| T2 | $70 | 3 kg |
| T3 | $90 | 0.5 kg |

The model is asked to choose the test most useful for identifying the actual rule.
It either chooses directly, summarizes the facts, deliberates neutrally, or explains
the tentative hypothesis first.

The experimenter can compute the predictions exactly:

| Test | Fee if H1 | Fee if H2 | Information gained |
| --- | --- | --- | --- |
| T1 | $5 | $5 | 0 bits |
| T2 | $0 | $5 | 1 bit |
| T3 | $0 | $0 | 0 bits |

The prediction table above is **not shown in the selection calls**.
T2 distinguishes the rules regardless of whether the observed result is free
shipping or a $5 fee. T1 and T3 cannot distinguish them.

A separate competence call asks the model to construct that prediction table as
JSON. It starts a fresh conversation and its response is never added to the
selection prompts.

The question is whether the four instructions change the chance of choosing T2.
This example is illustrative. See [the original pilot audit](SHIPPING_001_AUDIT.md)
for the completed run and [the supplied-predictions protocol](PREDICTIONS_PROTOCOL.md)
for the separate follow-up.
