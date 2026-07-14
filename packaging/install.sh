#!/usr/bin/env bash
# Ставит собранный Rhymer в пользовательский префикс и регистрирует ярлык,
# чтобы приложение запускалось из меню как любое другое (без sudo).
# Использование:  bash packaging/install.sh   (из корня проекта или из dist)
set -euo pipefail

# Корень проекта (родитель этой папки packaging/).
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="$ROOT/dist/Rhymer"
[ -x "$SRC/Rhymer" ] || { echo "Не найдено $SRC/Rhymer — сначала соберите: pyinstaller rhymer.spec"; exit 1; }

APPDIR="$HOME/.local/opt/Rhymer"
BINDIR="$HOME/.local/bin"
ICONROOT="$HOME/.local/share/icons/hicolor"
DESKTOPDIR="$HOME/.local/share/applications"

echo "-> копирую приложение в $APPDIR"
rm -rf "$APPDIR"
mkdir -p "$APPDIR" "$BINDIR" "$DESKTOPDIR"
cp -a "$SRC/." "$APPDIR/"

# иконки: ставим каждый доступный размер в свой слот темы hicolor.
# источник — вшитые в сборку ассеты, иначе исходники репозитория.
ASSETS="$APPDIR/_internal/View/assets"
[ -d "$ASSETS" ] || ASSETS="$ROOT/src/View/assets"
for sz in 256 512; do
    src_icon="$ASSETS/icon-$sz.png"
    [ "$sz" = 512 ] && [ -f "$ASSETS/icon.png" ] && src_icon="$ASSETS/icon.png"
    [ -f "$src_icon" ] || continue
    dst="$ICONROOT/${sz}x${sz}/apps"
    mkdir -p "$dst"
    cp -f "$src_icon" "$dst/rhymer.png"
    echo "-> иконка ${sz}x${sz} -> $dst/rhymer.png"
done

echo "-> ярлык командной строки -> $BINDIR/rhymer"
ln -sf "$APPDIR/Rhymer" "$BINDIR/rhymer"

echo "-> ярлык меню -> $DESKTOPDIR/rhymer.desktop"
cat > "$DESKTOPDIR/rhymer.desktop" <<EOF
[Desktop Entry]
Type=Application
Version=1.0
Name=Rhymer
GenericName=Генерация и оценка рифм
Comment=Генерация стихов и автоматическая оценка рифмы (Юкава + ИИ)
Exec=$APPDIR/Rhymer
Icon=rhymer
Terminal=false
Categories=Education;
StartupNotify=true
EOF
chmod +x "$DESKTOPDIR/rhymer.desktop"

command -v update-desktop-database >/dev/null 2>&1 && \
  update-desktop-database "$DESKTOPDIR" >/dev/null 2>&1 || true
command -v gtk-update-icon-cache >/dev/null 2>&1 && \
  gtk-update-icon-cache -f -t "$HOME/.local/share/icons/hicolor" >/dev/null 2>&1 || true

echo
echo "Готово. Запуск:"
echo "  - из меню приложений: Rhymer"
echo "  - из терминала:       rhymer   (если $BINDIR в PATH)"
echo "  - напрямую:           $APPDIR/Rhymer"
