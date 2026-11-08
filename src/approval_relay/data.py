import hashlib
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = Path(os.environ.get("APPROVAL_RELAY_DATA", ROOT / "data"))
RECORDS = DATA / "records"
SCENARIOS = DATA / "scenarios"
PROMPTS = DATA / "prompts"

MODELS = ("luna", "sol", "haiku", "sonnet", "deepseek", "gemini")
DISPLAY_NAMES = {
    "luna": "GPT-6 Luna",
    "sol": "GPT-6.1 Sol",
    "haiku": "Claude Haiku 5.5",
    "sonnet": "Claude Sonnet 5.5",
    "deepseek": "DeepSeek V4.1 Flash",
    "gemini": "Gemini 3.5 Flash Lite",
}
FORMATTING_MODELS = ("luna", "sol", "sonnet")
STORIES = ("garden", "fair", "books", "gen01")


def read_json(path):
    with Path(path).open() as f:
        return json.load(f)


def read_jsonl(path):
    rows = []
    with Path(path).open() as f:
        for line_number, line in enumerate(f, 1):
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON at {path}:{line_number}") from exc
    return rows


def write_jsonl(path, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")


def append_jsonl(path, row):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as f:
        f.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")


def records(relative_path):
    return read_jsonl(RECORDS / relative_path)


def record_group(group):
    rows = []
    for path in sorted((RECORDS / group).glob("*.jsonl")):
        rows.extend(read_jsonl(path))
    return rows


def all_records():
    return {group: record_group(group) for group in ("formatting", "networks", "monitoring", "actions")}


def formatting_stories():
    return read_json(SCENARIOS / "formatting-stories.json")


def action_scenarios():
    return read_json(SCENARIOS / "action-scenarios.json")


def prompt_dataset(name):
    return read_json(PROMPTS / name)


def model_config():
    return read_json(ROOT / "models.json")


def valid(row):
    return not row.get("empty") and not row.get("error")


def verify_manifest():
    manifest = read_json(DATA / "manifest.json")
    mismatches = []
    items = manifest["public_record_files"] + manifest.get("auxiliary_data_files", [])
    for item in items:
        path = ROOT / item["path"]
        if not path.is_file():
            mismatches.append({"path": item["path"], "problem": "missing"})
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if "rows" in item:
            rows = read_jsonl(path)
            if len(rows) != item["rows"]:
                mismatches.append({"path": item["path"], "problem": f"row count {len(rows)} != {item['rows']}"})
        if digest != item["sha256"]:
            mismatches.append({"path": item["path"], "problem": "SHA-256 mismatch"})
    return mismatches
