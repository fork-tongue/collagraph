#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
APP_DIR="$SCRIPT_DIR/todo_app"
EXPECTED="$SCRIPT_DIR/expected_output.json"

echo "==> Installing pyinstaller..."
uv pip install pyinstaller

echo "==> Building todo_app with PyInstaller..."
cd "$APP_DIR"
uv run pyinstaller \
    --noconfirm \
    --log-level WARN \
    --onefile \
    --name todo_app \
    app.py

echo "==> Running bundled application..."
OUTPUT=$(./dist/todo_app)

echo "==> Comparing output..."
EXPECTED_CONTENT=$(cat "$EXPECTED")

if [ "$OUTPUT" = "$EXPECTED_CONTENT" ]; then
    echo "==> PyInstaller test PASSED"
else
    echo "==> PyInstaller test FAILED"
    echo ""
    echo "Expected:"
    echo "$EXPECTED_CONTENT"
    echo ""
    echo "Got:"
    echo "$OUTPUT"
    exit 1
fi
