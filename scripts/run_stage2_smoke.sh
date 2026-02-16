#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT_DIR="${1:-$ROOT_DIR/artifacts/integration}"
STAMP="$(date -u +%Y%m%d-%H%M%S)"
LOG_PATH="$OUT_DIR/stage2-smoke-$STAMP.log"
VENV_PATH="$OUT_DIR/stage2-smoke-venv-$STAMP"

mkdir -p "$OUT_DIR"
cd "$ROOT_DIR"

cleanup() {
  rm -rf "$VENV_PATH"
}
trap cleanup EXIT

exec > >(tee "$LOG_PATH") 2>&1

echo "== Stage 2 smoke test =="
echo "UTC: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "Root: $ROOT_DIR"
echo "Output dir: $OUT_DIR"
echo

echo "-- Build isolated smoke environment --"
python3 -m venv "$VENV_PATH"
source "$VENV_PATH/bin/activate"
python -m pip install --upgrade pip >/dev/null
python -m pip install "$ROOT_DIR" "impact-preview>=0.2.2" >/dev/null
echo "Created venv: $VENV_PATH"
echo

echo "-- Installed package versions (isolated venv) --"
python - <<'PY'
import importlib.metadata as md

def show(name: str) -> None:
    try:
        print(f"{name}=={md.version(name)}")
    except md.PackageNotFoundError:
        print(f"{name}==NOT_INSTALLED")

show("safe-agent-cli")
show("impact-preview")
PY
echo

echo "-- Preset list smoke --"
safe-agent --list-policy-presets
echo

echo "-- CI option contract smoke --"
safe-agent --help | grep -- "--ci-summary-file" >/dev/null
safe-agent --help | grep -- "--policy-report" >/dev/null
echo "Found CI artifact flags in CLI help."
echo

echo "-- CI workflow contract smoke --"
test -f .github/workflows/safe-agent-pr-review.yml
test -f .github/actions/safe-agent-review/action.yml
echo "Found workflow and composite action files."
echo

echo "Smoke PASS"
echo "Log: $LOG_PATH"
