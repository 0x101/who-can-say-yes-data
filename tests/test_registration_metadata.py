import re

from approval_relay.data import ROOT, read_json
from approval_relay.results import build_summary


def test_registration_metadata_matches_all_criteria():
    document = read_json(ROOT / "data" / "preregistration.json")
    metadata = {item["id"]: item for item in document["criteria"]}
    summary = build_summary()["preregistered"]
    assert len(metadata) == 45
    for criterion in summary["criteria"]:
        item = metadata[criterion["original_id"]]
        assert item["experiment"] == criterion["experiment"]
        assert item["description"] == criterion["description"]
        assert item["status"] == criterion["status"]
        assert re.fullmatch(r"[0-9a-f]{7,40}", item["registration_commit"])
