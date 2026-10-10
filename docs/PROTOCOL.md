# Shipping evidence selection: pilot protocol v1

Protocol ID: evidence-selection-shipping-v1

Written: 2026-10-10, before any live calls for this implementation.

This is a prospectively specified exploratory screen, not a registered
confirmatory study. The code freezes its cases and prompts before collection.

## Question and scope

Does a prompted processing style change which test a language model selects,
holding its observable history and stated tentative hypothesis fixed?

The primary directional hypothesis is that neutral deliberation can reduce
diagnostic selection relative to a factual summary. Direct selection is an
additional control. Explaining a tentative hypothesis tests a related but narrower
justification effect. Beneficial effects and null results are reported as observed.

The intervention bundles the instruction and the text it elicits. A difference
does not isolate the causal influence of an individual rationale sentence,
establish a latent belief, or show that computation itself is harmful. Fixed API
prefixes do not guarantee identical latent confidence. No mechanistic claim is
licensed by this pilot.

## Environment and exact oracle

There are exactly two exhaustive deterministic rules, with equal prior
probability. Both initial examples are consistent with both rules. Consequently,
neither initial hypothesis is more justified by the supplied observations.
The request for a working hypothesis explicitly permits a tentative tie break.
It is a controlled commitment, not a measured strong belief.

The model is not shown test candidates until after its initial response.
There are three equal-cost tests:

1. A low-price heavy order: both rules charge the fee.
2. A high-price light order: both rules give free shipping.
3. A conflicting order: the rules predict different fees.

Test order is permuted. The conflicting order alternates between high-price/heavy
and low-price/light. Exactly one candidate always identifies the rule completely,
regardless of the test outcome. The other two cannot distinguish the rules.

Thus the exact expected information gains are 1, 0, and 0 bits, under the supplied
prior and deterministic observation model. Candidate names and free/paid outcomes
are counterbalanced. Scoring does not label a test bad merely because it can
confirm a hypothesis.

This stage measures a choice before receiving any new result. No hidden rule needs
to be sampled, no test is actually executed, and there is no final-answer accuracy
outcome. A later experiment supplying identical diagnostic feedback would address
evidence interpretation; it is not part of this pilot.

## Cases and counterbalancing

Default seed: 202610101. Twenty-four cases form the full crossing of:

- Two mappings of H1/H2 to price/weight rules.
- Two directions of the conflicting test.
- Six candidate permutations.

Thresholds, fees, and numerical inputs vary. No candidate duplicates an observed
order. All 24 permutations of the four condition call orders occur once, assigned
independently of the case factors. Each condition appears six times in each call
position, and each diagnostic-test position occurs eight times.

These are 24 paired numerical cases from one template, not 24 distinct domains
or a broad generalization sample. A later fresh-seed replication would test
numerical robustness; a second task family would be needed for transfer.

## Collection

For each case:

1. Ask for exactly one initial line, HYPOTHESIS: H1 or HYPOTHESIS: H2.
2. Fork four separate calls from that exact saved assistant response and identical
   preceding messages. Each receives the same candidate tests and selection
   objective, plus its assigned direct/facts/deliberate/explain instruction.
3. Make one independent competence call with the rules, initial observations,
   and candidate inputs. Ask for all six fees: three tests under two hypotheses.
   It contains no initial hypothesis or earlier generated text.

All selection arms share the same temperature and 1,024-token completion cap.
The three text-generating arms request 60-100 words. Equal requested length and
completion caps do not guarantee equal realized output length or internal compute.
Record actual words and provider-reported token usage. No constrained-output API
schema suppresses text in the selection comparison.

Default model: gpt-4o-2024-08-06; temperature: 0.0. This minimizes sampling
variation but does not guarantee deterministic provider behavior.

There are 144 planned calls. Maximum total attempts: 168. Maximum attempts per
job: two. Only transport failures/uncertain requests can consume retries.
The model identity, raw requests/responses, timestamps, usage, source fingerprint,
and frozen plan hash are recorded.

## Validity and exclusions

- Initial response: the entire trimmed output must be exactly one valid hypothesis
  line. Otherwise retain it and block the four dependent selection calls.
- Selection response: the last nonempty line must be exactly CHOICE: T1, T2, or
  T3, with no earlier CHOICE marker. Preserve a valid choice even if the direct
  arm writes extra text or a text arm misses its requested word range.
- Competence response: strict JSON with exactly T1/T2/T3, each containing numeric
  H1/H2 fees. Reject duplicate keys, booleans, nonfinite numbers, and extra fields.
- Truncation, refusal, tool calls, and an unexpected returned model are invalid
  regardless of whether a parseable answer appears.
- Returned invalid answers are never retried. No cases are replaced post hoc.

Automatic prefix/word checks measure format compliance. They do not establish
that a prefix contains substantive reasoning, a faithful rationale, or a genuinely
descriptive summary. Manually audit the raw text before substantive interpretation.

## Outcomes and analysis

The primary outcome is diagnostic-test selection. Report:

- Diagnostic choices divided by all 24 planned cases, with invalid and missing
  counts shown separately.
- Diagnostic choices among valid returned choices.
- Mean oracle information gain among valid choices; in this task it numerically
  equals diagnostic-selection rate.
- Text presence, word counts, completion status, and token usage.
- Competence: cases with all six fees correct, plus descriptive per-cell accuracy.

An invalid or missing action is not observed to have zero information gain.
The all-planned rate instead measures successful production of a diagnostic choice.

Primary contrast: deliberate minus facts.
Secondary contrasts: deliberate minus direct; explain minus facts; explain minus
deliberate. Use case-level pairing and report gains, losses, and the net difference.
Do not treat four responses or six predictions within a case as independent cases.

Report descriptive percentile intervals from 10,000 case bootstrap draws, seeded
at 271828, and exploratory unadjusted exact McNemar p-values. These are not a
multiple-comparison-controlled discovery claim. Constant paired differences
produce no bootstrap interval; a degenerate interval must not imply equivalence.
Partial/invalid runs cannot pass the investment screen.

Also report paired differences restricted to cases whose separate competence
call predicts all six outcomes correctly. This is secondary and does not prove
the model held the relevant knowledge during its selection call.

## Prespecified investment screen

These thresholds prioritize a large, interpretable signal in a tiny pilot. They
are planning heuristics, not statistical proof and not a conference-acceptance bar.
Read them in this order:

1. Mock run: software demonstration only; never draw a research conclusion.
2. Incomplete or invalid collection: review the measurement problem first.
3. Format check: direct has no prefix on at least 22/24 cases; each text arm
   meets the 60-100-word request on at least 20/24. Otherwise inspect compliance.
4. Competence: at least 22/24 cases have all six predicted fees correct.
   Otherwise the proposed competence-versus-choice distinction is not established.
5. Ceiling: if every arm selects the diagnostic test on at least 23/24 cases,
   stop this task. This does not prove a general absence of the effect.
6. Controls: direct and facts must each reach at least 22/24 diagnostic choices.
   Weaker controls require inspection before expansion.
7. Candidate neutral-deliberation harm: deliberate has at least four fewer
   diagnostic choices than each of direct and facts. Audit these cases; if the
   contrast survives review, replicate with a fresh frozen seed and another model.
8. If explain has at least four fewer diagnostic choices than facts but the
   neutral-deliberation criterion fails, treat it as justification-specific.
   Deprioritize the broad claim that ordinary reasoning harms information seeking.
9. Otherwise, there is no prespecified large harm signal. Do not launch a larger
   battery merely to search for a favorable wording.

The thresholds scale proportionally for a future multiple-of-24 configuration.
The default screen is fixed at 24; any expansion is a new experiment with a
separate run directory and stated rationale.

## Audit and later work

Review the actual texts for whether each instruction elicited its intended
behavior. Check position/label balance, competence on harmed cases, realized
length, and any invented assumptions. Treat these as descriptive diagnostics.

A credible positive pilot would motivate controlled text interventions, matched
diagnostic feedback, and transfer to a practical test-selection environment.
Those are follow-up studies, not findings of this implementation. A single task,
single model, and prompt comparison is insufficient to establish a general
mechanism or a strong publication contribution.
