#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Делает иконку приложения: центр-кроп bg.png в квадрат, скругление углов
# (squircle-подобно) и прозрачный фон по краям. Запуск: venv/bin/python packaging/make_icon.py
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtGui import QImage, QPainter, QPainterPath
from PySide6.QtCore import Qt, QRectF

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
SRC = os.path.join(ROOT, "src", "View", "assets", "bg.png")
OUT = os.path.join(ROOT, "src", "View", "assets", "icon.png")

SIZE = 512               # итоговый размер иконки, px
RADIUS_RATIO = 0.22      # радиус скругления = 22% стороны (как у мобильных иконок)


def main():
    src = QImage(SRC)
    if src.isNull():
        sys.exit(f"Не удалось загрузить {SRC}")

    # центр-кроп в квадрат
    side = min(src.width(), src.height())
    x = (src.width() - side) // 2
    y = (src.height() - side) // 2
    square = src.copy(x, y, side, side).scaled(
        SIZE, SIZE, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)

    out = QImage(SIZE, SIZE, QImage.Format_ARGB32)
    out.fill(Qt.transparent)

    p = QPainter(out)
    p.setRenderHint(QPainter.Antialiasing, True)
    p.setRenderHint(QPainter.SmoothPixmapTransform, True)
    path = QPainterPath()
    r = SIZE * RADIUS_RATIO
    path.addRoundedRect(QRectF(0, 0, SIZE, SIZE), r, r)
    p.setClipPath(path)
    p.drawImage(0, 0, square)
    p.end()

    out.save(OUT, "PNG")
    print("Готово:", OUT, f"({SIZE}x{SIZE}, радиус {int(r)}px, прозрачные углы)")


if __name__ == "__main__":
    main()
