#!/usr/bin/env bash
set -euo pipefail

REMOTE_URL="${1:-}"
BRANCH="${2:-work}"

echo "[1/6] Checking git remote..."
if git remote get-url origin >/dev/null 2>&1; then
  echo "origin: $(git remote get-url origin)"
else
  if [[ -z "$REMOTE_URL" ]]; then
    echo "No origin remote configured."
    echo "Usage: $0 <github_remote_url> [branch]"
    exit 2
  fi
  git remote add origin "$REMOTE_URL"
  echo "origin added: $REMOTE_URL"
fi

echo "[2/6] Checking Python/build dependencies..."
python3 --version || true
pip --version || true

if ! command -v buildozer >/dev/null 2>&1; then
  echo "Buildozer not found. Trying to install via pip..."
  if ! pip install buildozer cython; then
    echo "pip install failed (likely network/proxy restriction)."
    echo "Trying apt install..."
    if ! apt-get update -y || ! apt-get install -y buildozer; then
      echo "Could not install buildozer automatically."
      exit 3
    fi
  fi
fi

echo "[3/6] Running Python syntax checks..."
python -m py_compile terminal_ai.py hand_control_mediapipe.py mobile_api/server.py android_client/main.py android_client/service.py discord_bot.py

echo "[4/6] Building APK..."
(
  cd android_client
  buildozer android debug
)

echo "[5/6] Committing any pending changes..."
if [[ -n "$(git status --porcelain)" ]]; then
  git add -A
  git commit -m "chore: sync before apk build"
fi

echo "[6/6] Pushing to GitHub..."
git push -u origin "$BRANCH"

echo "Done."
