# Experiment archives

These are the original run exports, containing requests, raw responses, parsed
outputs, plans, prompts, configuration, runtime metadata, analyses, and reports.
The automatic decisions have been preserved.

| Archive | Experiment | Completed calls | Outcome |
| --- | --- | ---: | --- |
| [shipping-001.zip](shipping-001.zip) | Four selection instructions | 144/144 returned | Deliberation helped; original competence parser rejected 24 responses |
| [predictions-001.zip](predictions-001.zip) | Rules only versus supplied predictions | 72/72 valid | 4/24 versus 24/24 informative selections; stop shipping-task expansion |

The shipping report's 0/24 competence score comes from strict format checks.
The [content audit](../docs/SHIPPING_001_AUDIT.md) found 23/24 cases with all six
fees correct after applying a uniform parsing rule. It leaves the original
responses and flags unchanged; the scores are in
[shipping-001-content-audit.json](shipping-001-content-audit.json).

The [follow-up audit](../docs/PREDICTIONS_001_AUDIT.md) explains the supplied-predictions result and its limits. [predictions-001-analysis.json](predictions-001-analysis.json) contains the same analysis as the original follow-up archive, for inspection without extraction.

## Checksums

| File | SHA-256 |
| --- | --- |
| `shipping-001.zip` | `6be41a130b998b73352708cec45d475db5543c9787e7124a38dc8c308852d48d` |
| `predictions-001.zip` | `60f1c5832476396bb56ccffed4c58f7db5bb3391d050e278da6e76727cdfa4d9` |

The [README](../README.md#reproduce-the-saved-analyses-offline) has commands to
reanalyze both archives without model calls.
