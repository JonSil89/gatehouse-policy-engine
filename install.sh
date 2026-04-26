#!/usr/bin/env bash
set -euo pipefail

SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_DIR="${1:-$(pwd)}"

echo "Gatehouse Compliance Kit installer"
echo "Source: ${SOURCE_DIR}"
echo "Target: ${TARGET_DIR}"
echo ""

mkdir -p "${TARGET_DIR}/.github/workflows"
mkdir -p "${TARGET_DIR}/docs"
mkdir -p "${TARGET_DIR}/examples"
mkdir -p "${TARGET_DIR}/templates"
mkdir -p "${TARGET_DIR}/validation/pre-merge-checks"
mkdir -p "${TARGET_DIR}/validation/pre_merge_checks"

copy_if_missing() {
  local rel="$1"
  local src="${SOURCE_DIR}/${rel}"
  local dst="${TARGET_DIR}/${rel}"

  if [ ! -f "${src}" ]; then
    echo "WARNING: Source missing, skipped: ${rel}"
    return 0
  fi

  mkdir -p "$(dirname "${dst}")"

  if [ -e "${dst}" ]; then
    echo "SKIP   ${rel} (already exists)"
    return 0
  fi

  cp "${src}" "${dst}"
  echo "CREATE ${rel}"
}

copy_if_missing "gatehouse.yaml"
copy_if_missing ".github/workflows/quality-gate-demo.yml"
copy_if_missing "templates/change-request-template.md"
copy_if_missing "templates/rollback-plan-template.md"
copy_if_missing "examples/example-change-request.md"
copy_if_missing "examples/example-rollback-plan.md"
copy_if_missing "docs/QUICKSTART.md"
copy_if_missing "validation/pre-merge-checks/validate-change-request.py"
copy_if_missing "validation/pre_merge_checks/__init__.py"
copy_if_missing "validation/pre_merge_checks/config.py"
copy_if_missing "validation/pre_merge_checks/parser.py"
copy_if_missing "validation/pre_merge_checks/rules.py"
copy_if_missing "validation/pre_merge_checks/reporter.py"
copy_if_missing "validation/pre_merge_checks/cli.py"

echo ""
echo "Installation complete. Re-running this script is safe (idempotent)."
