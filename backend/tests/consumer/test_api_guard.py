"""Tests for ConsumerApiGuard — the consumer boundary validation module."""

import pytest

from app.services.consumer.api_guard import ConsumerApiGuard


class FakeSimulation:
    def __init__(self, consumer_mode=False, project_type="default"):
        self.consumer_mode = consumer_mode
        self.project_type = project_type


class FakeProject:
    def __init__(self, project_type="default"):
        self.project_type = project_type


def test_check_consumer_simulation_missing():
    ok, error = ConsumerApiGuard.check_consumer_simulation(None)
    assert not ok
    assert "not found" in error.lower()


def test_check_consumer_simulation_non_consumer():
    state = FakeSimulation(consumer_mode=False)
    ok, error = ConsumerApiGuard.check_consumer_simulation(state)
    assert not ok
    assert "consumer_test" in error.lower()


def test_check_consumer_simulation_ok():
    state = FakeSimulation(consumer_mode=True)
    ok, error = ConsumerApiGuard.check_consumer_simulation(state)
    assert ok
    assert error is None


def test_check_consumer_project_missing():
    ok, error = ConsumerApiGuard.check_consumer_project(None)
    assert not ok
    assert "not found" in error.lower()


def test_check_consumer_project_non_consumer():
    project = FakeProject(project_type="default")
    ok, error = ConsumerApiGuard.check_consumer_project(project)
    assert not ok
    assert "consumer_test" in error.lower()


def test_check_consumer_project_ok():
    project = FakeProject(project_type="consumer_test")
    ok, error = ConsumerApiGuard.check_consumer_project(project)
    assert ok
    assert error is None


def test_is_consumer_context_from_state_flag():
    state = FakeSimulation(consumer_mode=True, project_type="default")
    project = FakeProject(project_type="default")
    assert ConsumerApiGuard.is_consumer_context(state=state, project=project)


def test_is_consumer_context_from_project_type():
    state = FakeSimulation(consumer_mode=False, project_type="default")
    project = FakeProject(project_type="consumer_test")
    assert ConsumerApiGuard.is_consumer_context(state=state, project=project)


def test_is_consumer_context_from_state_project_type():
    state = FakeSimulation(consumer_mode=False, project_type="consumer_test")
    assert ConsumerApiGuard.is_consumer_context(state=state)


def test_is_consumer_context_false():
    state = FakeSimulation(consumer_mode=False, project_type="default")
    project = FakeProject(project_type="default")
    assert not ConsumerApiGuard.is_consumer_context(state=state, project=project)


def test_is_consumer_context_no_args():
    assert not ConsumerApiGuard.is_consumer_context()
