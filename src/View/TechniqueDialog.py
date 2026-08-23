# View/TechniqueDialog.py
# Окно «Требования к технике»: что стих обязан выдержать.
# Требования не пожелание, а условие: они уходят в промпт генерации и
# проверяются автоматически — и у сгенерированного стиха, и на вкладке оценки.
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QGridLayout, QLabel,
                               QCheckBox, QLineEdit, QDialogButtonBox)

from Model.Techniques import TECHNIQUES


class TechniqueDialog(QDialog):
    def __init__(self, parent, current: list = None):
        super().__init__(parent)
        self.setWindowTitle("Требования к технике")
        self.setMinimumWidth(560)
        chosen = {r.get("id"): r.get("param", "") for r in (current or [])}

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        cap = QLabel("Отмеченное обязательно к исполнению: требование уходит в "
                     "задание модели и проверяется после генерации, а также при "
                     "оценке стиха на второй вкладке.")
        cap.setWordWrap(True)
        root.addWidget(cap)

        grid = QGridLayout()
        grid.setColumnStretch(1, 1)
        self.rows = {}
        for row, (tid, t) in enumerate(TECHNIQUES.items()):
            cb = QCheckBox(t["label"])
            cb.setChecked(tid in chosen)
            ed = QLineEdit(chosen.get(tid, ""))
            ed.setPlaceholderText(t["param"] or "без параметра")
            ed.setEnabled(bool(t["param"]) and cb.isChecked())
            cb.toggled.connect(
                lambda on, e=ed, need=bool(t["param"]): e.setEnabled(on and need))
            hint = QLabel(t["hint"])
            hint.setWordWrap(True)
            grid.addWidget(cb, row, 0)
            grid.addWidget(ed, row, 1)
            grid.addWidget(hint, row, 2)
            self.rows[tid] = (cb, ed)
        root.addLayout(grid)

        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.button(QDialogButtonBox.Ok).setText("Применить")
        bb.button(QDialogButtonBox.Cancel).setText("Отмена")
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        root.addWidget(bb)

    def result_techniques(self) -> list:
        """Отмеченные требования: [{id, param}]. Требование без обязательного
        параметра тоже валидно (кольцо, анафора без слова)."""
        out = []
        for tid, (cb, ed) in self.rows.items():
            if cb.isChecked():
                out.append({"id": tid, "param": ed.text().strip()})
        return out
