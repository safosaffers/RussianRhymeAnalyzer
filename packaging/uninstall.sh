#!/usr/bin/env bash
# Удаляет установленный Rhymer и ярлыки (обратное к install.sh).
set -euo pipefail
rm -rf "$HOME/.local/opt/Rhymer"
rm -f "$HOME/.local/bin/rhymer"
rm -f "$HOME/.local/share/applications/rhymer.desktop"
rm -f "$HOME/.local/share/icons/hicolor/256x256/apps/rhymer.png"
rm -f "$HOME/.local/share/icons/hicolor/512x512/apps/rhymer.png"
command -v update-desktop-database >/dev/null 2>&1 && \
  update-desktop-database "$HOME/.local/share/applications" >/dev/null 2>&1 || true
echo "Rhymer удалён."
