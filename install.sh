#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DESKTOP_DIR="$HOME/.local/share/applications"
DESKTOP_FILE="$DESKTOP_DIR/poolsuite-gui.desktop"

mkdir -p "$DESKTOP_DIR"
sed "s|%INSTALL_DIR%|$SCRIPT_DIR|g" "$SCRIPT_DIR/poolsuite-gui.desktop" > "$DESKTOP_FILE"
chmod +x "$DESKTOP_FILE"

echo "Installed: $DESKTOP_FILE"
echo "Launch from your app menu, or run: python3 $SCRIPT_DIR/main.py"
