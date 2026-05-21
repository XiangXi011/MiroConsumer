"""Tests for simulation_ipc core logic."""

from __future__ import annotations

import json
import os
from datetime import datetime
from unittest.mock import patch

import pytest

from app.services.simulation_ipc import (
    CommandStatus,
    CommandType,
    IPCCommand,
    IPCResponse,
    SimulationIPCClient,
    SimulationIPCServer,
)


class TestCommandType:
    """Test CommandType enum."""

    def test_values(self):
        """CommandType has expected values."""
        assert CommandType.INTERVIEW == "interview"
        assert CommandType.BATCH_INTERVIEW == "batch_interview"
        assert CommandType.CLOSE_ENV == "close_env"


class TestCommandStatus:
    """Test CommandStatus enum."""

    def test_values(self):
        """CommandStatus has expected values."""
        assert CommandStatus.PENDING == "pending"
        assert CommandStatus.PROCESSING == "processing"
        assert CommandStatus.COMPLETED == "completed"
        assert CommandStatus.FAILED == "failed"


class TestIPCCommand:
    """Test IPCCommand dataclass."""

    def test_creation(self):
        """IPCCommand can be created."""
        cmd = IPCCommand(
            command_id="cmd_123",
            command_type=CommandType.INTERVIEW,
            args={"agent_id": 0, "prompt": "test"},
        )
        assert cmd.command_id == "cmd_123"
        assert cmd.command_type == CommandType.INTERVIEW
        assert cmd.args == {"agent_id": 0, "prompt": "test"}

    def test_to_dict(self):
        """IPCCommand serializes to dict correctly."""
        cmd = IPCCommand(
            command_id="cmd_1",
            command_type=CommandType.BATCH_INTERVIEW,
            args={"interviews": []},
        )
        d = cmd.to_dict()
        assert d["command_id"] == "cmd_1"
        assert d["command_type"] == "batch_interview"
        assert d["args"] == {"interviews": []}

    def test_from_dict(self):
        """IPCCommand deserializes from dict correctly."""
        d = {
            "command_id": "cmd_2",
            "command_type": "close_env",
            "args": {},
            "timestamp": "2024-01-01T00:00:00",
        }
        cmd = IPCCommand.from_dict(d)
        assert cmd.command_id == "cmd_2"
        assert cmd.command_type == CommandType.CLOSE_ENV
        assert cmd.args == {}

    def test_round_trip(self):
        """IPCCommand survives to_dict -> from_dict round-trip."""
        original = IPCCommand(
            command_id="cmd_rt",
            command_type=CommandType.INTERVIEW,
            args={"key": "value"},
            timestamp="2024-01-01T00:00:00",
        )
        d = original.to_dict()
        restored = IPCCommand.from_dict(d)
        assert restored.command_id == original.command_id
        assert restored.command_type == original.command_type
        assert restored.args == original.args


class TestIPCResponse:
    """Test IPCResponse dataclass."""

    def test_creation(self):
        """IPCResponse can be created."""
        resp = IPCResponse(
            command_id="cmd_1",
            status=CommandStatus.COMPLETED,
            result={"answer": "test"},
        )
        assert resp.command_id == "cmd_1"
        assert resp.status == CommandStatus.COMPLETED
        assert resp.result == {"answer": "test"}
        assert resp.error is None

    def test_to_dict(self):
        """IPCResponse serializes to dict correctly."""
        resp = IPCResponse(
            command_id="cmd_1",
            status=CommandStatus.FAILED,
            error="timeout",
        )
        d = resp.to_dict()
        assert d["command_id"] == "cmd_1"
        assert d["status"] == "failed"
        assert d["error"] == "timeout"
        assert d["result"] is None

    def test_from_dict(self):
        """IPCResponse deserializes from dict correctly."""
        d = {
            "command_id": "cmd_2",
            "status": "completed",
            "result": {"data": "value"},
            "error": None,
            "timestamp": "2024-01-01T00:00:00",
        }
        resp = IPCResponse.from_dict(d)
        assert resp.command_id == "cmd_2"
        assert resp.status == CommandStatus.COMPLETED
        assert resp.result == {"data": "value"}

    def test_round_trip(self):
        """IPCResponse survives to_dict -> from_dict round-trip."""
        original = IPCResponse(
            command_id="cmd_rt",
            status=CommandStatus.PENDING,
            result={"key": "val"},
            timestamp="2024-01-01T00:00:00",
        )
        d = original.to_dict()
        restored = IPCResponse.from_dict(d)
        assert restored.command_id == original.command_id
        assert restored.status == original.status
        assert restored.result == original.result


class TestSimulationIPCClient:
    """Test SimulationIPCClient."""

    def test_init_creates_directories(self, tmp_path):
        """Client creates command and response directories."""
        client = SimulationIPCClient(str(tmp_path))
        assert os.path.isdir(os.path.join(str(tmp_path), "ipc_commands"))
        assert os.path.isdir(os.path.join(str(tmp_path), "ipc_responses"))

    def test_init_existing_dirs(self, tmp_path):
        """Client works when directories already exist."""
        os.makedirs(os.path.join(str(tmp_path), "ipc_commands"), exist_ok=True)
        os.makedirs(os.path.join(str(tmp_path), "ipc_responses"), exist_ok=True)
        client = SimulationIPCClient(str(tmp_path))
        assert client.simulation_dir == str(tmp_path)

    def test_send_command_timeout(self, tmp_path):
        """send_command raises TimeoutError when no response."""
        client = SimulationIPCClient(str(tmp_path))
        with pytest.raises(TimeoutError):
            client.send_command(
                command_type=CommandType.INTERVIEW,
                args={"agent_id": 0},
                timeout=0.1,
                poll_interval=0.01,
            )

    def test_send_command_success(self, tmp_path):
        """send_command returns response when file appears."""
        client = SimulationIPCClient(str(tmp_path))
        fixed_uuid = "test-uuid-1234"

        with patch("app.services.simulation_ipc.uuid.uuid4") as mock_uuid:
            mock_uuid.return_value = fixed_uuid

            # Pre-write response file
            resp_file = os.path.join(str(tmp_path), "ipc_responses", f"{fixed_uuid}.json")
            os.makedirs(os.path.dirname(resp_file), exist_ok=True)
            resp = IPCResponse(
                command_id=fixed_uuid,
                status=CommandStatus.COMPLETED,
                result={"answer": "yes"},
            )
            with open(resp_file, "w", encoding="utf-8") as f:
                json.dump(resp.to_dict(), f)

            response = client.send_command(
                command_type=CommandType.INTERVIEW,
                args={"agent_id": 0},
                timeout=1.0,
                poll_interval=0.01,
            )
            assert response.status == CommandStatus.COMPLETED
            assert response.result == {"answer": "yes"}

    def test_send_interview(self, tmp_path):
        """send_interview sends correct command."""
        client = SimulationIPCClient(str(tmp_path))
        with pytest.raises(TimeoutError):
            client.send_interview(agent_id=0, prompt="Hello?", timeout=0.01)

    def test_send_batch_interview(self, tmp_path):
        """send_batch_interview sends correct command."""
        client = SimulationIPCClient(str(tmp_path))
        with pytest.raises(TimeoutError):
            client.send_batch_interview(
                interviews=[{"agent_id": 0, "prompt": "Q1"}], timeout=0.01
            )

    def test_send_close_env(self, tmp_path):
        """send_close_env sends correct command."""
        client = SimulationIPCClient(str(tmp_path))
        with pytest.raises(TimeoutError):
            client.send_close_env(timeout=0.01)

    def test_check_env_alive_no_file(self, tmp_path):
        """check_env_alive returns False when no status file."""
        client = SimulationIPCClient(str(tmp_path))
        assert client.check_env_alive() is False

    def test_check_env_alive_true(self, tmp_path):
        """check_env_alive returns True when status is alive."""
        client = SimulationIPCClient(str(tmp_path))
        status_file = os.path.join(str(tmp_path), "env_status.json")
        with open(status_file, "w", encoding="utf-8") as f:
            json.dump({"status": "alive", "timestamp": "2024-01-01T00:00:00"}, f)
        assert client.check_env_alive() is True

    def test_check_env_alive_false(self, tmp_path):
        """check_env_alive returns False when status is not alive."""
        client = SimulationIPCClient(str(tmp_path))
        status_file = os.path.join(str(tmp_path), "env_status.json")
        with open(status_file, "w", encoding="utf-8") as f:
            json.dump({"status": "stopped", "timestamp": "2024-01-01T00:00:00"}, f)
        assert client.check_env_alive() is False


class TestSimulationIPCServer:
    """Test SimulationIPCServer."""

    def test_init_creates_directories(self, tmp_path):
        """Server creates command and response directories."""
        server = SimulationIPCServer(str(tmp_path))
        assert os.path.isdir(os.path.join(str(tmp_path), "ipc_commands"))
        assert os.path.isdir(os.path.join(str(tmp_path), "ipc_responses"))

    def test_start_stop(self, tmp_path):
        """Server start/stop updates env status."""
        server = SimulationIPCServer(str(tmp_path))
        server.start()
        assert server._running is True

        status_file = os.path.join(str(tmp_path), "env_status.json")
        assert os.path.exists(status_file)
        with open(status_file, "r", encoding="utf-8") as f:
            status = json.load(f)
        assert status["status"] == "alive"

        server.stop()
        assert server._running is False
        with open(status_file, "r", encoding="utf-8") as f:
            status = json.load(f)
        assert status["status"] == "stopped"

    def test_poll_commands_empty(self, tmp_path):
        """poll_commands returns None when no commands."""
        server = SimulationIPCServer(str(tmp_path))
        result = server.poll_commands()
        assert result is None

    def test_poll_commands_valid(self, tmp_path):
        """poll_commands returns valid command."""
        server = SimulationIPCServer(str(tmp_path))
        cmd = IPCCommand(
            command_id="cmd_1",
            command_type=CommandType.INTERVIEW,
            args={"agent_id": 0},
        )
        cmd_file = os.path.join(str(tmp_path), "ipc_commands", "cmd_1.json")
        with open(cmd_file, "w", encoding="utf-8") as f:
            json.dump(cmd.to_dict(), f)

        result = server.poll_commands()
        assert result is not None
        assert result.command_id == "cmd_1"
        assert result.command_type == CommandType.INTERVIEW

    def test_send_response(self, tmp_path):
        """send_response writes response file."""
        server = SimulationIPCServer(str(tmp_path))
        resp = IPCResponse(
            command_id="cmd_1",
            status=CommandStatus.COMPLETED,
            result={"answer": "yes"},
        )
        server.send_response(resp)

        resp_file = os.path.join(str(tmp_path), "ipc_responses", "cmd_1.json")
        assert os.path.exists(resp_file)
        with open(resp_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert data["status"] == "completed"

    def test_send_success(self, tmp_path):
        """send_success creates completed response."""
        server = SimulationIPCServer(str(tmp_path))
        server.send_success("cmd_s", {"data": "value"})

        resp_file = os.path.join(str(tmp_path), "ipc_responses", "cmd_s.json")
        with open(resp_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert data["status"] == "completed"
        assert data["result"] == {"data": "value"}

    def test_send_error(self, tmp_path):
        """send_error creates failed response."""
        server = SimulationIPCServer(str(tmp_path))
        server.send_error("cmd_e", "Something failed")

        resp_file = os.path.join(str(tmp_path), "ipc_responses", "cmd_e.json")
        with open(resp_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert data["status"] == "failed"
        assert data["error"] == "Something failed"
