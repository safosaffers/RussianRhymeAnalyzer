# -*- mode: python ; coding: utf-8 -*-
# PyInstaller — сборка Rhymer: оба детектора рифмы (Юкава и RPST) + генерация (LLM).
# RPST (russian_scansion) тянет torch и ~520 МБ моделей — образ получается большой.
# Сборка:  pyinstaller --noconfirm rhymer.spec   ->   dist/Rhymer/
# Лёгкая сборка без RPST (только Юкава):
#          RHYMER_LITE=1 pyinstaller --noconfirm rhymer.spec
import os

from PyInstaller.utils.hooks import collect_all

LITE = os.environ.get("RHYMER_LITE") == "1"

datas = [
    ("src/View/assets", "View/assets"),   # фоны интерфейса
    ("poems", "poems"),                   # корпус классики для офлайн-генератора
    ("resources", "resources"),           # свод правил о смысле для промпта
]
binaries = []

# Генераторы импортируют SDK лениво — подсказываем сборщику.
hiddenimports = ["anthropic", "openai"]

# Исключаем тяжёлое и ненужное. torch и RPST выкидываем только в лёгкой сборке.
excludes = [
    "torchvision", "torchaudio", "transformers", "tokenizers",
    "scipy", "matplotlib", "pandas", "sympy", "numba", "sklearn",
    "IPython", "jupyter", "notebook", "tkinter", "PIL", "cv2",
    "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets",
    "PySide6.Qt3DCore", "PySide6.QtMultimedia", "PySide6.QtCharts",
    "PySide6.QtQuick", "PySide6.QtQml", "PySide6.QtPdf",
]

if LITE:
    excludes += ["torch", "russian_scansion", "ufal", "ufal.udpipe", "rusyllab"]
else:
    # RPST: сам пакет, его модели (каталог models/ лежит внутри пакета) и
    # нативный ufal.udpipe. collect_all забирает данные, бинарники и подмодули.
    for pkg in ("russian_scansion", "ufal", "rusyllab"):
        pkg_datas, pkg_binaries, pkg_hidden = collect_all(pkg)
        datas += pkg_datas
        binaries += pkg_binaries
        hiddenimports += pkg_hidden
    # импортируются внутри функций RPST — сборщик их сам не находит
    hiddenimports += ["torch", "huggingface_hub", "pyconll",
                      "jellyfish", "jsonpickle", "coloredlogs"]

a = Analysis(
    ["src/main.py"],
    pathex=["src"],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Rhymer",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,            # GUI-приложение без консольного окна
    disable_windowed_traceback=False,
    target_arch=None,
    icon="src/View/assets/icon_R.ico",   # иконка .exe (Windows); на Linux игнор
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="Rhymer",
)
