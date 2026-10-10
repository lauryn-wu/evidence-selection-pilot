# Literature context and the candidate contribution

Reviewed 2026-10-10. This is a focused motivation, not an exhaustive review or a
claim that the proposed effect is novel.

## Closest work

- Wan, Jia, and Li. **Unveiling Confirmation Bias in Chain-of-Thought Reasoning.**
  Findings of ACL 2025.
  [Paper](https://aclanthology.org/2025.findings-acl.195/).
  Analyzes associations between initial answer preferences, generated rationales,
  and subsequent answers, using direct-answer probabilities as proxies for belief
  strength. Reinforcement of an initial answer during reasoning is therefore
  established related work. This pilot instead measures which new evidence a model
  elects to obtain.

- Jhaveri, GX-Chen, Sucholutsky, and Choi. **Failing to Falsify: Evaluating and
  Mitigating Confirmation Bias in Language Models.**
  April 2026 preprint; conference status not established here.
  [Paper](https://arxiv.org/abs/2604.02485).
  Studies interactive rule discovery across 11 LLMs, tests compatible with their
  current hypotheses, and interventions improving discovery. This is substantial
  overlap: confirmation-seeking test selection and counterexample prompting are
  not new contributions. The present screen holds the stated starting hypothesis
  fixed across processing instructions and scores exact diagnostic value.

- Xiong and colleagues. **Thinking Under Uncertainty: Evidence Use and
  Information-Seeking in Language Models.**
  July 2026 preprint; conference status not established here.
  [Paper](https://arxiv.org/abs/2607.26845).
  Separates using current evidence from acquiring information in a controlled
  bandit task. Thinking improves evidence use without strengthening the measured
  exploration signatures. This does not establish that explaining a specific
  tentative hypothesis causes worse selection, but it already motivates the
  broader distinction between reasoning and exploration.

- Liquin and Lombrozo. **Explain, Explore, Exploit: Effects of Explanation on
  Information Search.** CogSci 2017.
  [Paper](https://cognition.princeton.edu/document/217).
  Human studies found explanation could increase exploration and improve rule
  discovery; exploration effects differed across experiments. The target of an
  explanation matters conceptually: explaining observations need not have the same
  effect as explaining a chosen hypothesis. Harm must be tested, not presumed.

- Sinha and colleagues. **Can Language Models Falsify? Evaluating Algorithmic
  Reasoning with Counterexample Creation.** COLM 2025.
  [Project and paper](https://falsifiers.github.io/).
  Evaluates construction of counterexamples to incorrect programs and documents
  difficulties. Moving a similar failure into a coding task would not alone make
  the research contribution novel.

## What this pilot could establish

A within-case effect of the assigned processing instruction on objectively scored
test choice, with a fixed observable starting history and a separate ability check.
It can distinguish a neutral-deliberation effect from a justification-specific
one, subject to instruction-compliance and task-competence checks.

## What it cannot establish

- That the effect exists before real results are collected.
- That the model's latent hypothesis or confidence is fixed across calls.
- That generated explanation text, rather than the instruction or another
  bundled change, is the unique cause.
- That a separately demonstrated capability is used in each selection trace.
- That a positive test is intrinsically uninformative or biased.
- That results generalize beyond the task family and model studied.
- That the result is novel or sufficient for a top-conference paper.

If the prespecified signal appears, a stronger contribution would explain when
reasoning changes evidence selection, isolate the responsible behavioral factors,
and demonstrate consequences beyond this easy task.
