from approval_relay.figures import generate_figures


def test_generate_all_figures(tmp_path):
    paths = generate_figures(tmp_path)
    assert len(paths) == 12
    assert {path.name for path in paths} == {
        "fig1-factorial.png", "fig2-monitors.png", "fig3-natural-relays.png", "fig4-labels.png",
        "fig5-followup.png", "fig6-group-run.png", "fig7-who-can-approve.png", "fig8-false-approval.png",
        "fig9-second-convention.png", "fig10-same-words.png", "fig11-actions.png", "fig12-same-words-sync.png",
    }
    for path in paths:
        assert path.stat().st_size > 1000
        assert path.with_suffix(".pdf").stat().st_size > 1000
