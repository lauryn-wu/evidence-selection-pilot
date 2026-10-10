# Supplied predictions diagnostic: protocol v1

Protocol: evidence-selection-supplied-predictions-v1

Written 2026-10-10 after auditing shipping-001 and before collecting this follow-up.
This is a prospectively specified exploratory diagnostic, not a registered
confirmatory study. The original pilot and its strict analysis remain intact.

## Question

Does providing a correct table of conditional test outcomes improve selection of
an informative test, compared with giving the rules and test inputs alone?

In shipping-001, the direct, facts, deliberate, and explain conditions selected
the informative test on 7, 8, 20, and 11 of 24 cases. The separately audited fee
predictions were fully correct on 23/24 cases. That result did not support the
proposed reasoning-harm effect. Separate-task competence does not show that the
model represented the predictions correctly during a selection response.

This follow-up tests the effect of making the correct predictions available at
selection time. It is a bounded diagnostic, not a new claim of confirmation bias,
an internal mechanism, or a novel research contribution.

## Matched conditions

Both conditions receive the original rules, two ambiguous observations, three
test inputs, and the same exact saved tentative hypothesis. Both receive the
original direct-selection instruction, including the same objective and demand
for only a final CHOICE line.

| Condition | Extra information |
| --- | --- |
| rules_only | None; original direct-selection prompt on fresh cases. |
| predictions_supplied | A table giving each test's predicted fee under H1 and H2. |

The sole prompt difference is insertion of this table after the test inputs and
before the common objective. Example of its form (illustrative values):

~~~text
Predicted shipping fees calculated from the stated rules:
Test | Fee if H1 | Fee if H2
T1 | $5 | $5
T2 | $0 | $5
T3 | $0 | $0
~~~

The program computes the table exactly. Rows follow the same T1/T2/T3 order as
the candidate inputs; columns are H1/H2. It does not label an informative test,
provide information-gain values, recommend an answer, or state which rule is true.
The table is supplied by the experiment, not generated in a preceding model call.

The difference includes visibility, presentation, redundancy, and prompt length.
A benefit cannot uniquely distinguish arithmetic, attention, working memory,
representation, or decision-process explanations. Residual errors do not establish
that the model read or trusted the table. Answer-only output does not mean that
the model performed no internal reasoning.

## Cases and collection

Use 24 fresh numerical cases with seed 202610102. The default cases are verified
not to duplicate any complete original shipping-001 case. This is the same shipping
task family, not a new domain. Both deterministic rules remain exhaustive and
equally likely, and both observed orders fit both rules.

The full crossing is two hypothesis-label mappings, two diagnostic directions
(high price/heavy or low price/light), and six candidate permutations. Each
diagnostic test position occurs eight times. The two condition call orders occur
once each within every label-mapping x diagnostic-direction x diagnostic-position
stratum, giving twelve occurrences of each order. Directions are interleaved in
the frozen schedule so the first two cases cover both directions.

For each case:

1. Request one tentative H1/H2 guess before showing candidate tests.
2. Fork two independent continuations from the exact saved initial response.
3. Insert the table only for predictions_supplied; request an answer-only choice
   in both conditions.

The initial hypothesis is not artificially balanced or forced. Report both its
H1/H2 label and price/weight meaning; in the original pilot all initial guesses
favored price. A fixed observable prefix does not fix a measured latent belief.

No separate competence call is needed for this two-condition diagnostic. No test
is executed, no hidden true rule is sampled, and no final identification score is
claimed. Exactly one test distinguishes the two rules; the others yield identical
outcomes. Expected information gain is therefore one or zero bits.

Default model: gpt-4o-2024-08-06. Temperature: 0.0. Completion cap: 1024 tokens in
every call, matching the original experiment. Provider determinism is not assumed.
There are **72 planned calls**, with **84 maximum attempts** and at most two
transport attempts per job. These limits do not set a dollar spending cap.

## Validity, resumability, and audit

- Initial output must be exactly HYPOTHESIS: H1 or HYPOTHESIS: H2 after trimming.
  An invalid initial answer blocks both dependent branches; no replacement case.
- Choices use the original parser: the final nonempty line must be CHOICE: T1,
  CHOICE: T2, or CHOICE: T3, with no earlier CHOICE marker. Retain extra text and
  record its presence separately; do not retry a valid choice for compliance.
- Refusals, truncation, tool calls, unexpected models, and unparseable choices
  are invalid and retained. Wrong or malformed returned answers are never retried.
- Retry only bounded transport failures. Interrupted or uncertain requests count
  against the cap and require explicit --retry-uncertain before another attempt.
- Preserve requests, raw responses, parsing, model, timestamps, token usage, plan
  hash, and a source fingerprint covering this package and its shared dependencies.
- Changed prompts/config/source or a different mock/live mode cannot resume a run.
  The original evidence_selection package is not changed by this implementation.

Inspect the first six calls (two complete cases), then resume the same frozen
run. Do not change wording or replace an unfavorable response after inspection.

## Analysis and planning screen

Primary contrast: predictions_supplied minus rules_only in diagnostic selection.
Report all-planned and valid-only rates, invalid/missing counts, paired gains and
losses, and a descriptive case bootstrap interval (10,000 draws; seed 271828).
The exact McNemar p-value is exploratory. Constant paired differences receive no
misleading zero-width interval. The experimental unit is the case, not a response.

The primary paired comparison uses cases with valid choices in both conditions.
Also report an answer-only subset, initial semantic-hypothesis counts, and
diagnostic-direction slices as secondary descriptive checks. Missing/invalid
answers are not observed zero-bit actions. All data remain in the audit.

Apply this planning screen in order:

1. Simulated data: no scientific conclusion.
2. Incomplete collection or invalid output: review measurement; do not pass a gate.
3. Either condition has fewer than 22/24 answers without extra text: review
   answer-only compliance before interpretation.
4. Supplied predictions yield at least 23/24 informative choices: stop expanding
   this shipping task. Record separately whether the baseline is also at ceiling.
   A table benefit localizes the issue only at the level of this intervention.
5. Supplied predictions yield at most 20/24 informative choices: manually audit
   every residual error, its supplied table, and paired baseline before deciding
   whether any fresh replication is justified. This does not authorize expansion.
6. Supplied predictions yield 21 or 22/24: report the small residual and do not
   expand automatically.

Thresholds are planning heuristics, not significance tests or a publication bar.
They scale with a configured multiple of 24, but changing the default sample size
constitutes a new experiment. Do not pool this run with the original four-arm pilot.

## Run commands

From the repository root, with OPENAI_API_KEY exported in the same terminal:

~~~bash
python3 -m unittest discover -s tests -v
python3 -m evidence_selection_predictions prepare --config configs/predictions.json --output runs/predictions-001
caffeinate -i python3 -m evidence_selection_predictions run --output runs/predictions-001 --max-calls 6
python3 -m evidence_selection_predictions export --output runs/predictions-001 --destination runs/predictions-check-001.zip
~~~

After reviewing the six-call check, resume and export using a new ZIP filename:

~~~bash
caffeinate -i python3 -m evidence_selection_predictions run --output runs/predictions-001
python3 -m evidence_selection_predictions export --output runs/predictions-001 --destination runs/predictions-001.zip
~~~

For a zero-API software demonstration use a different output directory:

~~~bash
python3 -m evidence_selection_predictions run --config configs/predictions.json --output runs/predictions-mock-001 --mock
~~~

To reproduce the original run's separate content audit without changing it:

~~~bash
python3 -m evidence_selection_predictions audit-original --input runs/shipping-001 --output runs/shipping-content-audit-001
~~~

The input may also be the exported shipping-001.zip. Audit output must be a new,
separate directory. The original strict flags and report are retained.
