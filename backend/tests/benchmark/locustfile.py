"""SPEC-P2-012 Locust pressure script for high-frequency API endpoints."""

from __future__ import annotations

from locust import HttpUser, between, events, task

P99_TARGET_MS = 500


def _mark_server_error(response):
    if response.status_code >= 500:
        response.failure(f"server error: {response.status_code}")


@events.quitting.add_listener
def enforce_p99_target(environment, **_kwargs):
    percentile = environment.stats.total.get_response_time_percentile(0.99)
    if percentile and percentile > P99_TARGET_MS:
        environment.process_exit_code = 1


class MiroConsumerApiUser(HttpUser):
    wait_time = between(0.1, 0.5)

    @task
    def health(self):
        with self.client.get("/health", catch_response=True, name="GET /health") as response:
            _mark_server_error(response)

    @task
    def ready(self):
        with self.client.get("/ready", catch_response=True, name="GET /ready") as response:
            _mark_server_error(response)

    @task
    def create_concept_test(self):
        payload = {
            "task_type": "concept_test",
            "product_concept_assets": ["Protein breakfast pouch"],
            "research_goal": "Pressure test concept creation",
        }
        with self.client.post(
            "/api/v1/consumer/concept-tests",
            json=payload,
            catch_response=True,
            name="POST /api/v1/consumer/concept-tests",
        ) as response:
            _mark_server_error(response)

    @task
    def start_simulation(self):
        with self.client.post(
            "/api/v1/simulation/start",
            json={"simulation_id": "load_sim", "force_restart": False},
            catch_response=True,
            name="POST /api/v1/simulation/start",
        ) as response:
            _mark_server_error(response)

    @task
    def generate_report(self):
        with self.client.post(
            "/api/v1/report/generate",
            json={"simulation_id": "load_sim", "force_regenerate": False},
            catch_response=True,
            name="POST /api/v1/report/generate",
        ) as response:
            _mark_server_error(response)

    @task
    def report_status(self):
        with self.client.post(
            "/api/v1/report/generate/status",
            json={"task_id": "load_task"},
            catch_response=True,
            name="POST /api/v1/report/generate/status",
        ) as response:
            _mark_server_error(response)

    @task
    def list_comparisons(self):
        with self.client.get(
            "/api/v1/consumer/comparisons",
            catch_response=True,
            name="GET /api/v1/consumer/comparisons",
        ) as response:
            _mark_server_error(response)

    @task
    def list_research_assets(self):
        with self.client.get(
            "/api/v1/consumer/research-assets",
            catch_response=True,
            name="GET /api/v1/consumer/research-assets",
        ) as response:
            _mark_server_error(response)

    @task
    def current_user(self):
        with self.client.get("/api/v1/auth/me", catch_response=True, name="GET /api/v1/auth/me") as response:
            _mark_server_error(response)

    @task
    def version(self):
        with self.client.get("/api/version", catch_response=True, name="GET /api/version") as response:
            _mark_server_error(response)
