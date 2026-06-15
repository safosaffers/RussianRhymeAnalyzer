# main.py — точка входа Rhymer (MVP + PySide6)
import os
import sys

# чтобы пакеты Model/View/Presenter импортировались при запуске из любой папки
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication

from Model.Model import Model
from View.View import View
from View.SettingsDialog import ORG, APP, load_settings, apply_to_env
from Presenter.Presenter import Presenter


def main():
    app = QApplication(sys.argv)
    app.setOrganizationName(ORG)
    app.setApplicationName(APP)
    # сохранённые провайдер/ключи -> переменные окружения ДО создания Model
    apply_to_env(load_settings())

    m = Model()
    v = View()
    p = Presenter(m, v)   # noqa: F841 — держит связи сигналов
    v.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
