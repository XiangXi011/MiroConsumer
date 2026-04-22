from pathlib import Path

from app.services.consumer.benchmark_registry import (
    _benchmarks_dir,
    register_benchmark,
    list_benchmarks,
    get_benchmark,
    delete_benchmark,
)


def test_register_benchmark_creates_manifest_and_expected_signals(tmp_path):
    root = str(tmp_path / "uploads")
    expected_signals = {
        "acceptance_band": "positive_lean",
        "top_resonance_labels": ["breakfast yogurt pouch"],
        "top_risk_labels": ["sweetener debate"],
        "misread_present": True,
        "clarification_recovery_present": False,
        "cascade_band": "contained",
    }
    benchmark = register_benchmark(
        name="Breakfast Yogurt Concept v1",
        source_pack_lineage="asset_pack_001",
        expected_signals=expected_signals,
        simulation_context={"requirement": "test yogurt concept"},
        upload_root=root,
    )

    assert "benchmark_id" in benchmark
    assert benchmark["name"] == "Breakfast Yogurt Concept v1"
    assert benchmark["source_pack_lineage"] == "asset_pack_001"
    assert benchmark["simulation_context"] == {"requirement": "test yogurt concept"}

    # Manifest persisted
    bench_dir = _benchmarks_dir(root)
    manifest_path = bench_dir / benchmark["benchmark_id"] / "benchmark_manifest.json"
    assert manifest_path.exists()

    # Expected signals persisted
    signals_path = bench_dir / benchmark["benchmark_id"] / "expected_signals.json"
    assert signals_path.exists()


def test_list_benchmarks_returns_registered_items(tmp_path):
    root = str(tmp_path / "uploads")
    register_benchmark(
        name="Bench A",
        source_pack_lineage="pack_a",
        expected_signals={"acceptance_band": "mixed"},
        upload_root=root,
    )
    register_benchmark(
        name="Bench B",
        source_pack_lineage="pack_b",
        expected_signals={"acceptance_band": "negative_lean"},
        upload_root=root,
    )

    items = list_benchmarks(upload_root=root)
    assert len(items) == 2
    names = {b["name"] for b in items}
    assert names == {"Bench A", "Bench B"}


def test_get_benchmark_returns_data(tmp_path):
    root = str(tmp_path / "uploads")
    benchmark = register_benchmark(
        name="Bench Get",
        source_pack_lineage="pack_get",
        expected_signals={"acceptance_band": "positive_lean"},
        upload_root=root,
    )

    fetched = get_benchmark(benchmark["benchmark_id"], upload_root=root)
    assert fetched is not None
    assert fetched["benchmark_id"] == benchmark["benchmark_id"]
    assert fetched["name"] == "Bench Get"
    assert fetched["expected_signals"]["acceptance_band"] == "positive_lean"


def test_get_benchmark_missing_returns_none(tmp_path):
    root = str(tmp_path / "uploads")
    assert get_benchmark("bench_missing", upload_root=root) is None


def test_delete_benchmark_removes_files(tmp_path):
    root = str(tmp_path / "uploads")
    benchmark = register_benchmark(
        name="Bench Del",
        source_pack_lineage="pack_del",
        expected_signals={"acceptance_band": "contained"},
        upload_root=root,
    )

    assert delete_benchmark(benchmark["benchmark_id"], upload_root=root) is True
    assert get_benchmark(benchmark["benchmark_id"], upload_root=root) is None


def test_delete_benchmark_missing_returns_false(tmp_path):
    root = str(tmp_path / "uploads")
    assert delete_benchmark("bench_noexist", upload_root=root) is False


def test_register_benchmark_without_optional_context(tmp_path):
    root = str(tmp_path / "uploads")
    benchmark = register_benchmark(
        name="Minimal Bench",
        source_pack_lineage="pack_min",
        expected_signals={"acceptance_band": "mixed"},
        upload_root=root,
    )

    assert benchmark["simulation_context"] == {}
    fetched = get_benchmark(benchmark["benchmark_id"], upload_root=root)
    assert fetched["simulation_context"] == {}
