from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
WORKFLOW = ROOT / ".github" / "workflows" / "docker-image.yml"


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
    assert "continue-on-error" not in text


def test_docker_workflow_uses_pinned_trivy_action():
    text = _workflow_text()

    assert "aquasecurity/trivy-action@master" not in text
    assert "aquasecurity/trivy-action@v0.36.0" in text
    assert "severity: 'HIGH,CRITICAL'" in text
    assert "exit-code: '1'" in text
