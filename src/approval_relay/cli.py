import argparse
import json
from pathlib import Path

from . import actions, formatting, monitors, networks
from .data import (
    MODELS, ROOT, action_scenarios, append_jsonl, prompt_dataset, write_jsonl,
)
from .figures import generate_figures
from .providers import LiveClient, MockClient
from .results import build_summary, print_headline


def _models(value):
    models = tuple(value.split(",")) if value else MODELS
    unknown = set(models) - set(MODELS)
    if unknown:
        raise ValueError(f"Unknown model keys: {sorted(unknown)}; choose from {MODELS}")
    return models


def _client(args):
    if not args.live:
        return MockClient(args.mock_mode)
    log_path = args.log or str(Path(args.out).with_name(Path(args.out).stem + "-calls.jsonl"))
    return LiveClient(args.max_calls, args.max_usd, log_path=log_path, config_path=args.config)


def _add_live_options(parser, output_required=True):
    parser.add_argument("--out", required=output_required, help="New output path; existing files are never overwritten")
    parser.add_argument("--live", action="store_true", help="Make paid provider calls; without this flag, use offline mock replies")
    parser.add_argument("--mock-mode", choices=("copy", "never"), default="copy")
    parser.add_argument("--max-calls", type=int, help="Required live-call cap, including retries")
    parser.add_argument("--max-usd", type=float, help="Required live spending cap in USD")
    parser.add_argument("--log", help="Live-call log path (default: alongside --out)")
    parser.add_argument("--config", help="Alternative model configuration with explicit token prices")


def _new_output(path):
    path = Path(path)
    if path.exists():
        raise FileExistsError(f"Refusing to overwrite {path}; choose a new output path")
    path.parent.mkdir(parents=True, exist_ok=True)


def cmd_verify(args):
    summary = build_summary()
    print_headline(summary)
    problems = list(summary["manifest_mismatches"])
    for group, result in summary["independent_rescore"].items():
        if result["mismatches"]:
            problems.append(f"{group}: {result['mismatches']} rescoring mismatches")
    if summary["preregistered"]["summary"]["total"] != 45:
        problems.append("Expected 45 preregistered criteria")
    if args.out:
        output = Path(args.out)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(summary, indent=1, ensure_ascii=False) + "\n")
        print(f"Wrote full verification summary to {output}")
    if problems:
        for problem in problems:
            print("PROBLEM:", problem)
        return 1
    print("Verification passed: data hashes and independent outcome rescoring are consistent.")
    return 0


def cmd_criteria(args):
    summary = build_summary()["preregistered"]
    for item in summary["criteria"]:
        print(f"{item['original_id']:5} {item['status']:13} {item['description']}")
    print("Summary:", summary["summary"])
    print("Pilot gates:", {stage: "passed" if gate["passed"] else "failed" for stage, gate in summary["pilot_gate"].items()})
    return 0


def cmd_tables(args):
    print_headline(build_summary())
    return 0


def cmd_plan(args):
    models = _models(args.models)
    scenarios = action_scenarios()
    plans = {}
    for experiment in formatting.EXPERIMENT_CONDITIONS:
        plans[f"formatting:{experiment}"] = sum(1 for _ in formatting.experiment_jobs(experiment, models))
    for stage in ("pilot", "main"):
        plans[f"actions:{stage}"] = sum(1 for _ in actions.action_jobs(stage, scenarios, models))
    for experiment in networks.NETWORK_EXPERIMENTS:
        plans[f"network:{experiment}"] = sum(1 for _ in networks.network_jobs(experiment)) * 66
    plans["natural-relay-exposure"] = 39 + 20 + 39 * len(models)
    plans["relay-hop-monitor"] = 160 * 2
    plans["approval-wording-monitor"] = 48 * 2
    print(json.dumps(plans, indent=1))
    print("Counts exclude empty-reply retries. Live retries count toward --max-calls.")
    return 0


def cmd_show_prompt(args):
    condition = args.condition or {
        "formatting": "operator-identical-approval",
        "action": "operator-approval",
        "approval-monitor": "bare-reminder",
    }.get(args.kind)
    if args.kind == "formatting":
        _, messages = formatting.build_prompt(args.experiment, args.story, condition, args.repetition)
    elif args.kind == "action":
        scenario = next(row for row in action_scenarios() if row["id"] == args.scenario)
        _, messages = actions.build_prompt(scenario, condition, args.repetition)
    elif args.kind == "natural-relay":
        relay = next(row for row in prompt_dataset("natural-relays.json") if row["relay_id"] == args.relay_id)
        _, messages = monitors.natural_relay_messages(relay)
    elif args.kind == "relay-monitor":
        item = prompt_dataset("relay-monitor-messages.json")[args.index]
        messages = [{"role": "user", "content": monitors.MONITOR_PROMPT.format(text=item["input_text"])}]
    else:
        item = next(
            row for row in prompt_dataset("approval-monitor-messages.json")
            if row["story"] == args.story and row["condition"] == condition and row["repetition"] == args.repetition
        )
        messages = [{"role": "user", "content": monitors.MONITOR_PROMPT.format(text=item["input_text"])}]
    print(json.dumps(messages, indent=1, ensure_ascii=False))
    return 0


def cmd_run(args):
    _new_output(args.out)
    client = _client(args)
    models = _models(args.models)
    if args.kind == "formatting":
        if not args.experiment:
            raise ValueError("--experiment is required for formatting runs")
        rows = formatting.run_experiment(client, args.experiment, models)
    elif args.kind == "action":
        rows = actions.run_experiment(client, args.stage, action_scenarios(), models)
    elif args.kind == "network":
        if not args.experiment:
            raise ValueError("--experiment is required for network runs")
        rows = networks.run_experiment(client, args.experiment)
    elif args.kind == "natural-relay":
        rows = monitors.run_natural_relays(client, models)
    elif args.kind == "relay-monitor":
        rows = monitors.run_relay_monitors(client)
    else:
        rows = monitors.run_approval_monitors(client)
    count = 0
    for row in rows:
        append_jsonl(args.out, row)
        count += 1
        if count % 25 == 0:
            print(f"{count} records written", flush=True)
    print(f"Wrote {count} records to {args.out}")
    if args.live:
        print(f"Live calls including retries: {client.calls}; reserved worst-case ${client.reserved_usd:.4f}; logged list cost ${client.actual_usd:.4f}")
    else:
        print("These are mock plumbing outputs, not evidence about model behaviour.")
    return 0


def cmd_generate(args):
    if not args.live:
        raise ValueError("Scenario generation requires --live and explicit call/spending caps; no paid call is made by default")
    _new_output(args.out)
    client = LiveClient(args.max_calls, args.max_usd, log_path=args.log, config_path=args.config)
    existing = action_scenarios() if args.resume_existing else None
    ids = set(args.ids.split(",")) if args.ids else None
    scenarios = actions.generate_scenarios(client, existing=existing, scenario_ids=ids)
    Path(args.out).write_text(json.dumps(scenarios, indent=1, ensure_ascii=False) + "\n")
    problems = {row["id"]: actions.scenario_problems(row) for row in scenarios if actions.scenario_problems(row)}
    print(f"Wrote {len(scenarios)} scenarios to {args.out}; validation problems: {problems or 'none'}")
    return 1 if problems else 0


def build_parser():
    parser = argparse.ArgumentParser(
        prog="who-can-say-yes",
        description="Reproduce saved results or run harmless operator-approval experiments. No live calls unless --live is explicit.",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    verify = sub.add_parser("verify", help="Verify hashes, criteria, tables, labels, costs, and independent rescoring")
    verify.add_argument("--out", default="results/summary.json")
    verify.set_defaults(function=cmd_verify)
    criteria = sub.add_parser("criteria", help="Print all 45 preregistered criteria and outcomes")
    criteria.set_defaults(function=cmd_criteria)
    tables = sub.add_parser("tables", help="Print the headline result tables")
    tables.set_defaults(function=cmd_tables)
    figures = sub.add_parser("figures", help="Regenerate all figures")
    figures.add_argument("--out", default="results/figures")
    figures.set_defaults(function=lambda args: (print(f"Wrote {len(generate_figures(args.out))} PNG figures and matching PDFs to {args.out}"), 0)[1])
    plan = sub.add_parser("plan", help="Count planned calls without provider credentials")
    plan.add_argument("--models", default=",".join(MODELS))
    plan.set_defaults(function=cmd_plan)

    show = sub.add_parser("show-prompt", help="Print an exact prompt without making a call")
    show.add_argument("kind", choices=("formatting", "action", "natural-relay", "relay-monitor", "approval-monitor"))
    show.add_argument("--experiment", default="identical-approval-sync")
    show.add_argument("--story", default="garden")
    show.add_argument("--condition", help="Condition name; a suitable default is chosen for the experiment kind")
    show.add_argument("--repetition", type=int, default=0)
    show.add_argument("--scenario", default="s01")
    show.add_argument("--relay-id", type=int, default=0)
    show.add_argument("--index", type=int, default=0)
    show.set_defaults(function=cmd_show_prompt)

    run = sub.add_parser("run", help="Run a formatting, action, network, natural-relay, or monitor experiment")
    run.add_argument("kind", choices=("formatting", "action", "network", "natural-relay", "relay-monitor", "approval-monitor"))
    run.add_argument("--experiment", choices=sorted(set(formatting.EXPERIMENT_CONDITIONS) | set(networks.NETWORK_EXPERIMENTS)))
    run.add_argument("--stage", choices=("pilot", "main"), default="main")
    run.add_argument("--models", default=",".join(MODELS))
    _add_live_options(run)
    run.set_defaults(function=cmd_run)

    generate = sub.add_parser("generate-scenarios", help="Generate fictional action scenarios through Adaption (paid, explicit --live required)")
    _add_live_options(generate)
    generate.add_argument("--ids", help="Comma-separated scenario IDs to regenerate")
    generate.add_argument("--resume-existing", action="store_true", help="Keep existing scenarios and replace only selected IDs")
    generate.set_defaults(function=cmd_generate, mock_mode="copy", live=False)
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.function(args)
    except (ValueError, FileExistsError, KeyError, StopIteration) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    raise SystemExit(main())
