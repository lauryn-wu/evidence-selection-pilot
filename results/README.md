# Completed experiment records

Both ZIP files are unchanged copies of the original uploaded run exports. They contain exact requests, raw provider responses, parsed outputs, frozen plans and prompts, configuration, runtime metadata, analyses, and reports. The original automatic decisions remain intact.

| Archive | Experiment | Completed calls | Outcome |
| --- | --- | ---: | --- |
| [shipping-001.zip](shipping-001.zip) | Four selection instructions | 144/144 returned | Deliberation helped; original competence parser rejected 24 responses |
| [predictions-001.zip](predictions-001.zip) | Rules only versus supplied predictions | 72/72 valid | 4/24 versus 24/24 informative selections; stop shipping-task expansion |

The original shipping report's 0/24 competence score is a strict-format score. Read it with the [separate content audit](../docs/SHIPPING_001_AUDIT.md), which found 23/24 cases with all six fees correct without changing original responses or flags. The corresponding [content-audit JSON](shipping-001-content-audit.json) was already part of this repository.

The [follow-up audit](../docs/PREDICTIONS_001_AUDIT.md) explains the supplied-predictions result and its limits. [predictions-001-analysis.json](predictions-001-analysis.json) contains the same analysis as the original follow-up archive, for inspection without extraction.

## Archive identity

| File | SHA-256 |
| --- | --- |
| `shipping-001.zip` | `6be41a130b998b73352708cec45d475db5543c9787e7124a38dc8c308852d48d` |
| `predictions-001.zip` | `60f1c5832476396bb56ccffed4c58f7db5bb3391d050e278da6e76727cdfa4d9` |

See the [README](../README.md#reproduce-the-saved-analyses-offline) for offline reproduction commands. No new model run is needed to inspect or reanalyze these records.
