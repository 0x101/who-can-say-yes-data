import pytest

from approval_relay.actions import scenario_problems
from approval_relay.data import action_scenarios, all_records
from approval_relay.results import build_summary


@pytest.fixture(scope="session")
def summary():
    return build_summary()


def test_manifest_and_record_totals(summary):
    assert summary["manifest_mismatches"] == []
    groups = all_records()
    assert {name: len(rows) for name, rows in groups.items()} == {
        "formatting": 2573, "networks": 104, "monitoring": 416, "actions": 3696,
    }


def test_all_preregistered_verdicts(summary):
    result = summary["preregistered"]
    assert result["summary"] == {"total": 45, "met": 32, "not_met": 13, "not_estimable": 0}
    assert {row["original_id"] for row in result["criteria"] if row["status"] == "not met"} == {
        "2", "3", "F1", "G1", "F2b", "H1", "X5a", "X7b", "N2a", "Ra", "Rc", "Ua", "Ub",
    }
    assert result["pilot_gate"]["pilot-initial"]["passed"] is False
    assert result["pilot_gate"]["pilot-revised"]["passed"] is True


def test_identical_sentence_table(summary):
    expected = {
        "luna": (12, 12, 6, 12, 12, 12, 1, 12),
        "sol": (12, 12, 1, 12, 12, 12, 1, 12),
        "sonnet": (11, 11, 0, 9, 11, 11, 0, 7),
    }
    for row in summary["formatting_table"]:
        values = expected[row["model"]]
        actual = (
            row["sync_operator"]["adopted"], row["sync_operator"]["valid"],
            row["sync_peer"]["adopted"], row["sync_peer"]["valid"],
            row["file_operator"]["adopted"], row["file_operator"]["valid"],
            row["file_peer"]["adopted"], row["file_peer"]["valid"],
        )
        assert actual == values
    sonnet = next(row for row in summary["formatting_table"] if row["model"] == "sonnet")
    assert sonnet["file_peer"]["estimable"] is False


def test_action_table_and_clustered_tests(summary):
    expected = {
        "luna": (0, 37, 38, 6, 6, 1),
        "sol": (0, 35, 1, 18, 0, 7.62939453125e-06),
        "haiku": (12, 36, 0, 19, 0, 3.814697265625e-06),
        "sonnet": (3, 48, 0, 24, 0, 1.1920928955078125e-07),
        "deepseek": (8, 41, 16, 15, 0, 0.00006103515625),
        "gemini": (43, 47, 48, 0, 1, 1),
    }
    for row in summary["action_table"]:
        none = row["conditions"]["no-approval"]["proposed"]
        operator = row["conditions"]["operator-approval"]["proposed"]
        peer = row["conditions"]["peer-approval"]["proposed"]
        comparison = row["scenario_comparison"]
        actual = (none, operator, peer, comparison["operator_wins"], comparison["peer_wins"], comparison["sign_test_p"])
        assert actual == pytest.approx(expected[row["model"]])
        assert row["conditions"]["operator-non-approval"] == {"proposed": 0, "valid": 48}
        assert row["conditions"]["simulated-status-failed"] == {"proposed": 0, "valid": 48}
        assert all(value["valid"] == 48 for value in row["conditions"].values())
    assert sum(row["conditions"]["simulated-status-failed"]["proposed"] for row in summary["action_table"]) == 0


def test_independent_rescoring(summary):
    assert summary["independent_rescore"] == {
        "formatting": {"checked": 2514, "mismatches": 0},
        "actions": {"checked": 3696, "mismatches": 0, "main_parseable": 3453},
        "network_updates": {"checked": 6864, "mismatches": 0},
    }


def test_natural_labels_and_monitor_posthoc(summary):
    labels = summary["natural_hand_labels"]
    assert labels["relays"] == 39
    assert labels["counts"]["names_who_asked"] == {"all": 2, "first-hop": 0, "second-hop": 2}
    assert labels["counts"]["asks_reader_to_use_tag"] == {"all": 28, "first-hop": 22, "second-hop": 6}
    assert labels["agreement_fields"] == labels["total_fields"] == 195
    assert "not a blind independent replication" in labels["independence_note"]
    assert summary["natural_model_coder_agreement"] == {"agree": 12, "double_coded": 20}
    monitors = summary["monitor_posthoc"]
    assert monitors["haiku"]["counts"]["requests-tag"] == [5, 8]
    assert monitors["haiku"]["counts"]["tag-only"] == [0, 30]
    assert monitors["sonnet"]["counts"]["requests-tag"] == [7, 8]
    assert monitors["sonnet"]["counts"]["tag-only"] == [0, 32]


def test_network_intervals(summary):
    criteria = {row["original_id"]: row for row in summary["preregistered"]["criteria"]}
    assert criteria["F1"]["details"]["difference"] == pytest.approx(-.05)
    assert criteria["F1"]["details"]["interval"] == pytest.approx([-.18333333333333332, .08333333333333331])
    assert criteria["F2b"]["details"]["interval"] == pytest.approx([-.30000000000000004, 0])
    assert criteria["X4b"]["details"]["interval"] == pytest.approx([-.18333333333333332, -.016666666666666666])
    assert criteria["X7b"]["details"]["interval"] == pytest.approx([-.2, .03333333333333334])


def test_costs_and_scenarios(summary):
    costs = summary["logged_costs"]
    assert costs["groups"]["main-experiments"]["all"]["calls"] == 9967
    assert costs["groups"]["main-experiments"]["all"]["list_cost"] == pytest.approx(6.006268925)
    assert costs["groups"]["simulated-actions"]["all"]["list_cost"] == pytest.approx(4.93388588)
    assert costs["groups"]["scenario-generation"]["all"]["list_cost"] == pytest.approx(.34210260)
    assert costs["unmeasured_reservation_total_usd"] == pytest.approx(2.85)
    assert summary["action_scenarios"] == {
        "total": 28, "main": 24, "pilot": 4, "generator": ["adaption:glm-5.2"],
    }
    assert all(not scenario_problems(row) for row in action_scenarios())
