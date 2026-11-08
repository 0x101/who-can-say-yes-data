# Who Can Say Yes?

Code and data for a study of **operator approval and peer-reported approval in multi-agent LLM systems**.

The central question is simple: in a fictional team, if a human operator approves a convention or action, does a model respond differently when an AI peer merely reports that approval? The study holds the approval sentence fixed in its main comparisons and examines harmless formatting conventions and simulated tool-call proposals.

This repository is a standalone reproduction package.

## What is included

- Saved replies for every result used in the study: **6,789 records**.
- The **24 main fictional action scenarios**, four pilot scenarios, and four formatting stories.
- Exact natural-relay and monitor inputs, with no extra downloads.
- Both natural-relay hand-labelling passes and their independence caveat.
- Descriptive experiment and condition names, with all 45 preregistered criteria and outcomes.
- Offline analysis, independent rescoring, statistical checks, and all 12 figures.
- Prompt inspection, mock runs, and an explicitly capped live runner for new experiments.
- Privacy-reduced token records supporting the cost disclosures.

All scenarios and actions are fictional and harmless. **No tool is executed.** In the action experiment, a parser checks only whether the requested tool name appears in the model's final `ACTIONS:` line. Arguments are not validated. The simulated platform-status text is not a cryptographic check.

## Reproduce the saved results

Use Python 3.12 or later:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
bash reproduce.sh
```

The script needs no provider credentials and makes no paid calls. It:

1. Verifies data hashes and record counts.
2. Recomputes all **45 preregistered criteria** and both action pilot gates.
3. Rebuilds the headline tables, scenario-level sign tests, secondary analyses, and cost totals.
4. Independently rescores every saved formatting, action, and network outcome.
5. Regenerates all figures and runs the offline tests.

Expected checks include:

- **32 criteria met and 13 not met**; the initial action pilot fails and the revised pilot passes.
- **2,514 formatting outcomes, 3,696 action outcomes, and 6,864 network updates** rescore with zero mismatches.
- The action main run has **3,453 parseable replies out of 3,456**.
- The natural-relay hand labels agree on **195/195 fields**, with the documented limitation that the second pass was not blind.
- Logged list-price totals reproduce as **$6.006268925** for the main experiments, **$4.93388588** for the action experiments, and **0.34210260 Adaption credits** for scenario generation. Separate unmeasured reservation holds are not treated as spend.

Outputs are written to `results/summary.json` and `results/figures/`. Figure rendering can vary by platform even with the same Matplotlib version.

## Useful commands

The reproduction script sets `PYTHONPATH` automatically. To use the commands yourself, either install the package:

```bash
python -m pip install -e .
```

or run commands with `PYTHONPATH=src python -m approval_relay.cli ...`.

```bash
# Print the main result tables
who-can-say-yes tables

# Print every preregistered prediction and its outcome
who-can-say-yes criteria

# Count calls without contacting a provider
who-can-say-yes plan

# Inspect the identical-sentence formatting comparison
who-can-say-yes show-prompt formatting \
  --experiment identical-approval-sync \
  --story garden --condition operator-identical-approval --repetition 0

who-can-say-yes show-prompt formatting \
  --experiment identical-approval-sync \
  --story garden --condition peer-identical-approval --repetition 0

# Inspect an action prompt
who-can-say-yes show-prompt action \
  --scenario s01 --condition peer-approval --repetition 0

# Exercise the action pipeline with free mock replies
who-can-say-yes run action --stage pilot --models luna \
  --out outputs/mock-action-pilot.jsonl
```

Mock output tests the plumbing. It is not evidence about a real model.

## Run new model calls

Live calls are off by default. They require `--live`, a call cap, and a spending cap. The runner also refuses models without explicit token prices in `models.json`.

For example, after reviewing the exact prompts and current provider pricing:

```bash
export OPENROUTER_API_KEY='your-key'

who-can-say-yes run formatting \
  --experiment identical-approval-sync \
  --models luna \
  --out outputs/luna-sync.jsonl \
  --live --max-calls 30 --max-usd 1.00
```

The planned 24 calls can incur additional empty-reply retries, which is why the cap above is higher. Existing output files are never overwritten. Use a new output path for each run.

Anthropic and Adaption use `ANTHROPIC_API_KEY` and `ADAPTION_API_KEY` respectively. See [EXPERIMENTS.md](EXPERIMENTS.md) before any live run. Model availability and provider behaviour can change; a new sampled run is a replication, not a deterministic replay of the saved replies.

## Repository guide

- `src/approval_relay/`: prompt builders, provider clients, scoring, preregistered analyses, figures, and CLI.
- `data/records/`: saved replies and outcomes with descriptive metadata.
- `data/scenarios/`: all formatting stories and action scenarios.
- `data/prompts/`: fixed natural-relay and monitor inputs.
- `data/labels/`: structured natural-relay hand labels.
- `data/costs/`: token-only call records and the separate reservation-hold disclosure.
- `data/manifest.json`: source and published-file hashes.
- `data/preregistration.json`: audit IDs and registration references in machine-readable form.
- `tests/`: offline regression tests.
- [PREREGISTRATION.md](PREREGISTRATION.md): all 45 preregistered criteria and outcomes.
- [DATA.md](DATA.md): data schema, provenance, and measurement boundaries.
- [EXPERIMENTS.md](EXPERIMENTS.md): experiment names, call planning, live-run instructions, and safety limits.

## Interpretation boundaries

The formatting comparison varies **both delivery channel and repetition**: operator approval appears once, while peer approval appears in all four reminders. It does not isolate channel alone. The action comparison contains one approval sentence per channel, but it is a different task, not a frequency-control replication.

The operator channel is a system prompt and peer messages are embedded in a user turn. The study tests API instruction privilege, not authenticated human or agent identity. Model behaviour also changes across models and tasks; the saved results do not support a universal channel effect or a safety ranking.

Approval should be enforced by trusted infrastructure outside the model. That is a design recommendation motivated by these results and prior work, not a safeguard implemented or validated here.

## Licences

The code is released under the [MIT License](LICENSE). The data, saved replies, scenarios, hand labels, cost records, figures, and documentation are released under [Creative Commons Attribution 4.0 International (CC BY 4.0)](DATA-LICENSE.md).
