#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

REMOTE_URL="${1:-}"
BRANCH="${2:-$(git -C "$REPO_ROOT" branch --show-current || echo work)}"

cd "$REPO_ROOT"

echo "[0/7] Repo root: $REPO_ROOT"

echo "[1/7] Checking git remote..."
HAS_REMOTE=0
if git remote get-url origin >/dev/null 2>&1; then
  HAS_REMOTE=1
  echo "origin: $(git remote get-url origin)"
else
  if [[ -n "$REMOTE_URL" ]]; then
    git remote add origin "$REMOTE_URL"
    HAS_REMOTE=1
    echo "origin added: $REMOTE_URL"
  else
    echo "No origin remote configured. Continuing build without push."
  fi
fi

echo "[2/7] Checking Python/build dependencies..."
python3 --version || true
pip --version || true

if ! command -v buildozer >/dev/null 2>&1; then
  echo "Buildozer not found. Trying to install via pip..."
  pip install buildozer cython || true
fi

if ! command -v buildozer >/dev/null 2>&1; then
  echo "Trying apt install of buildozer tooling..."
  if command -v sudo >/dev/null 2>&1; then
    sudo apt-get update -y || true
    sudo apt-get install -y buildozer || true
  else
    apt-get update -y || true
    apt-get install -y buildozer || true
  fi
fi

if ! command -v buildozer >/dev/null 2>&1; then
  echo "Could not install buildozer automatically."
  exit 3
fi

echo "[3/7] Installing Android native build prerequisites (libtool/autoconf/automake)..."
if command -v sudo >/dev/null 2>&1; then
  sudo apt-get update -y || true
  sudo apt-get install -y autoconf automake libtool libtool-bin pkg-config m4 gettext bison flex || true
else
  apt-get update -y || true
  apt-get install -y autoconf automake libtool libtool-bin pkg-config m4 gettext bison flex || true
fi

echo "[4/7] Running Python syntax checks..."
python -m py_compile \
  terminal_ai.py \
  hand_control_mediapipe.py \
  mobile_api/server.py \
  android_client/main.py \
  android_client/service.py \
  discord_bot.py

ensure_modern_p4a_if_needed() {
  local spec="$REPO_ROOT/android_client/buildozer.spec"
  if [[ -f "$spec" ]]; then
    sed -i 's/p4a.branch = stable/p4a.branch = master/g' "$spec" || true
    if ! grep -q '^p4a.branch = ' "$spec"; then
      printf '\np4a.branch = master\n' >> "$spec"
    fi
    if ! grep -q '^android.ndk = ' "$spec"; then
      printf 'android.ndk = 25b\n' >> "$spec"
    fi
  fi
}

build_apk() {
  echo "[5/7] Building APK..."
  (
    cd "$REPO_ROOT/android_client"
    yes y | buildozer android debug
  )
}

if ! build_apk; then
  echo "First build failed. Applying recovery (libffi/autotools + p4a compatibility) and retrying..."
  ensure_modern_p4a_if_needed
  rm -rf "$REPO_ROOT/android_client/.buildozer/android/platform/python-for-android" || true
  rm -rf "$REPO_ROOT/android_client/.buildozer/android/platform/build-"* || true
  (
    cd "$REPO_ROOT/android_client"
    yes y | buildozer android clean || true
  )
  build_apk || true

  if [[ -f "$REPO_ROOT/android_client/.buildozer/android/platform/python-for-android/pythonforandroid/toolchain.py" ]] \
    && grep -q "import imp" "$REPO_ROOT/android_client/.buildozer/android/platform/python-for-android/pythonforandroid/toolchain.py"; then
    echo "Detected legacy p4a using imp. Forcing p4a master + clean rebuild..."
    ensure_modern_p4a_if_needed
    rm -rf "$REPO_ROOT/android_client/.buildozer/android/platform/python-for-android" || true
    rm -rf "$REPO_ROOT/android_client/.buildozer/android/platform/build-"* || true
    build_apk
  fi
fi

echo "[6/7] Committing any pending changes..."
if [[ -n "$(git status --porcelain)" ]]; then
  find "$REPO_ROOT" -type d -name __pycache__ -prune -exec rm -rf {} + || true
  find "$REPO_ROOT" -type f -name "*.pyc" -delete || true
  git add -A
  git commit -m "chore: sync before apk build"
fi

echo "[7/7] Pushing to GitHub..."
if [[ "$HAS_REMOTE" == "1" ]]; then
  git push -u origin "$BRANCH"
else
  echo "Skip push: no remote configured."
fi

echo "Done."
