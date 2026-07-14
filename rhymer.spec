# -*- mode: python ; coding: utf-8 -*-
# PyInstaller — ОБЛЕГЧЁННАЯ сборка Rhymer: детектор Юкавы + генерация (LLM).
# БЕЗ torch и RPST (russian_scansion) — они исключены, поэтому образ компактный.
# Сборка:  pyinstaller --noconfirm rhymer.spec   ->   dist/Rhymer/
datas = [
    ("src/View/assets", "View/assets"),   # фоны интерфейса
    ("poems", "poems"),                   # корпус классики для офлайн-генератора
]

# Генераторы импортируют SDK лениво — подсказываем сборщику.
hiddenimports = ["anthropic", "openai"]

# Исключаем тяжёлое и ненужное (главное — torch и RPST).
excludes = [
    "torch", "torchvision", "torchaudio",
    "russian_scansion", "ufal", "ufal.udpipe", "transformers", "tokenizers",
    "scipy", "matplotlib", "pandas", "sympy", "numba", "sklearn",
    "IPython", "jupyter", "notebook", "tkinter", "PIL", "cv2",
    "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets",
    "PySide6.Qt3DCore", "PySide6.QtMultimedia", "PySide6.QtCharts",
    "PySide6.QtQuick", "PySide6.QtQml", "PySide6.QtPdf",
]

a = Analysis(
    ["src/main.py"],
    pathex=["src"],
    binaries=[],
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
