# Evidence selection pilot

Does the way a language model reasons before choosing a test change how informative
that test is?

This is a small, standalone behavioral pilot. It compares four response
instructions after the model has stated the same tentative hypothesis. It includes
an exact scoring oracle, a separate rule-prediction check, frozen prompts,
resumable requests, raw responses, and paired analysis.

**Status: implementation and offline validation only. No empirical model results
are included.** The project tests a candidate effect; it does not assume that
explanation harms exploration.

## The experiment

A shipping calculator follows exactly one of two possible rules:

- Free shipping depends on order price.
- Free shipping depends on order weight.

Two initial observations fit both rules. The model states a tentative hypothesis
before seeing the candidate tests. Four independent continuations use that exact
same saved response:

| Condition | Instruction before selecting a test |
| --- | --- |
| direct | Select a test with no written explanation. |
| facts | Summarize the supplied information in 60-100 words, then select. |
| deliberate | Reason about the competing hypotheses and what the tests reveal in 60-100 words, then select. |
| explain | Explain the reasoning behind the tentative hypothesis in 60-100 words, allowing uncertainty and revision, then select. |

All conditions receive the same objective: choose the test most useful for
distinguishing the rules. One test perfectly distinguishes them; the other two
give the same outcome under either rule. The primary outcome is the fraction of
diagnostic tests selected. Under the stated equal prior, a diagnostic test gives
one bit of information and either other test gives zero.

A separate, fresh conversation asks the model to predict each candidate's outcome
under each rule. This checks whether it can calculate the consequences of the
tests without feeding that calculation into any selection condition.

The default pilot has **24 paired cases and 144 planned API calls**:
24 initial hypotheses, 96 selections, and 24 competence checks. The hard limit is
168 attempts, including transport retries and uncertain in-flight requests.
The cases vary thresholds, fees, numerical inputs, hypothesis labels, candidate
order, and condition call order. They are variants of one task family.

See [the worked example](docs/EXAMPLE.md), [protocol](docs/PROTOCOL.md), and
[literature context](docs/LITERATURE.md).

## Run on your Mac

Requires Python 3.10 or newer. There are no runtime dependencies to install.
Run the commands from this project folder. Linux is also supported; the process
lock uses fcntl, so Windows requires WSL.

First, verify the code and freeze the experiment. Neither command contacts a model.

~~~bash
python3 -m unittest discover -s tests -v
python3 -m evidence_selection prepare --config configs/pilot.json --output runs/shipping-001
~~~

Inspect runs/shipping-001/prompts.md if you want to see every prepared prompt.
The saved initial answer is inserted only after its real response arrives.

The live runner uses OPENAI_API_KEY from your terminal environment. It does not
read a .env file automatically. If your key is already exported, no setup change
is needed. The default model is gpt-4o-2024-08-06.

Start with six calls: the initial hypothesis, all four conditions, and the isolated
competence check for one case.

~~~bash
caffeinate -i python3 -m evidence_selection run --output runs/shipping-001 --max-calls 6
~~~

After inspecting those responses, resume the same run:

~~~bash
caffeinate -i python3 -m evidence_selection run --output runs/shipping-001
~~~

Completed and invalid responses are never requested again. The smoke check is part
of the frozen 24-case pilot, not a separate experiment. On Linux, omit caffeinate -i.
Do not change prompts, code, or config midway through a run.

Analyze or package the results:

~~~bash
python3 -m evidence_selection analyze --output runs/shipping-001
python3 -m evidence_selection export --output runs/shipping-001 --destination runs/shipping-001.zip
~~~

Upload the resulting ZIP for review. It contains raw responses and exact requests,
not just a summary.

## Offline demonstration

This uses a deterministic oracle simulator and makes **zero API calls**:

~~~bash
python3 -m evidence_selection run --config configs/pilot.json --output runs/mock-001 --mock
~~~

Mock and live responses cannot share a run directory. Mock reports are prominently
labeled and never pass a scientific decision gate.

## What to read after a run

- report.md: readable results and the pilot decision.
- analysis.json: condition counts, missingness, paired comparisons, uncertainty
  summaries, competence performance, and returned-response token usage.
- audit.csv: one row per case and condition, including the full selection response.
- attempts/*.json: every request, raw response, parsing result, timestamps, model,
  token usage, and transport failure.
- plan.json and prompts.md: the frozen cases, schedule, oracle, and instructions.

The main contrast is deliberate minus facts. Deliberate minus direct is a
secondary check; explain minus facts and explain minus deliberate help distinguish
justification-specific behavior. Negative differences mean less informative
selection in the first condition.

Decision thresholds are specified in the protocol. They are conservative planning
rules for whether to invest in a fresh replication, not significance or novelty
claims. If performance is at ceiling, stop this task rather than repeatedly
changing wording until an effect appears.

## Interrupted or failed requests

Ordinary HTTP rate limits/server errors receive bounded retries. Refusals,
truncated responses, malformed outputs, and incorrect selections are retained.
They are never retried to obtain a better answer.

An interruption or network timeout may leave an uncertain attempt that was
already processed by the provider. It counts against the attempt budget. Review
that attempt before explicitly allowing another request:

~~~bash
caffeinate -i python3 -m evidence_selection run --output runs/shipping-001 --retry-uncertain
~~~

Invalid initial hypotheses block that case's four selection branches, while its
competence check can still run. The report shows the missing branches. Investigate
the format failure; do not silently replace that case or delete an attempt.

The attempt cap limits request count, not dollar spending. Token totals include
returned responses only; a timed-out request may still have been billed.

## Create the separate GitHub repository

The download is a complete source project. Create an **empty private repository**
named evidence-selection-pilot on GitHub, without an automatically generated
README, then run these commands from this folder:

~~~bash
git init -b main
git add .
git commit -m "Initialize evidence selection pilot"
git remote add origin https://github.com/lauryn-wu/evidence-selection-pilot.git
git push -u origin main
~~~

Run outputs and API-key files are excluded by .gitignore. The project contains
no dependency on another research repository.
