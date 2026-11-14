#!/bin/sh
# Run inside the pinned manylinux container: its own Python has no libpython.so.
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
TEMP_ROOT=$(mktemp -d)
trap 'rm -rf "$TEMP_ROOT"' EXIT
trap 'exit 1' HUP INT TERM
ARCHIVE="$TEMP_ROOT/python.tar.gz"
curl -fLsS --connect-timeout 10 --max-time 120 \
    'https://github.com/astral-sh/python-build-standalone/releases/download/20261026/cpython-3.11.18%2B20261026-x86_64-unknown-linux-gnu-install_only_stripped.tar.gz' \
    -o "$ARCHIVE"
printf '17c4978a36c496dc53c08899ef8dad1ad2734f6325f08d6033a1e66419e0af26  %s\n' "$ARCHIVE" | sha256sum -c -
tar -xzf "$ARCHIVE" -C "$TEMP_ROOT"
PYTHON="$TEMP_ROOT/python/bin/python3.11"
cd "$ROOT"
"$PYTHON" -m pip install -r requirements-build.txt
"$PYTHON" .build/build_cloud_function.py
"$PYTHON" .build/test_cloud_package.py
