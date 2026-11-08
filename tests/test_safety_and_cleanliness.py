import json
from pathlib import Path

import pytest

from approval_relay.data import ROOT, all_records, read_jsonl
from approval_relay.providers import LiveClient


def test_live_client_requires_explicit_caps(tmp_path):
    with pytest.raises(ValueError, match="max-calls"):
        LiveClient(None, 1)
    with pytest.raises(ValueError, match="max-usd"):
        LiveClient(1, None)


def test_no_live_call_can_silently_use_an_unpriced_model(tmp_path):
    client = LiveClient(1, 1, log_path=tmp_path / "calls.jsonl")
    with pytest.raises(ValueError, match="Unknown model"):
        client.complete("not-in-config", [{"role": "user", "content": "hello"}])
    assert client.calls == 0
    assert not (tmp_path / "calls.jsonl").exists()


def test_spending_cap_blocks_before_any_provider_call():
    client = LiveClient(1, 0.000001)
    with pytest.raises(RuntimeError, match="Spending cap"):
        client.complete("luna", [{"role": "user", "content": "hello"}], max_tokens=3000)
    assert client.calls == 0


def test_call_cap_includes_empty_reply_retries():
    client = LiveClient(1, 100)
    client._request = lambda *args: ("", "length", 1, 1)
    with pytest.raises(RuntimeError, match="Call cap"):
        client.complete("luna", [{"role": "user", "content": "hello"}], max_tokens=3000)
    assert client.calls == 1


def test_no_submission_report_or_private_workspace_paths():
    assert not list(ROOT.glob("**/submission*.pdf"))
    assert not list(ROOT.glob("**/submission*.docx"))
    assert not (ROOT / ".env").exists()
    for path in (ROOT / "src").rglob("*.py"):
        text = path.read_text()
        assert "/Users/" not in text
        assert "apart" + "-hackathon" not in text
        assert "swarmlab." not in text
        assert "budget/reservations" not in text


def test_public_records_omit_provider_reasoning():
    for rows in all_records().values():
        for row in rows:
            assert "reasoning" not in row
            assert "api_key" not in row
            assert "messages" not in row


def test_cost_records_contain_no_message_content_or_call_tags():
    expected = {
        "main-experiment-calls.jsonl": 9967,
        "action-and-generation-calls.jsonl": 3743,
    }
    for filename, expected_rows in expected.items():
        path = ROOT / "data" / "costs" / filename
        assert path.is_file(), filename
        assert len(read_jsonl(path)) == expected_rows
    for path in (ROOT / "data" / "costs").glob("*-calls.jsonl"):
        for row in read_jsonl(path):
            assert set(row) == {
                "call_id", "timestamp", "provider", "model_id", "group",
                "input_tokens", "output_tokens", "batch",
            }
            assert len(row["call_id"]) == 64
