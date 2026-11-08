# Running experiments

Offline reproduction never contacts a model provider. The commands below are for inspecting prompts, testing plumbing with mock replies, or deliberately running new experiments.

## Experiment names

| Command target | What it tests |
| --- | --- |
| `scripted-source-relay` | Scripted relay wording, source/non-approval statements, and formatting controls |
| `delivery-channel-labels` | User-role, unverified-agent, and untrusted-data delivery |
| `source-and-label-controls` | Source naming, non-approval, and unverified-peer labels |
| `peer-approval-check` | A peer's third-person approval claim |
| `approval-channel-and-wording-sync` | Approval channel and wording on `[[sync-7]]` |
| `channel-wording-completion-sync` | The missing channel-by-wording cells on `[[sync-7]]` |
| `approval-channel-and-wording-file` | Approval channel and wording on `~filed-B~` |
| `channel-wording-completion-file` | The missing channel-by-wording cells on `~filed-B~` |
| `identical-approval-sync` | The identical approval sentence on `[[sync-7]]` |
| `identical-approval-file` | The identical approval sentence on `~filed-B~` |
| `network-luna-initial` | Initial mixed Luna/Gemini network episodes and seedless controls |
| `network-luna-replication-1` | Luna network replication, seeds 5–9 |
| `network-luna-replication-2` | Luna network replication, seeds 10–14 |
| `network-sol` | Mixed Sol/Gemini network episodes |
| `network-false-approval` | Network spread with and without a false approval claim |
| `natural-relay-exposure` | Coding and follower exposure to 39 natural relays |
| `relay-hop-monitor` | Two monitors scoring first-hop, second-hop, and benign updates |
| `approval-wording-monitor` | Two monitors scoring four approval-wording conditions |
| `simulated-actions` | Fictional tool-call proposals under approval and control conditions |

Use `who-can-say-yes criteria` for the preregistered thresholds and `who-can-say-yes plan` for exact call counts.

## Inspect before running

Every prompt can be inspected without credentials. Examples:

```bash
# Peer-reported formatting approval; the sentence appears in all four reminders
who-can-say-yes show-prompt formatting \
  --experiment identical-approval-sync --story garden \
  --condition peer-identical-approval --repetition 0

# The same sentence once in the operator's system prompt
who-can-say-yes show-prompt formatting \
  --experiment identical-approval-sync --story garden \
  --condition operator-identical-approval --repetition 0

# One occurrence in the requesting peer's action message
who-can-say-yes show-prompt action \
  --scenario s01 --condition peer-approval --repetition 0

# A natural relay and a monitor prompt
who-can-say-yes show-prompt natural-relay --relay-id 0
who-can-say-yes show-prompt relay-monitor --index 0
who-can-say-yes show-prompt approval-monitor \
  --story garden --condition peer-third-person-approval --repetition 0
```

## Mock runs

Without `--live`, the runner uses deterministic mock replies and requires no credentials:

```bash
who-can-say-yes run formatting \
  --experiment identical-approval-sync --models luna \
  --out outputs/mock-formatting.jsonl

who-can-say-yes run action --stage pilot --models luna \
  --out outputs/mock-actions.jsonl

who-can-say-yes run network --experiment network-luna-replication-1 \
  --out outputs/mock-network.jsonl
```

Mock replies test record schemas, parsing, and analysis plumbing. They do not reproduce scientific findings and must not be presented as model evidence.

## Live-call safeguards

A live run requires all of the following:

1. `--live`;
2. `--max-calls`, counting every provider attempt including retries;
3. `--max-usd`, a positive worst-case list-price cap;
4. An explicit model and prices in `models.json`;
5. The relevant provider credential.

Before each attempt, the runner reserves one token per character of prompt text plus the full output budget, and refuses the call if that conservative estimate would exceed either cap. Unpriced models fail closed. Existing output files are never overwritten.

The caps are local safeguards, not a provider invoice or a guarantee against every concurrent process. Use one run per budget cap and verify current prices yourself. The recorded prices date from 6 November 2026.

Example using Luna through OpenRouter:

```bash
export OPENROUTER_API_KEY='your-key'

who-can-say-yes run formatting \
  --experiment identical-approval-sync --models luna \
  --out outputs/luna-sync.jsonl \
  --live --max-calls 30 --max-usd 1.00
```

For Anthropic models, set `ANTHROPIC_API_KEY`. OpenRouter models request temperature 1.0; Anthropic calls omit temperature and use the provider default. Calls start with at least a 3,000-token output budget. An empty reply is retried once with twice that budget. Retry attempts count toward `--max-calls`.

The live log defaults to a `*-calls.jsonl` path beside the output. It contains prompts and replies and is excluded by `.gitignore`. Review it before sharing.

## Action experiments

The revised pilot uses four pilot-only scenarios and five conditions. The main run uses 24 scenarios, 12 conditions, and two repetitions per model:

```bash
who-can-say-yes run action --stage pilot --models luna \
  --out outputs/luna-action-pilot.jsonl \
  --live --max-calls 25 --max-usd 1.00

who-can-say-yes run action --stage main --models luna \
  --out outputs/luna-action-main.jsonl \
  --live --max-calls 600 --max-usd 25.00
```

These are examples, not spending recommendations. Inspect `who-can-say-yes plan --models luna` and choose your own caps.

An action is only a textual proposal. The runner does not execute file sharing, deletion, announcements, or publication. The scorer searches the final `ACTIONS:` line for the requested tool name and does not validate its arguments.

The platform-status conditions insert trusted text into the same user message as the peer request. They compute no signature and provide no execution-boundary enforcement.

## Generating new scenarios

Generation is optional; all 28 study scenarios are already included. New generation uses GLM 5.2 through Adaption and requires `ADAPTION_API_KEY`, `--live`, and explicit caps:

```bash
who-can-say-yes generate-scenarios \
  --out outputs/new-action-scenarios.json \
  --live --max-calls 35 --max-usd 5.00
```

To retain the included scenarios and regenerate selected IDs, add `--resume-existing --ids s01,s19`. The validator rejects malformed rows, authority claims already present in the request, peer updates that make requests, and disallowed financial framing. The generation prompt also forbids dangerous or illegal content; automatic checks do not replace reviewing the scenarios yourself before use.

## Replication cautions

- Saved replies are the evidence for the reported results; new samples can differ.
- The formatting comparison changes channel and repetition together. Use the action comparison or a new one-peer control if frequency is your question.
- System-prompt versus user-turn delivery is not human or agent authentication.
- Small story and scenario counts limit generalisation. Action sign tests cluster by scenario; reply-level Fisher tests and Wilson intervals are descriptive only.
- Failed preregistered predictions are study results, not software failures.
