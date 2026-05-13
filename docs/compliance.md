# Compliance Notes

Updated: 2026-05-13

## SBOM

The Docker image workflow generates a repository-level SPDX JSON SBOM with
Trivy and uploads it as a retained CI artifact. Release managers must attach
the matching SBOM to the release artifact set before publishing externally.

Manual generation:

```bash
docker run --rm -v "$PWD:/workspace" -w /workspace aquasec/trivy:0.58.2 \
  fs --format spdx-json --output sbom.spdx.json .
```

The SBOM must include backend Python dependencies, frontend npm dependencies,
container base images, and workflow-installed runtime tools. Keep the SBOM file
with the image digest or release tag it describes.

## AGPL Obligations

MiroConsumer is distributed under AGPL-3.0. When the software is offered over a
network, operators must provide corresponding source code for the running
version, including local modifications and deployment-relevant build scripts.

Operational policy:

- Keep the public Source link visible in the frontend shell.
- Publish release source archives alongside container images.
- Retain SBOM artifacts for at least 90 days.
- Document any private deployment patches that change user-facing behavior.

## License Scan

CI runs `pip-licenses` for backend packages and `npm audit` for frontend
packages. Allowed licenses include MIT, BSD-2-Clause, BSD-3-Clause,
Apache-2.0, ISC, LGPL, AGPL-3.0, and Python-2.0. Proprietary or
GPL-incompatible packages require legal review before merge.

If a dependency reports an unknown license:

1. Check the upstream package metadata and repository license file.
2. Add the license to the allowlist only after review.
3. Record the decision in the release note for the dependency update.
