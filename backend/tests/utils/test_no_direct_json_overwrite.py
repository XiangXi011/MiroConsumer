from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCANNED_FILES = [
    ROOT / "app" / "repositories" / "filesystem.py",
    ROOT / "app" / "services" / "simulation_runner.py",
    ROOT / "app" / "services" / "report_agent.py",
    ROOT / "app" / "services" / "report_manager.py",
    ROOT / "app" / "services" / "consumer" / "society" / "state_store.py",
    ROOT / "app" / "services" / "consumer" / "society" / "society_runtime.py",
]


def test_key_json_state_files_do_not_use_direct_overwrite_helpers():
    offenders = []
    for path in SCANNED_FILES:
        lines = path.read_text(encoding="utf-8").splitlines()
        for lineno, line in enumerate(lines, start=1):
            stripped = line.strip()
            if "json.dump(" in stripped:
                offenders.append(f"{path}:{lineno}:{stripped}")
            if ".write_text(json.dumps" in stripped:
                offenders.append(f"{path}:{lineno}:{stripped}")

    assert offenders == []
