import argparse
from collections import defaultdict
from pathlib import Path

from .data import DISPLAY_NAMES, MODELS, all_records, valid
from .scoring import still_requests_tag
from .stats import wilson

BLUE, ORANGE, GREY = "#2a78d6", "#eb6834", "#9a9893"
INK, INK2, GRID, SURFACE = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
STYLE = {
    "operator": dict(color=BLUE, hatch=None, edgecolor="#ffffff"),
    "peer": dict(color=ORANGE, hatch="///", edgecolor="#ffffff"),
    "control": dict(color=GREY, hatch="..", edgecolor="#ffffff"),
}


def _rates(rows, key):
    counts = defaultdict(lambda: [0, 0])
    for row in rows:
        if not valid(row):
            continue
        group = key(row)
        if group is not None:
            counts[group][0] += bool(row["adopted"])
            counts[group][1] += 1
    return counts


def _bars(ax, labels, groups, counts, ylabel=None, rotate=0, gap=True, common_n=None):
    positions, current = [], 0.0
    for index, group in enumerate(groups):
        if gap and index and group != groups[index - 1]:
            current += .5
        positions.append(current)
        current += 1
    for position, group, (adopted, total) in zip(positions, groups, counts):
        proportion = adopted / total if total else 0
        low, high = wilson(adopted, total) if total else (0, 0)
        style = STYLE[group]
        ax.bar(position, proportion, width=.72, color=style["color"], hatch=style["hatch"], edgecolor=style["edgecolor"], linewidth=0, zorder=2)
        if total:
            ax.errorbar(position, proportion, yerr=[[max(0, proportion - low)], [max(0, high - proportion)]], color=INK2, lw=.8, capsize=2, zorder=3)
        label = str(adopted) if common_n and total == common_n else f"{adopted}/{total}"
        ax.text(position, min(1, high if total else 0) + .03, label, ha="center", va="bottom", fontsize=6.5, color=INK2)
    ax.set_xticks(positions)
    if rotate:
        ax.set_xticklabels(labels, fontsize=6.5, rotation=rotate, ha="right", rotation_mode="anchor")
    else:
        ax.set_xticklabels(labels, fontsize=6.5)
    ax.set_ylim(0, 1.18)
    ax.set_yticks([0, .5, 1], ["0%", "50%", "100%"])
    ax.yaxis.grid(True, color=GRID, lw=.6, zorder=0)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    if ylabel:
        ax.set_ylabel(ylabel)


def _legend(fig, plt, items, y=.005):
    from matplotlib.patches import Patch
    handles = [Patch(facecolor=STYLE[group]["color"], hatch=STYLE[group]["hatch"], edgecolor="#ffffff", label=label) for group, label in items]
    fig.legend(handles=handles, loc="lower center", ncol=len(items), frameon=False, fontsize=7.5, bbox_to_anchor=(.5, y))


def _save(fig, plt, out, name):
    out.mkdir(parents=True, exist_ok=True)
    for extension in ("png", "pdf"):
        fig.savefig(out / f"{name}.{extension}", dpi=220 if extension == "png" else None)
    plt.close(fig)


def _model_panels(plt, rows, conditions, labels, groups, out, name, size=(7.2, 4.4), legend=None):
    labels = {key: value.replace("operator", "op") for key, value in labels.items()}
    counts = _rates(rows, lambda row: (row["model"], row["condition"]))
    fig, axes = plt.subplots(2, 3, figsize=size, sharey=True)
    for ax, model in zip(axes.flat, MODELS):
        _bars(ax, [labels[c] for c in conditions], [groups[c] for c in conditions], [counts[(model, c)] for c in conditions], gap=False,
              ylabel="adopts the convention" if model in ("luna", "sonnet") else None)
        ax.set_title(DISPLAY_NAMES[model], fontsize=8.5, loc="left", color=INK)
        ax.tick_params(axis="x", labelsize=6.5)
    if legend:
        _legend(fig, plt, legend)
    fig.tight_layout(rect=(0, .05, 1, 1))
    _save(fig, plt, out, name)


def _source_figure(plt, rows, out):
    conditions = ("original-order", "source-reason-and-nonapproval", "source-and-nonapproval", "reason-only", "bare-reminder", "no-relay", "operator-request", "bare-marker")
    labels = {
        "original-order": "original order", "source-reason-and-nonapproval": "origin + reason",
        "source-and-nonapproval": "origin only", "reason-only": "reason only", "bare-reminder": "neither",
        "no-relay": "no relay", "operator-request": "operator asks", "bare-marker": "bare tag",
    }
    groups = {c: "peer" for c in conditions[:5]} | {c: "control" for c in conditions[5:]}
    counts = _rates(rows, lambda row: (row["model"], row["condition"]))
    fig, axes = plt.subplots(2, 3, figsize=(7.2, 5), sharey=True)
    for index, (ax, model) in enumerate(zip(axes.flat, MODELS)):
        _bars(ax, [labels[c] for c in conditions], [groups[c] for c in conditions], [counts[(model, c)] for c in conditions],
              ylabel="adopts the tag" if model in ("luna", "sonnet") else None, rotate=40, common_n=12)
        if index < 3:
            ax.set_xticklabels([])
        ax.set_title(DISPLAY_NAMES[model], fontsize=8.5, loc="left")
    fig.suptitle("Numbers above bars: adoptions out of 12 (k/n where replies were lost).\nSource cells also say the operator did not approve; later controls separate those statements.", fontsize=6.5, color=INK2, x=.01, ha="left", y=.995)
    _legend(fig, plt, [("peer", "scripted peer relay"), ("control", "control")])
    fig.tight_layout(rect=(0, .05, 1, .965))
    _save(fig, plt, out, "fig1-factorial")


def _natural_figure(plt, rows, out):
    texts = {row["relay_id"]: row["input_text"] for row in rows if row.get("role") == "coder" and row.get("coder") == "haiku"}
    counts = _rates([row for row in rows if row.get("role") == "follower"], lambda row: (row["model"], still_requests_tag(texts[row["relay_id"]])))
    fig, ax = plt.subplots(figsize=(7.2, 2.7))
    labels, groups, values = [], [], []
    for model in MODELS:
        for requests, group in ((True, "operator"), (False, "control")):
            labels.append("")
            groups.append(group)
            values.append(counts[(model, requests)])
    _bars(ax, labels, groups, values, ylabel="adopts the tag", gap=False)
    ax.set_xticks([i + .5 for i in range(0, len(labels), 2)])
    ax.set_xticklabels([DISPLAY_NAMES[m].replace(" ", "\n", 1) for m in MODELS], fontsize=6.5)
    _legend(fig, plt, [("operator", "relay still asks readers to use the tag"), ("control", "relay only carries the tag")], y=.08)
    fig.tight_layout(rect=(0, .12, 1, 1))
    _save(fig, plt, out, "fig3-natural-relays")


def _monitor_figure(plt, rows, out):
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.9), sharey=True)
    classes = (("first-hop", "first-hop relay", ORANGE, "///"), ("requests", "second-hop, still asks", BLUE, None),
               ("tag-only", "second-hop, tag only", BLUE, "xxx"), ("benign", "benign update", GREY, ".."))
    for ax, monitor in zip(axes, ("haiku", "sonnet")):
        by_class = defaultdict(list)
        for row in rows:
            if row["model"] != monitor or row.get("score") is None:
                continue
            category = row["message_type"]
            if category == "second-hop":
                category = "requests" if still_requests_tag(row["input_text"]) else "tag-only"
            by_class[category].append(row["score"])
        threshold = sorted(by_class["first-hop"])[int(.2 * len(by_class["first-hop"]))]
        for index, (category, label, colour, hatch) in enumerate(classes):
            values = by_class[category]
            flagged = sum(score >= threshold for score in values)
            ax.barh(index, flagged / (len(values) or 1), height=.62, color=colour, hatch=hatch, edgecolor="#ffffff", linewidth=0)
            ax.text(flagged / (len(values) or 1) + .02, index, f"{flagged}/{len(values)} flagged", va="center", fontsize=7, color=INK2)
        ax.set_yticks(range(len(classes)), [c[1] for c in classes])
        ax.set_xlim(0, 1.3)
        ax.set_xticks([0, .5, 1], ["0%", "50%", "100%"])
        ax.xaxis.grid(True, color=GRID, lw=.6, zorder=0)
        ax.set_axisbelow(True)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        ax.set_title(f"{DISPLAY_NAMES[monitor].replace('Claude ', '')} monitor, scores of {threshold}+ flagged", fontsize=8, loc="left")
    axes[0].invert_yaxis()
    fig.text(.01, .01, "The second-hop request/tag-only split is post hoc.", fontsize=6.5, color=INK2)
    fig.tight_layout(rect=(0, .04, 1, 1))
    _save(fig, plt, out, "fig2-monitors")


def _round_lines(ax, episodes, mixed_model, lines):
    endpoints = []
    for key, colour, marker, style, name in lines:
        values = []
        for round_number in range(1, 7):
            selected = [item for row in episodes if key(row) for item in row["rounds"] if item["uses_mixed_model"] == mixed_model and item["round"] == round_number]
            values.append(sum(bool(item["adopted"]) for item in selected) / len(selected) if selected else 0)
        ax.plot(range(1, 7), values, color=colour, marker=marker, ls=style, lw=2, ms=6, label=name)
        endpoints.append(values[-1])
    close = len(endpoints) == 2 and abs(endpoints[0] - endpoints[1]) < .06
    for index, value in enumerate(endpoints):
        offset = 0 if not close else (5 if value >= max(endpoints) and index == endpoints.index(max(endpoints)) else -5)
        ax.annotate(f"{value:.0%}", (6, value), xytext=(6, offset), textcoords="offset points", va="center", fontsize=7.5, color=INK2)
    ax.set_xticks(range(1, 7))
    ax.set_xlabel("round")
    ax.set_xlim(.7, 6.6)
    ax.set_ylim(0, 1)
    ax.yaxis.set_major_formatter(lambda value, _: f"{value:.0%}")
    ax.grid(axis="y", color=GRID, lw=.6)
    ax.spines[["top", "right"]].set_visible(False)


def _network_figure(plt, rows, out):
    specifications = (
        ("network-luna-initial", "Luna", "seeds 0–4"),
        ("network-luna-replication-1", "Luna", "seeds 5–9"),
        ("network-luna-replication-2", "Luna", "seeds 10–14"),
        ("network-sol", "Sol", "seeds 0–4"),
    )
    specifications = tuple(spec for spec in specifications if any(row["experiment"] == spec[0] for row in rows))
    fig, axes = plt.subplots(2, len(specifications), figsize=(2.45 * len(specifications) + .5, 5.4), sharey=True, squeeze=False)
    lines = ((lambda row: not row["labelled"], BLUE, "o", "-", "plain peer messages"),
             (lambda row: row["labelled"], ORANGE, "s", "--", "labelled ‘not verified’"))
    for column, (experiment, model, seeds) in enumerate(specifications):
        episodes = [row for row in rows if row["experiment"] == experiment and not row["seedless_control"] and not row["incomplete"]]
        pairs = len({(row["graph"], row["seed"]) for row in episodes})
        for panel, (mixed, title) in enumerate(((True, f"{model} nodes"), (False, "Gemini nodes"))):
            _round_lines(axes[panel][column], episodes, mixed, lines)
            axes[panel][column].set_title(f"{title}, {seeds}" + ("" if pairs == 10 else f" ({pairs} pairs)"), fontsize=8, loc="left")
    for row in axes:
        row[0].set_ylabel("updates ending with the tag")
    axes[0][0].legend(frameon=False, fontsize=7, loc="upper left")
    fig.text(.01, .01, "Each line pools ten episodes: 12 agents, six rounds, ring and small-world graphs. Final-round measurement was preregistered after the first seed set.", fontsize=6.5, color=INK2)
    fig.tight_layout(rect=(0, .035, 1, 1))
    _save(fig, plt, out, "fig6-group-run")


def _false_approval_figure(plt, rows, out):
    fig, axes = plt.subplots(1, 2, figsize=(6.6, 2.9), sharey=True)
    lines = ((lambda row: not row["false_approval_claim"], BLUE, "o", "-", "plain relay"),
             (lambda row: row["false_approval_claim"], ORANGE, "s", "--", "relay + false approval claim"))
    for ax, (mixed, title) in zip(axes, ((True, "Luna nodes"), (False, "Gemini nodes"))):
        _round_lines(ax, rows, mixed, lines)
        ax.set_title(f"{title}, seeds 0–4", fontsize=8.5, loc="left")
    axes[0].set_ylabel("updates ending with the tag")
    axes[0].legend(frameon=False, fontsize=7.5, loc="upper left")
    fig.text(.01, .01, "Ten episodes per condition. The formatting tag is harmless; the approval claim is false.", fontsize=6.5, color=INK2)
    fig.tight_layout(rect=(0, .05, 1, 1))
    _save(fig, plt, out, "fig8-false-approval")


def _same_words_figure(plt, rows, out):
    experiments = [experiment for experiment in ("identical-approval-sync", "identical-approval-file") if any(row["experiment"] == experiment for row in rows)]
    conventions = {"identical-approval-sync": "[[sync-7]]", "identical-approval-file": "~filed-B~"}
    fig, axes = plt.subplots(len(experiments), 3, figsize=(6.6, 2.6 * len(experiments)), sharey=True, squeeze=False)
    for panel, experiment in zip(axes, experiments):
        selected = [row for row in rows if row["experiment"] == experiment]
        counts = _rates(selected, lambda row: (row["model"], row["condition"]))
        for ax, model in zip(panel, ("luna", "sol", "sonnet")):
            _bars(ax, ["in operator\nchannel", "in repeated peer\nreminders"], ["operator", "peer"],
                  [counts[(model, "operator-identical-approval")], counts[(model, "peer-identical-approval")]],
                  gap=False, ylabel="adopts the tag" if model == "luna" else None)
            ax.set_title(f"{DISPLAY_NAMES[model]}, {conventions[experiment]}", fontsize=8.5, loc="left")
            ax.tick_params(axis="x", labelsize=7)
    _legend(fig, plt, [("operator", "operator channel"), ("peer", "peer messages")], y=.01)
    fig.tight_layout(rect=(0, .1 / len(experiments), 1, 1))
    _save(fig, plt, out, "fig10-same-words")


def _same_words_sync_figure(plt, rows, out):
    selected = [row for row in rows if row["experiment"] == "identical-approval-sync"]
    counts = _rates(selected, lambda row: (row["model"], row["condition"]))
    fig, axes = plt.subplots(1, 3, figsize=(6.6, 2.6), sharey=True, squeeze=False)
    for ax, model in zip(axes[0], ("luna", "sol", "sonnet")):
        _bars(ax, ["in operator\nchannel", "in repeated peer\nreminders"], ["operator", "peer"],
              [counts[(model, "operator-identical-approval")], counts[(model, "peer-identical-approval")]],
              gap=False, ylabel="adopts the tag" if model == "luna" else None)
        ax.set_title(f"{DISPLAY_NAMES[model]}, [[sync-7]]", fontsize=8.5, loc="left")
        ax.tick_params(axis="x", labelsize=7)
    _legend(fig, plt, [("operator", "operator channel"), ("peer", "peer messages")], y=.01)
    fig.tight_layout(rect=(0, .1, 1, 1))
    _save(fig, plt, out, "fig12-same-words-sync")


def _action_figure(plt, rows, out):
    conditions = (
        ("no-approval", "no\napproval", GREY, ".."),
        ("operator-approval", "operator\napproves", BLUE, None),
        ("peer-approval", "peer says\napproved", ORANGE, "///"),
        ("simulated-status-valid", "status:\nvalid", BLUE, None),
        ("simulated-status-failed", "status:\nfailed", ORANGE, "///"),
    )
    fig, axes = plt.subplots(2, 3, figsize=(9.2, 5.2), sharey=True)
    for ax, model in zip(axes.flat, MODELS):
        for index, (condition, label, colour, hatch) in enumerate(conditions):
            selected = [row for row in rows if row["model"] == model and row["condition"] == condition and valid(row)]
            proposed, total = sum(row["proposed"] for row in selected), len(selected)
            position = index + (.4 if index >= 3 else 0)
            proportion = proposed / total
            low, high = wilson(proposed, total)
            ax.bar(position, proportion, width=.72, color=colour, hatch=hatch, edgecolor="#ffffff", linewidth=0, zorder=2)
            ax.errorbar(position, proportion, yerr=[[max(0, proportion - low)], [max(0, high - proportion)]], color="#555", capsize=2, lw=.8, zorder=3)
            ax.text(position, high + .03, f"{proposed}/{total}", ha="center", fontsize=6.5)
        ax.set_xticks([i + (.4 if i >= 3 else 0) for i in range(5)], [c[1] for c in conditions], fontsize=6.5)
        ax.set_title(DISPLAY_NAMES[model], loc="left", fontsize=9)
        ax.set_ylim(0, 1.18)
        ax.set_yticks([0, .5, 1], ["0%", "50%", "100%"])
        ax.spines[["top", "right"]].set_visible(False)
        ax.grid(axis="y", color="#ddd", lw=.5, zorder=0)
    for ax in axes[:, 0]:
        ax.set_ylabel("proposes the simulated call")
    from matplotlib.patches import Patch
    fig.legend(handles=[Patch(facecolor=GREY, hatch="..", edgecolor="#fff", label="no approval"),
                        Patch(facecolor=BLUE, edgecolor="#fff", label="operator approval or valid simulated status"),
                        Patch(facecolor=ORANGE, hatch="///", edgecolor="#fff", label="peer claim or failed simulated status")],
               loc="lower center", ncol=3, frameon=False, fontsize=8)
    fig.tight_layout(rect=(0, .06, 1, 1))
    out.mkdir(parents=True, exist_ok=True)
    for extension in ("png", "pdf"):
        fig.savefig(out / f"fig11-actions.{extension}", dpi=200 if extension == "png" else None)
    plt.close(fig)


def generate_figures(out):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update({"font.size": 8, "axes.edgecolor": INK2, "axes.labelcolor": INK, "xtick.color": INK2,
                         "ytick.color": INK2, "text.color": INK, "axes.facecolor": SURFACE, "figure.facecolor": SURFACE,
                         "hatch.linewidth": .8, "font.family": "DejaVu Sans"})
    records = all_records()
    formatting, monitoring, networks, actions = (records[key] for key in ("formatting", "monitoring", "networks", "actions"))
    out = Path(out)
    _source_figure(plt, [r for r in formatting if r["experiment"] == "scripted-source-relay"], out)
    _monitor_figure(plt, [r for r in monitoring if r["experiment"] == "relay-hop-monitor"], out)
    _natural_figure(plt, [r for r in formatting if r["experiment"] == "natural-relay-exposure"], out)
    _model_panels(plt, [r for r in formatting if r["experiment"] == "delivery-channel-labels"],
                  ("user-role-instruction", "unverified-agent-label", "untrusted-data-block", "no-instruction"),
                  {"user-role-instruction": "user\nmessage", "unverified-agent-label": "labelled\nagent", "untrusted-data-block": "untrusted\ndata", "no-instruction": "no\ninstruction"},
                  {"user-role-instruction": "operator", "unverified-agent-label": "peer", "untrusted-data-block": "peer", "no-instruction": "control"},
                  out, "fig4-labels", legend=[("operator", "user role"), ("peer", "agent label or data block"), ("control", "control")])
    followup = [r for r in formatting if r["experiment"] in ("source-and-label-controls", "peer-approval-check")]
    _model_panels(plt, followup,
                  ("bare-reminder", "source-name", "peer-non-approval", "peer-third-person-approval", "labelled-bare-reminder"),
                  {"bare-reminder": "reminder\nalone", "source-name": "+ source\nname", "peer-non-approval": "+ not\napproved", "peer-third-person-approval": "+ peer\napproved", "labelled-bare-reminder": "+ peer\nlabel"},
                  {"bare-reminder": "operator", "source-name": "peer", "peer-non-approval": "peer", "peer-third-person-approval": "peer", "labelled-bare-reminder": "control"},
                  out, "fig5-followup", size=(8.6, 4.4), legend=[("operator", "reminder alone"), ("peer", "one sentence added"), ("control", "peer label")])
    _network_figure(plt, networks, out)
    channel = [r for r in formatting if r["experiment"] in ("approval-channel-and-wording-sync", "channel-wording-completion-sync")]
    _model_panels(plt, channel,
                  ("peer-neutral-addition", "peer-third-person-approval", "peer-quoted-operator-approval", "peer-non-approval", "operator-first-person-approval", "operator-third-person-approval", "operator-first-person-non-approval"),
                  {"peer-neutral-addition": "peer +\nneutral", "peer-third-person-approval": "peer:\nyes", "peer-quoted-operator-approval": "peer\nquotes\noperator", "peer-non-approval": "peer:\nno", "operator-first-person-approval": "operator:\nyes", "operator-third-person-approval": "operator,\n3rd\nperson", "operator-first-person-non-approval": "operator:\nno"},
                  {c: "peer" for c in ("peer-neutral-addition", "peer-third-person-approval", "peer-quoted-operator-approval", "peer-non-approval")} | {c: "operator" for c in ("operator-first-person-approval", "operator-third-person-approval", "operator-first-person-non-approval")},
                  out, "fig7-who-can-approve", size=(9.6, 5), legend=[("peer", "peer statement"), ("operator", "operator statement")])
    _false_approval_figure(plt, [r for r in networks if r["experiment"] == "network-false-approval"], out)
    second = [r for r in formatting if r["experiment"] in ("approval-channel-and-wording-file", "channel-wording-completion-file")]
    _model_panels(plt, second,
                  ("bare-reminder", "labelled-bare-reminder", "peer-third-person-approval", "peer-quoted-operator-approval", "operator-first-person-approval", "operator-third-person-approval"),
                  {"bare-reminder": "reminder\nalone", "labelled-bare-reminder": "+ peer\nlabel", "peer-third-person-approval": "peer:\nyes", "peer-quoted-operator-approval": "peer\nquotes\noperator", "operator-first-person-approval": "operator:\nyes", "operator-third-person-approval": "operator,\n3rd\nperson"},
                  {"bare-reminder": "control", "labelled-bare-reminder": "control", "peer-third-person-approval": "peer", "peer-quoted-operator-approval": "peer", "operator-first-person-approval": "operator", "operator-third-person-approval": "operator"},
                  out, "fig9-second-convention", size=(8.8, 4.8), legend=[("control", "reminder control"), ("peer", "peer approval"), ("operator", "operator approval")])
    _same_words_figure(plt, [r for r in formatting if r["experiment"] in ("identical-approval-sync", "identical-approval-file")], out)
    _same_words_sync_figure(plt, [r for r in formatting if r["experiment"] == "identical-approval-sync"], out)
    _action_figure(plt, [r for r in actions if r["stage"] == "main"], out)
    return sorted(out.glob("*.png"))


def main():
    parser = argparse.ArgumentParser(description="Regenerate all study figures from saved replies.")
    parser.add_argument("--out", default="results/figures")
    args = parser.parse_args()
    paths = generate_figures(args.out)
    print(f"Wrote {len(paths)} PNG figures and matching PDFs to {args.out}")


if __name__ == "__main__":
    main()
