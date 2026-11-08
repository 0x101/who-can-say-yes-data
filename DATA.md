# Data and provenance

## Included data

| Location | Contents |
| --- | --- |
| `data/records/formatting/` | 2,573 formatting and natural-relay records |
| `data/records/monitoring/` | 416 monitor records |
| `data/records/networks/` | 104 network episodes, containing 6,864 agent updates |
| `data/records/actions/` | 3,696 action records: 3,456 main and 240 across two pilots |
| `data/scenarios/` | Four formatting stories and 28 fictional action scenarios |
| `data/prompts/` | 39 natural relays, 160 relay-monitor inputs, and 48 approval-monitor inputs |
| `data/labels/natural-relay-labels.json` | Five hand-label fields for 39 relays, from two documented passes |
| `data/costs/` | 9,967 main-experiment and 3,743 action/generation token records, plus reservation-hold disclosure |

The action scenarios are included locally. No external dataset service or Adaption account is needed for offline reproduction. Adaption is needed only to generate new scenarios through GLM 5.2.

## Readable schema

Public metadata uses descriptive names:

- `experiment` and `condition` identify what was tested;
- `model` uses keys such as `luna` and `sonnet`, resolved in `models.json`;
- `adopted` records formatting and network outcomes;
- `proposed` records a simulated tool-call proposal;
- `labelled`, `tagged_neighbours`, and `uses_mixed_model` describe network records;
- `action_line_present`, `numeric_headcount`, and `repeated_approval_code` provide additional action checks.

The main action conditions are `no-approval`, `operator-approval`, `peer-approval`, `operator-non-approval`, `correct-code`, `forged-code`, `missing-code`, `simulated-status-valid`, `simulated-status-failed`, `ordinary-request`, `ordinary-request-with-context`, and `designated-relay`.

Audit IDs remain available for readers who want to compare the criteria with their registration records. They are not needed to use the data or run experiments.

## Saved records and integrity

Model replies, validity flags, monitor scores, and outcomes are preserved. Provider reasoning is omitted because no reported analysis uses it. Cost records omit messages, replies, and call tags; each retains token counts and a hash of the deduplication key.

`data/manifest.json` records public filenames, hashes, and row counts, along with source metadata for audit. `who-can-say-yes verify` checks all public record and auxiliary-data hashes.

The verifier independently recomputes formatting adoption, action parsing and proposals, numeric headcounts, repeated approval codes, and network tag adoption. Expected result: zero mismatches across 2,514 formatting outcomes, 3,696 action outcomes, and 6,864 network updates. Three action replies have no readable `ACTIONS:` line and count as not proposing the requested call.

## Preregistration

The 45 criteria were fixed before their corresponding runs; 32 were met and 13 were not met. The action pilot allowed one prompt correction after the first gate failed. The initial gate fails and the revised gate passes.

`PREREGISTRATION.md` lists the criteria and outcomes in readable form. `data/preregistration.json` records their audit IDs and registration references. The standalone evaluator reproduces those criteria; it is not a byte-for-byte copy of the original analysis code.

## Prior work

Some components predate the hackathon: the provider-call and budget layer, formatting-story builder, network runner, and three network runs that supplied the 39 natural relays. The original pre-sprint tree is commit `0ecbfa1` at 6 November 2026, 20:27 UTC, before the 21:30 UTC kickoff. The relay-template builder was added after kickoff. The reported confirmation and action experiments were designed, preregistered, and run during the hackathon.

## Hand-label limitations

The natural-relay rubric records whether each text names who asked, attributes the convention to anyone, asks the reader to use the tag, carries the tag, and gives a reason. The two passes agree on 195/195 fields. The second pass saw the first pass's rubric and table before finalising its labels, so it is a consistency audit, not a blind independent replication. Only two relays name who asked, so the natural source-present/source-absent adoption contrast is not estimable.

## Costs

Token costs use the recorded 6 November 2026 list prices in `models.json`. Calls are deduplicated on timestamp, model, call tag, input tokens, and output tokens; batch calls are halved. Published rows contain a hash of that key instead of the tag.

| Group | Calls | Provider breakdown | Total |
| --- | ---: | --- | ---: |
| Main experiments | 9,967 | OpenRouter $3.316457425; Anthropic $2.689811500 | $6.006268925 |
| Action pilots and main run | 3,706 | OpenRouter $1.909598580; Anthropic $3.024287300 | $4.933885880 |
| Scenario generation | 37 | Adaption | 0.34210260 credits |

Separate reservation holds of $2.50 and $0.35 are worst-case holds, not measured invoices, and are not added to logged spend.

## Privacy and scenario generation

The scenarios use invented people, organisations, files, permissions, and actions. The package contains no credentials, personal data, real permissions, or executed actions. Provider reasoning and private budget state are excluded. The released prompts reproduce benign evaluations rather than an operational attack recipe.

GLM 5.2 generated the action scenarios through Adaption Labs.
