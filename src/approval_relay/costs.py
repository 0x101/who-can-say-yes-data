from collections import defaultdict

from .data import DATA, model_config, read_json, read_jsonl


def logged_costs():
    config = model_config()
    prices = {
        settings["model_id"]: (
            settings["input_usd_per_million_tokens"], settings["output_usd_per_million_tokens"],
        )
        for settings in config.values()
    }
    totals = defaultdict(lambda: {"calls": 0, "input_tokens": 0, "output_tokens": 0, "list_cost": 0.0})
    for name in ("main-experiment-calls.jsonl", "action-and-generation-calls.jsonl"):
        for row in read_jsonl(DATA / "costs" / name):
            if row["model_id"] not in prices:
                raise ValueError(f"No recorded price for {row['model_id']}")
            input_price, output_price = prices[row["model_id"]]
            cost = (
                row["input_tokens"] / 1e6 * input_price + row["output_tokens"] / 1e6 * output_price
            ) * (0.5 if row["batch"] else 1.0)
            for key in ((row["group"], row["provider"]), (row["group"], "all")):
                item = totals[key]
                item["calls"] += 1
                item["input_tokens"] += row["input_tokens"]
                item["output_tokens"] += row["output_tokens"]
                item["list_cost"] += cost
    grouped = defaultdict(dict)
    for (group, provider), values in totals.items():
        grouped[group][provider] = values
    disclosure = read_json(DATA / "costs" / "disclosure.json")
    return {
        "groups": dict(grouped),
        "unmeasured_reservation_holds_usd": disclosure["unmeasured_reservation_holds_usd"],
        "unmeasured_reservation_total_usd": sum(
            item["amount"] for item in disclosure["unmeasured_reservation_holds_usd"]
        ),
        "method": disclosure["method"],
        "price_date": disclosure["price_date"],
    }
