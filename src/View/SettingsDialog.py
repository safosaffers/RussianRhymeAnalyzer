# View/SettingsDialog.py
# Окно настроек + персистентность (QSettings). Здесь же — заселение настроек
# в переменные окружения, чтобы Model/генераторы подхватывали провайдера и ключи
# без изменения их контракта (они читают os.environ).
import os

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QComboBox, QLineEdit, QLabel,
    QDialogButtonBox,
)

ORG, APP = "Karimov", "Rhymer"
PROVIDERS = ["anthropic", "gemini", "deepseek"]
KEY_ENV = {
    "anthropic": "ANTHROPIC_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
}


def _settings() -> QSettings:
    return QSettings(ORG, APP)


def load_settings() -> dict:
    """Сохранённые настройки; по умолчанию — текущее окружение."""
    s = _settings()
    return {
        "provider": s.value("provider", os.environ.get("RHYMER_PROVIDER", "anthropic")),
        "model": s.value("model", os.environ.get("RHYMER_MODEL", "")) or "",
        "keys": {p: (s.value(f"key/{p}", "") or "") for p in PROVIDERS},
    }


def save_settings(cfg: dict) -> None:
    s = _settings()
    s.setValue("provider", cfg["provider"])
    s.setValue("model", cfg.get("model", ""))
    for p, k in cfg.get("keys", {}).items():
        s.setValue(f"key/{p}", k)
    s.sync()


def apply_to_env(cfg: dict) -> None:
    """Настройки -> os.environ. Пустые значения не затирают внешние переменные
    окружения (заданный снаружи ключ продолжит работать)."""
    if cfg.get("provider"):
        os.environ["RHYMER_PROVIDER"] = cfg["provider"]
    if cfg.get("model"):
        os.environ["RHYMER_MODEL"] = cfg["model"]
    for p, k in cfg.get("keys", {}).items():
        if k:
            os.environ[KEY_ENV[p]] = k


class SettingsDialog(QDialog):
    """Провайдер ИИ, API-ключи и модель. Значения сохраняются между запусками."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Настройки")
        self.setMinimumWidth(440)
        cfg = load_settings()

        root = QVBoxLayout(self)
        form = QFormLayout()
        self.cb_provider = QComboBox()
        self.cb_provider.addItems(PROVIDERS)
        if cfg["provider"] in PROVIDERS:
            self.cb_provider.setCurrentText(cfg["provider"])
        self.le_model = QLineEdit(cfg["model"])
        self.le_model.setPlaceholderText("по умолчанию для провайдера")
        form.addRow("Провайдер ИИ:", self.cb_provider)
        form.addRow("Модель (необяз.):", self.le_model)

        self.keys = {}
        for p in PROVIDERS:
            le = QLineEdit(cfg["keys"].get(p, ""))
            le.setEchoMode(QLineEdit.Password)
            le.setPlaceholderText(KEY_ENV[p])
            self.keys[p] = le
            form.addRow(f"Ключ {p}:", le)
        root.addLayout(form)

        hint = QLabel("Провайдер, модель и ключи сохраняются локально между "
                      "запусками (QSettings). Внешние переменные окружения тоже "
                      "работают.")
        hint.setWordWrap(True)
        root.addWidget(hint)

        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        root.addWidget(bb)

    def result_config(self) -> dict:
        return {
            "provider": self.cb_provider.currentText(),
            "model": self.le_model.text().strip(),
            "keys": {p: le.text().strip() for p, le in self.keys.items()},
        }
