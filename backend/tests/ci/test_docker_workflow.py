from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
WORKFLOW = ROOT / ".github" / "workflows" / "docker-image.yml"
TRIVYIGNORE = ROOT / ".trivyignore"


def _workflow_text() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


def test_docker_workflow_scans_local_image_before_push():
    text = _workflow_text()

    build_index = text.index("name: Build local image")
    trivy_index = text.index("aquasecurity/trivy-action@v0.36.0")
    push_index = text.index("name: Push image")

    assert build_index < trivy_index < push_index
    assert "image-ref: miroconsumer:${{ github.sha }}" in text
    assert "load: true" in text
    assert "push: false" in text


def test_docker_workflow_uses_pinned_trivy_action_with_degraded_reporting():
    text = _workflow_text()

    assert "aquasecurity/trivy-action@master" not in text
    assert "aquasecurity/trivy-action@v0.36.0" in text
    assert "severity: 'HIGH,CRITICAL'" in text
    assert "exit-code: '1'" in text
    assert "continue-on-error:" in text
    assert "refs/heads/main" in text
    assert "refs/heads/release/" in text
    assert "format: 'sarif'" in text
    assert "output: 'trivy-results.sarif'" in text
    assert "github/codeql-action/upload-sarif@v3" in text
    assert "actions/upload-artifact@v4" in text
    assert TRIVYIGNORE.exists()


def test_docker_workflow_builds_worker_after_backend_base_image():
    text = _workflow_text()

    backend_index = text.index("name: Build backend runtime image")
    worker_index = text.index("name: Build worker image")
    frontend_index = text.index("name: Build frontend image")
    trivy_index = text.index("name: Run Trivy vulnerability scanner")

    assert backend_index < worker_index < frontend_index < trivy_index
    assert "file: ./Dockerfile.backend" in text
    assert "target: runtime" in text
    assert "target: worker" in text
    assert "miroconsumer-backend:${{ github.sha }}" in text
    assert "miroconsumer-worker:${{ github.sha }}" in text
    assert "file: ./Dockerfile.worker" not in text
