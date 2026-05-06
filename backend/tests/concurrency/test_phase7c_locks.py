"""Phase7F CI path compatibility tests for Phase7C concurrency locks."""

import pytest

from app.contracts.errors import ConcurrencyConflictError
from app.services.application.concurrency import (
    branch_fork_lock,
    FileLockManager,
    lock_key,
    report_generation_lock,
    simulation_run_lock,
)


class TestLockConstants:
    """Verify lock constant values are stable and distinct."""

    def test_simulation_run_lock_is_string(self):
        assert isinstance(simulation_run_lock, str)
        assert simulation_run_lock == "simulation_run_lock"

    def test_branch_fork_lock_is_string(self):
        assert isinstance(branch_fork_lock, str)
        assert branch_fork_lock == "branch_fork_lock"

    def test_report_generation_lock_is_string(self):
        assert isinstance(report_generation_lock, str)
        assert report_generation_lock == "report_generation_lock"

    def test_all_lock_constants_are_distinct(self):
        locks = {simulation_run_lock, branch_fork_lock, report_generation_lock}
        assert len(locks) == 3


class TestLockKeyDeterministic:
    """Verify lock_key produces stable, deterministic hashes."""

    def test_returns_positive_int(self):
        key = lock_key(simulation_run_lock, "sim_42")
        assert isinstance(key, int)
        assert key > 0

    def test_same_input_same_output(self):
        k1 = lock_key(simulation_run_lock, "sim_42")
        k2 = lock_key(simulation_run_lock, "sim_42")
        assert k1 == k2

    def test_different_resource_ids_differ(self):
        k1 = lock_key(simulation_run_lock, "sim_42")
        k2 = lock_key(simulation_run_lock, "sim_99")
        assert k1 != k2

    def test_different_lock_types_differ(self):
        k1 = lock_key(simulation_run_lock, "sim_42")
        k2 = lock_key(branch_fork_lock, "sim_42")
        assert k1 != k2

    def test_all_three_locks_produce_different_keys_for_same_id(self):
        k1 = lock_key(simulation_run_lock, "r1")
        k2 = lock_key(branch_fork_lock, "r1")
        k3 = lock_key(report_generation_lock, "r1")
        assert k1 != k2
        assert k2 != k3
        assert k1 != k3


class TestFileLockManagerConflict:
    """Verify FileLockManager raises ConcurrencyConflictError on conflicts."""

    def test_acquire_succeeds_when_no_conflict(self, tmp_path):
        lock_dir = tmp_path / "locks"
        mgr = FileLockManager(lock_dir=str(lock_dir))
        with mgr.acquire(simulation_run_lock, "sim_1", timeout_seconds=0):
            pass

    def test_second_acquire_same_resource_raises(self, tmp_path):
        lock_dir = tmp_path / "locks"
        mgr = FileLockManager(lock_dir=str(lock_dir))
        with mgr.acquire(simulation_run_lock, "sim_1", timeout_seconds=0):
            with pytest.raises(ConcurrencyConflictError) as exc_info:
                with mgr.acquire(simulation_run_lock, "sim_1", timeout_seconds=0):
                    pass
            assert exc_info.value.to_response()["reason"] == "lock_timeout"

    def test_different_resources_do_not_conflict(self, tmp_path):
        lock_dir = tmp_path / "locks"
        mgr = FileLockManager(lock_dir=str(lock_dir))
        with mgr.acquire(simulation_run_lock, "sim_1", timeout_seconds=0):
            with mgr.acquire(simulation_run_lock, "sim_2", timeout_seconds=0):
                pass

    def test_different_lock_types_do_not_conflict(self, tmp_path):
        lock_dir = tmp_path / "locks"
        mgr = FileLockManager(lock_dir=str(lock_dir))
        with mgr.acquire(simulation_run_lock, "res_1", timeout_seconds=0):
            with mgr.acquire(branch_fork_lock, "res_1", timeout_seconds=0):
                pass

    def test_lock_file_is_created_under_lock_dir(self, tmp_path):
        lock_dir = tmp_path / "locks"
        mgr = FileLockManager(lock_dir=str(lock_dir))
        with mgr.acquire(simulation_run_lock, "sim_1", timeout_seconds=0):
            lock_files = list(lock_dir.iterdir())
            assert len(lock_files) == 1
            assert lock_files[0].suffix == ".lock"

    def test_conflict_response_shape(self, tmp_path):
        lock_dir = tmp_path / "locks"
        mgr = FileLockManager(lock_dir=str(lock_dir))
        with mgr.acquire(branch_fork_lock, "branch_1", timeout_seconds=0):
            with pytest.raises(ConcurrencyConflictError) as exc_info:
                with mgr.acquire(branch_fork_lock, "branch_1", timeout_seconds=0):
                    pass
            response = exc_info.value.to_response()
            assert response == {
                "error": "conflict",
                "resource": branch_fork_lock,
                "resource_id": "branch_1",
                "reason": "lock_timeout",
            }

    def test_in_process_deduplication_rejects_double_acquire(self, tmp_path):
        lock_dir = tmp_path / "locks"
        mgr = FileLockManager(lock_dir=str(lock_dir))
        with pytest.raises(ConcurrencyConflictError):
            with mgr.acquire(report_generation_lock, "report_1", timeout_seconds=0):
                with mgr.acquire(report_generation_lock, "report_1", timeout_seconds=0):
                    pass
