#!/usr/bin/env bash
# build-on-github 便1: 倉庫の完成品が非公開かを確かめる（docs/handoff/build-on-github/design.md §24 C4・C15）
# ログインしたままなら読める・ログイン無しでは読めない、の両方。ログイン無しで読めたら落とす。
# 使い方: ghcr-private-check.sh <ghcr.io/<namespace>/<name>@sha256:<64桁>>
set -euo pipefail
REF="${1:?usage: ghcr-private-check.sh <ref@sha256:...>}"
if ! [[ "$REF" =~ @sha256:[0-9a-f]{64}$ ]]; then echo "PRIVATE_CHECK error: ref must end with @sha256:<64 hex>"; exit 1; fi
if ! docker manifest inspect "$REF" > /dev/null; then echo "PRIVATE_CHECK error: logged-in read failed"; exit 1; fi
ANON_DIR="$(mktemp -d)"
trap 'rm -rf "$ANON_DIR" 2>/dev/null || true' EXIT
set +e
ANON_OUT="$(DOCKER_CONFIG="$ANON_DIR" docker manifest inspect "$REF" 2>&1)"
ANON_RC=$?
set -e
if [ "$ANON_RC" -eq 0 ]; then
  echo "PRIVATE_CHECK error: anonymous read succeeded (package is not private)"; exit 1
fi
echo "ANON_MESSAGE ${ANON_OUT:0:300}"
case "$ANON_OUT" in
  *unauthorized*|*UNAUTHORIZED*|*denied*|*DENIED*) echo "PRIVATE_CHECK ok" ;;
  *) echo "::warning::PRIVATE_CHECK anonymous read failed without unauthorized/denied (design.md §24-2 U23)" ;;
esac
