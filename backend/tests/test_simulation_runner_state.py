import json

from app.services.simulation_runner import RunnerStatus, SimulationRunner, SimulationRunState


def test_get_run_state_refreshes_disk_state_over_stale_memory(tmp_path, monkeypatch):
    simulations_dir = tmp_path / "uploads" / "simulations"
    monkeypatch.setattr(SimulationRunner, "RUN_STATE_DIR", str(simulations_dir))
    SimulationRunner._run_states.clear()

    simulation_id = "sim_refresh"
    SimulationRunner._run_states[simulation_id] = SimulationRunState(
        simulation_id=simulation_id,
        runner_status=RunnerStatus.RUNNING,
        current_round=0,
        total_rounds=1,
    )

    sim_dir = simulations_dir / simulation_id
    sim_dir.mkdir(parents=True)
    (sim_dir / "run_state.json").write_text(
        json.dumps(
            {
                "simulation_id": simulation_id,
                "runner_status": "completed",
                "current_round": 1,
                "total_rounds": 1,
                "progress_percent": 100.0,
                "reddit_completed": True,
                "reddit_current_round": 1,
                "completed_at": "2026-05-18T07:55:18",
            }
        ),
        encoding="utf-8",
    )

    state = SimulationRunner.get_run_state(simulation_id)

    assert state is not None
    assert state.runner_status == RunnerStatus.COMPLETED
    assert state.current_round == 1
    assert SimulationRunner._run_states[simulation_id].runner_status == RunnerStatus.COMPLETED
