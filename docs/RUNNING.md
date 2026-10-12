# Running the evidence-selection experiments

Both archived experiments are complete. These instructions are retained for reproduction; further expansion of the shipping task is not planned. See the [README](../README.md) for results and offline reanalysis. Run commands from the repository root. Use a fresh, clearly named directory for a new experiment and preserve existing run records.

## Supplied-predictions experiment

Start with the six-call check (two cases), using your terminal's OPENAI_API_KEY:

~~~bash
python3 -m unittest discover -s tests -v
python3 -m evidence_selection_predictions prepare --config configs/predictions.json --output runs/predictions-001
caffeinate -i python3 -m evidence_selection_predictions run --output runs/predictions-001 --max-calls 6
python3 -m evidence_selection_predictions export --output runs/predictions-001 --destination runs/predictions-check-001.zip
~~~

After checking the responses, resume without --max-calls and export to a different
filename. See the [follow-up protocol and full commands](PREDICTIONS_PROTOCOL.md).
Neither prepare nor export makes model calls. Mock and live runs use separate
directories. Do not edit source or prompts during collection.

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

Keep the resulting ZIP as the complete run record. It contains raw responses and exact requests,
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

