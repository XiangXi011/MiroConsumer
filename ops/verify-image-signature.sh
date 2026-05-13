#!/usr/bin/env bash
set -euo pipefail

IMAGE="${1:?usage: verify-image-signature.sh IMAGE}"
KEY_FILE="${COSIGN_PUBLIC_KEY_PATH:-ops/cosign.pub}"
TMP_KEY=""

cleanup() {
  if [[ -n "$TMP_KEY" && -f "$TMP_KEY" ]]; then
    rm -f "$TMP_KEY"
  fi
}
trap cleanup EXIT

if ! command -v cosign >/dev/null 2>&1; then
  echo "Unsigned image rejected: cosign is required for deployment verification" >&2
  exit 127
fi

if [[ -n "${COSIGN_PUBLIC_KEY:-}" ]]; then
  TMP_KEY="$(mktemp)"
  printf '%s' "$COSIGN_PUBLIC_KEY" > "$TMP_KEY"
  KEY_FILE="$TMP_KEY"
fi

if [[ ! -f "$KEY_FILE" ]]; then
  echo "Unsigned image rejected: missing COSIGN_PUBLIC_KEY or COSIGN_PUBLIC_KEY_PATH" >&2
  exit 42
fi

cosign verify --key "$KEY_FILE" "$IMAGE" >/dev/null
echo "Image signature verified: $IMAGE"
