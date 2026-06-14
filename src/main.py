# main.py — точка входа Rhymer (MVP + PySide6)
import os
import sys

# чтобы пакеты Model/View/Presenter импортировались при запуске из любой папки
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication

from Model.Model import Model
from View.View import View
from Presenter.Presenter import Presenter


def main():
    app = QApplication(sys.argv)
    m = Model()
    v = View()
    p = Presenter(m, v)   # noqa: F841 — держит связи сигналов
    v.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
