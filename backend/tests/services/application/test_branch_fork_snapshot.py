"""Phase 7C branch fork pre-fork snapshot tests."""

import json


def test_branch_fork_snapshot_copies_only_pre_fork_rounds(tmp_path):
    from app.services.application.branch_fork_snapshot import BranchForkSnapshotService

    uploads = tmp_path / "uploads"
    sim_dir = uploads / "simulations" / "sim_1"
    branch_dir = sim_dir / "branches" / "branch_1"
    sim_dir.mkdir(parents=True)
    source = sim_dir / "consumer_rounds.jsonl"
    source.write_text(
        "\n".join(
            json.dumps(row)
            for row in [
                {"round": 0, "event": "first"},
                {"round": 1, "event": "second"},
                {"round": 2, "event": "after fork"},
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    result = BranchForkSnapshotService(upload_folder=str(uploads)).copy_pre_fork_state(
        simulation_id="sim_1",
        branch_id="branch_1",
        fork_round=1,
    )

    assert result["copied_rounds"] == 2
    copied = (branch_dir / "rounds.jsonl").read_text(encoding="utf-8").strip().splitlines()
    assert [json.loads(line)["event"] for line in copied] == ["first", "second"]


def test_branch_fork_snapshot_writes_empty_file_when_base_missing(tmp_path):
    from app.services.application.branch_fork_snapshot import BranchForkSnapshotService

    uploads = tmp_path / "uploads"
    result = BranchForkSnapshotService(upload_folder=str(uploads)).copy_pre_fork_state(
        simulation_id="sim_missing",
        branch_id="branch_1",
        fork_round=3,
    )

    target = uploads / "simulations" / "sim_missing" / "branches" / "branch_1" / "rounds.jsonl"
    assert result["copied_rounds"] == 0
    assert target.exists()
    assert target.read_text(encoding="utf-8") == ""
