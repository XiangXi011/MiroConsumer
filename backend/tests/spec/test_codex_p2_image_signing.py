"""SPEC-P2-020 image signing and integrity contract."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_image_sign_workflow_uses_cosign_key_material_and_verification():
    text = _read(".github/workflows/image-sign.yml")

    assert "sigstore/cosign-installer" in text
    assert "COSIGN_PRIVATE_KEY" in text
    assert "COSIGN_PASSWORD" in text
    assert "cosign sign" in text
    assert "cosign verify" in text
    assert "ghcr.io/" in text


def test_docker_image_workflow_generates_spdx_sbom_artifact():
    text = _read(".github/workflows/docker-image.yml")

    assert "name: Generate SBOM" in text
    assert "trivy fs" in text or "syft" in text
    assert "spdx-json" in text
    assert "sbom.spdx.json" in text
    assert "name: Upload SBOM artifact" in text
    assert "actions/upload-artifact@v4" in text


def test_production_compose_exposes_signature_verification_profile():
    text = _read("docker-compose.prod.yml")

    assert "image-signature-verify:" in text
    assert "cosign verify" in text
    assert "COSIGN_PUBLIC_KEY" in text
    assert "MIROCONSUMER_BACKEND_IMAGE" in text
    assert "MIROCONSUMER_WORKER_IMAGE" in text
    assert "MIROCONSUMER_FRONTEND_IMAGE" in text


def test_signature_verification_script_runs_cosign_in_strict_mode():
    text = _read("ops/verify-image-signature.sh")

    assert "set -euo pipefail" in text
    assert "cosign verify" in text
    assert "COSIGN_PUBLIC_KEY" in text
    assert "Unsigned image rejected" in text


def test_image_signing_runbook_documents_key_management_and_rejection():
    text = _read("docs/security/image_signing.md")

    for phrase in (
        "COSIGN_PRIVATE_KEY",
        "COSIGN_PASSWORD",
        "public key",
        "cosign verify",
        "SBOM",
        "unsigned",
        "rejected",
        "GitHub Secrets",
    ):
        assert phrase in text
