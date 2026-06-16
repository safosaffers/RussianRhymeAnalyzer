# View/View.py
import html
import os

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QFormLayout,
    QGroupBox, QLabel, QSpinBox, QDoubleSpinBox, QComboBox, QPushButton,
    QPlainTextEdit, QTextEdit, QTableWidget, QTableWidgetItem, QHeaderView,
    QFrame, QCheckBox, QTabWidget, QFileDialog, QMessageBox, QSizePolicy,
)
from PySide6.QtGui import QAction, QPainter, QColor, QPixmap
from PySide6.QtCore import Qt, Signal, QRect

from View.SettingsDialog import SettingsDialog, save_settings, apply_to_env
from Model.Session import save_session, load_session

METERS = ["ямб", "хорей", "дактиль", "амфибрахий", "анапест"]
SCHEMES = ["ABAB", "AABB", "ABBA"]
METHODS = [("RPST (хвосты)", "rpst"), ("Юкава (мой)", "yukawa")]


class GrowingTextEdit(QPlainTextEdit):
    """Поле ввода, растущее под текст (как в чат-вводах): от min_lines строк
    до max_lines, дальше — скролл."""

    def __init__(self, min_lines=1, max_lines=8, parent=None):
        super().__init__(parent)
        self.min_lines = min_lines
        self.max_lines = max_lines
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.textChanged.connect(self._adjust)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._adjust()

    def _adjust(self):
        lh = self.fontMetrics().lineSpacing()
        doc = self.document()
        doc.setTextWidth(max(1, self.viewport().width()))
        h = doc.size().height()
        h = max(self.min_lines * lh, min(self.max_lines * lh, h))
        self.setFixedHeight(int(h) + self.frameWidth() * 2 + 10)


def load_bg(dark: bool):
    """Картинка-фон из assets: bgdark.* для тёмной темы, bg.* для светлой."""
    base = os.path.join(os.path.dirname(__file__), "assets")
    for name in (("bgdark.png", "bgdark.jpg") if dark else ("bg.png", "bg.jpg")):
        path = os.path.join(base, name)
        if os.path.exists(path):
            pm = QPixmap(path)
            if not pm.isNull():
                return pm
    return None


def paint_cover(widget, pix, fallback=QColor("#7C3AED")):
    """Рисует pix на всё окно в режиме «cover» (заполнить, обрезать края)."""
    p = QPainter(widget)
    p.setRenderHint(QPainter.SmoothPixmapTransform)
    if pix is not None:
        s = pix.scaled(widget.size(), Qt.KeepAspectRatioByExpanding,
                       Qt.SmoothTransformation)
        x = (s.width() - widget.width()) // 2
        y = (s.height() - widget.height()) // 2
        p.drawPixmap(widget.rect(), s, QRect(x, y, widget.width(), widget.height()))
    else:
        p.fillRect(widget.rect(), fallback)
    p.end()


class DecorBackground(QWidget):
    """Фон-картинка на всё окно (cover). Светлая/тёмная тема — разные картинки."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self._pix = load_bg(False)

    def set_dark(self, dark: bool):
        self._pix = load_bg(dark)
        self.update()

    def paintEvent(self, e):
        paint_cover(self, self._pix)


class CollapsibleSection(QWidget):
    """Окошко с шапкой-кнопкой: клик — свернуть/развернуть содержимое."""

    def __init__(self, title, content, expanded=True, parent=None):
        super().__init__(parent)
        self._title, self.content = title, content
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(4)
        self.header = QPushButton()
        self.header.setObjectName("sect")
        self.header.setCheckable(True)
        self.header.setChecked(expanded)
        self.header.setCursor(Qt.PointingHandCursor)
        self.header.toggled.connect(self._on)
        v.addWidget(self.header)
        v.addWidget(content)
        self._on(expanded)

    def _on(self, exp):
        self.content.setVisible(exp)
        self.header.setText(("▼  " if exp else "▶  ") + self._title)


class View(QMainWindow):
    """Интерфейс (MVP): меню сверху, вкладки «Генерация» и «Оценка рифм»,
    общая панель (метод определения рифм, статус, тема оформления)."""

    candidate_selected = Signal(int)
    tune_changed = Signal()        # изменили константы Юкавы — пересчитать вживую
    settings_applied = Signal(dict)  # сохранили настройки (провайдер/ключи)

    TITLE = "Каримов Сафо. Rhymer — генерация и оценка рифм"

    THEMES = ["light", "dark"]

    def __init__(self):
        super().__init__()
        self.current_theme = "light"
        self.current_path = None      # путь текущей сессии (.rhymer.json)
        self._dirty = False
        self.setWindowTitle(self.TITLE)
        self.resize(1200, 780)
        self._build()
        self.apply_theme()
        # пустые «легенды рифм» не показываем (иначе висит пустая плашка)
        self.l_gen_legend.setVisible(False)
        self.l_eval_legend.setVisible(False)
        # отмечаем несохранённые правки основного содержимого
        self.pte_input.textChanged.connect(self._mark_dirty)
        self.le_theme.textChanged.connect(self._mark_dirty)

    # ---------- построение ----------
    def _build(self):
        self._build_menus()
        self._central = DecorBackground()
        root = QVBoxLayout(self._central)
        root.setContentsMargins(22, 14, 22, 22)
        root.setSpacing(14)

        # верхняя панель: метод рифм (общий), статус, тема оформления
        top = QHBoxLayout()
        top.addWidget(QLabel("Метод определения рифм:"))
        self.cb_method = QComboBox()
        self.cb_method.addItems([t for t, _ in METHODS])
        top.addWidget(self.cb_method)
        top.addSpacing(16)
        self.l_status = QLabel("Готово"); self.l_status.setObjectName("status")
        # статус не должен растягивать окно под длинный текст
        self.l_status.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        top.addWidget(self.l_status, 1)
        self.btn_theme = QPushButton("🌙 Тёмная тема")
        self.btn_theme.clicked.connect(self.toggle_theme)
        top.addWidget(self.btn_theme)
        root.addLayout(top)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_gen_tab(), "Генерация")
        self.tabs.addTab(self._build_eval_tab(), "Оценка рифм")
        root.addWidget(self.tabs, 1)

        self.setCentralWidget(self._central)

    # ---------- меню ----------
    def _build_menus(self):
        bar = self.menuBar()
        m_file = bar.addMenu("Файл")
        for name, slot, sc in [
            ("Новая", self._new_session, "Ctrl+N"),
            ("Открыть…", self._open_session, "Ctrl+O"),
            ("Сохранить", self._save_session, "Ctrl+S"),
            ("Сохранить как…", self._save_session_as, "Ctrl+Shift+S"),
        ]:
            a = QAction(name, self)
            a.setShortcut(sc)
            a.triggered.connect(slot)
            m_file.addAction(a)

        m_view = bar.addMenu("Вид")
        self.act_light = QAction("Светлая", self, checkable=True)
        self.act_dark = QAction("Тёмная", self, checkable=True)
        self.act_light.triggered.connect(lambda: self._set_theme("light"))
        self.act_dark.triggered.connect(lambda: self._set_theme("dark"))
        m_view.addAction(self.act_light)
        m_view.addAction(self.act_dark)

        m_settings = bar.addMenu("Настройки")
        act = QAction("Параметры…", self)
        act.triggered.connect(self._open_settings)
        m_settings.addAction(act)

    def _open_settings(self):
        dlg = SettingsDialog(self, dark=(self.current_theme == "dark"))
        if dlg.exec():
            cfg = dlg.result_config()
            save_settings(cfg)
            apply_to_env(cfg)
            self.settings_applied.emit(cfg)

    # ---------- сессия (Файл) ----------
    def session_state(self) -> dict:
        return {
            "poem": self.eval_text(),
            "gen": {
                "theme": self.theme_text(), "n_lines": self.n_lines(),
                "meter": self.meter(), "scheme": self.scheme(),
                "n": self.n_candidates(), "use_llm": self.use_llm(),
            },
            "method": self.rhyme_method(),
            "yukawa": self.yukawa_params(),
        }

    def apply_session(self, st: dict):
        self.pte_input.setPlainText(st.get("poem", ""))
        g = st.get("gen", {})
        self.le_theme.setPlainText(g.get("theme", ""))
        self.sb_lines.setValue(int(g.get("n_lines", 4)))
        self.cb_meter.setCurrentText(g["meter"] if g.get("meter") in METERS else METERS[0])
        self.cb_scheme.setCurrentText(g["scheme"] if g.get("scheme") in SCHEMES else SCHEMES[0])
        self.sb_n.setValue(int(g.get("n", 6)))
        if self.cb_llm.isEnabled():
            self.cb_llm.setChecked(bool(g.get("use_llm", self.cb_llm.isChecked())))
        method = st.get("method", "rpst")
        for i, (_, val) in enumerate(METHODS):
            if val == method:
                self.cb_method.setCurrentIndex(i)
        if st.get("yukawa"):
            self._apply_yukawa(st["yukawa"])

    def _apply_yukawa(self, yk: dict):
        spins = {self.yk_lam: "lam", self.yk_gamma: "gamma", self.yk_link: "link_ratio",
                 self.yk_vowel: "vowel_weight", self.yk_ediv: "energy_div",
                 self.yk_voiced: "voiced_mult", self.yk_voiceless: "voiceless_mult"}
        checks = {self.yk_use_distance: "use_distance", self.yk_use_energy: "use_energy"}
        widgets = list(spins) + list(checks)
        for w in widgets:
            w.blockSignals(True)
        for w, k in spins.items():
            if k in yk:
                w.setValue(float(yk[k]))
        for w, k in checks.items():
            if k in yk:
                w.setChecked(bool(yk[k]))
        for w in widgets:
            w.blockSignals(False)

    def _new_session(self):
        self.apply_session({})
        self.current_path = None
        self._dirty = False
        self._update_title()
        self.set_status("Новая сессия")

    def _open_session(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Открыть сессию", "",
            "Сессия Rhymer (*.rhymer.json);;JSON (*.json);;Все файлы (*)")
        if not path:
            return
        try:
            st = load_session(path)
        except Exception as e:   # noqa: BLE001
            QMessageBox.warning(self, "Ошибка", f"Не удалось открыть файл:\n{e}")
            return
        self.apply_session(st)
        self.current_path = path
        self._dirty = False
        self._update_title()
        self.set_status("Открыто: " + path)

    def _save_session(self):
        if not self.current_path:
            self._save_session_as()
            return
        self._write_session(self.current_path)

    def _save_session_as(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить сессию", "session.rhymer.json",
            "Сессия Rhymer (*.rhymer.json);;JSON (*.json)")
        if not path:
            return
        if not path.endswith(".json"):
            path += ".rhymer.json"
        self._write_session(path)

    def _write_session(self, path: str):
        try:
            save_session(path, self.session_state())
        except Exception as e:   # noqa: BLE001
            QMessageBox.warning(self, "Ошибка", f"Не удалось сохранить файл:\n{e}")
            return
        self.current_path = path
        self._dirty = False
        self._update_title()
        self.set_status("Сохранено: " + path)

    def _mark_dirty(self):
        if not self._dirty:
            self._dirty = True
            self._update_title()

    def _update_title(self):
        if self.current_path:
            name = os.path.basename(self.current_path)
            self.setWindowTitle(f"{'*' if self._dirty else ''}{name} — Rhymer")
        else:
            self.setWindowTitle(("*" if self._dirty else "") + self.TITLE)

    def _build_gen_tab(self) -> QWidget:
        tab = QWidget(); tab.setObjectName("page"); row = QHBoxLayout(tab)

        # --- слева: параметры (свор.), кнопка, кандидаты (свор.) ---
        left = QVBoxLayout()
        params = QWidget(); params.setObjectName("panel"); form = QFormLayout(params)
        self.le_theme = GrowingTextEdit(min_lines=1, max_lines=6)
        self.le_theme.setPlaceholderText("тема стихотворения: зима, любовь, море…")
        self.sb_lines = QSpinBox(); self.sb_lines.setRange(2, 12); self.sb_lines.setValue(4)
        self.cb_meter = QComboBox(); self.cb_meter.addItems(METERS)
        self.cb_scheme = QComboBox(); self.cb_scheme.addItems(SCHEMES)
        self.sb_n = QSpinBox(); self.sb_n.setRange(2, 16); self.sb_n.setValue(6)
        form.addRow("Тема:", self.le_theme)
        form.addRow("Строк:", self.sb_lines)
        form.addRow("Размер:", self.cb_meter)
        form.addRow("Рифмовка:", self.cb_scheme)
        form.addRow("Кандидатов (N):", self.sb_n)
        self.cb_llm = QCheckBox("Генерировать через ИИ")
        form.addRow(self.cb_llm)
        self.sec_params = CollapsibleSection("Параметры генерации", params)
        left.addWidget(self.sec_params)

        self.btn_generate = QPushButton("Сгенерировать")
        left.addWidget(self.btn_generate)

        # кандидаты — под кнопкой
        self.tbl = QTableWidget(0, 4)
        self.tbl.setHorizontalHeaderLabels(["Текст (1-я строка)", "рифма %", "размер", "схема"])
        self.tbl.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.tbl.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tbl.setSelectionBehavior(QTableWidget.SelectRows)
        self.tbl.cellClicked.connect(lambda r, c: self.candidate_selected.emit(r))
        self.sec_candidates = CollapsibleSection(
            "Кандидаты (по убыванию качества рифмы)", self.tbl)
        left.addWidget(self.sec_candidates, 1)

        # --- справа: крупное поле «лучший вариант» ---
        right = QVBoxLayout()
        right.addWidget(QLabel("Лучший вариант (рифмы выделены цветом):"))
        self.te_gen_best = QTextEdit(); self.te_gen_best.setReadOnly(True)
        right.addWidget(self.te_gen_best, 1)
        self.l_gen_metrics = QLabel("—"); self.l_gen_metrics.setWordWrap(True)
        right.addWidget(self.l_gen_metrics)
        self.l_gen_legend = QLabel(""); self.l_gen_legend.setWordWrap(True)
        right.addWidget(self.l_gen_legend)

        self._gen_row = row
        row.addLayout(left, 3); row.addLayout(right, 4)
        # оба окошка свёрнуты → ужать левую колонку, расширить «лучший вариант»
        self.sec_params.header.toggled.connect(self._update_gen_split)
        self.sec_candidates.header.toggled.connect(self._update_gen_split)
        return tab

    def _update_gen_split(self):
        both = (not self.sec_params.content.isVisible()
                and not self.sec_candidates.content.isVisible())
        self._gen_row.setStretch(0, 0 if both else 3)
        self._gen_row.setStretch(1, 1 if both else 4)

    def _build_eval_tab(self) -> QWidget:
        tab = QWidget(); tab.setObjectName("page"); row = QHBoxLayout(tab)

        left = QVBoxLayout()
        left.addWidget(QLabel("Вставьте стихотворение:"))
        self.pte_input = QPlainTextEdit()
        self.pte_input.setPlaceholderText("одна строка стиха на строку…")
        left.addWidget(self.pte_input, 1)
        left.addWidget(CollapsibleSection(
            "Настройка Юкавы — пересчёт вживую", self._build_yukawa_panel()))
        self.btn_evaluate = QPushButton("Оценить рифмы")
        left.addWidget(self.btn_evaluate)

        right = QVBoxLayout()
        right.addWidget(QLabel("Разбор (рифмы выделены цветом):"))
        self.te_eval_best = QTextEdit(); self.te_eval_best.setReadOnly(True)
        right.addWidget(self.te_eval_best, 1)
        self.l_eval_metrics = QLabel("—"); self.l_eval_metrics.setWordWrap(True)
        right.addWidget(self.l_eval_metrics)
        self.l_eval_legend = QLabel(""); self.l_eval_legend.setWordWrap(True)
        right.addWidget(self.l_eval_legend)

        row.addLayout(left, 1); row.addLayout(right, 1)
        return tab

    # ---------- панель настройки Юкавы ----------
    def _dspin(self, lo, hi, step, val, decimals=2):
        s = QDoubleSpinBox()
        s.setRange(lo, hi); s.setSingleStep(step); s.setDecimals(decimals); s.setValue(val)
        s.valueChanged.connect(lambda *_: self.tune_changed.emit())
        return s

    def _build_yukawa_panel(self) -> QWidget:
        gb = QWidget(); gb.setObjectName("panel")
        form = QFormLayout(gb)
        self.yk_use_distance = QCheckBox("Экранирование по расстоянию")
        self.yk_use_distance.setChecked(True)
        self.yk_use_distance.stateChanged.connect(lambda *_: self.tune_changed.emit())
        self.yk_lam = self._dspin(0.0, 3.0, 0.1, 0.8)
        self.yk_gamma = self._dspin(0.0, 1.0, 0.05, 0.3)
        self.yk_link = self._dspin(0.0, 1.0, 0.05, 0.6)
        self.yk_vowel = self._dspin(0.0, 1.0, 0.05, 0.6)
        self.yk_use_energy = QCheckBox("Учитывать энергию слогов")
        self.yk_use_energy.setChecked(True)
        self.yk_use_energy.stateChanged.connect(lambda *_: self.tune_changed.emit())
        self.yk_ediv = self._dspin(1.0, 50.0, 1.0, 10.0, decimals=1)
        self.yk_voiced = self._dspin(0.5, 4.0, 0.1, 2.0)
        self.yk_voiceless = self._dspin(0.1, 2.0, 0.1, 0.5)
        form.addRow(self.yk_use_distance)
        form.addRow("λ экранирование:", self.yk_lam)
        form.addRow("γ резонанс:", self.yk_gamma)
        form.addRow("порог рифмы:", self.yk_link)
        form.addRow("вес гласной:", self.yk_vowel)
        form.addRow(self.yk_use_energy)
        form.addRow("делитель энергии:", self.yk_ediv)
        form.addRow("звонкие ×:", self.yk_voiced)
        form.addRow("глухие ×:", self.yk_voiceless)
        self.btn_yk_reset = QPushButton("Сбросить к умолчаниям")
        self.btn_yk_reset.clicked.connect(self._reset_yukawa)
        form.addRow(self.btn_yk_reset)
        return gb

    def yukawa_params(self) -> dict:
        return {
            "use_distance": self.yk_use_distance.isChecked(),
            "lam": self.yk_lam.value(),
            "gamma": self.yk_gamma.value(),
            "link_ratio": self.yk_link.value(),
            "vowel_weight": self.yk_vowel.value(),
            "use_energy": self.yk_use_energy.isChecked(),
            "energy_div": self.yk_ediv.value(),
            "voiced_mult": self.yk_voiced.value(),
            "voiceless_mult": self.yk_voiceless.value(),
        }

    def _reset_yukawa(self):
        defaults = {self.yk_lam: 0.8, self.yk_gamma: 0.3, self.yk_link: 0.6,
                    self.yk_vowel: 0.6, self.yk_ediv: 10.0,
                    self.yk_voiced: 2.0, self.yk_voiceless: 0.5}
        checks = [self.yk_use_distance, self.yk_use_energy]
        for w in list(defaults) + checks:
            w.blockSignals(True)
        for w, v in defaults.items():
            w.setValue(v)
        for c in checks:
            c.setChecked(True)
        for w in list(defaults) + checks:
            w.blockSignals(False)
        self.tune_changed.emit()

    # ---------- геттеры ----------
    def theme_text(self): return self.le_theme.toPlainText().strip()
    def n_lines(self): return self.sb_lines.value()
    def meter(self): return self.cb_meter.currentText()
    def scheme(self): return self.cb_scheme.currentText()
    def n_candidates(self): return self.sb_n.value()
    def rhyme_method(self): return METHODS[self.cb_method.currentIndex()][1]
    def use_llm(self): return self.cb_llm.isChecked()
    def eval_text(self): return self.pte_input.toPlainText()

    def set_llm_available(self, available: bool, name: str = "", provider: str = "anthropic"):
        hint = {"gemini": ("GEMINI_API_KEY", "openai"),
                "deepseek": ("DEEPSEEK_API_KEY", "openai"),
                "anthropic": ("ANTHROPIC_API_KEY", "anthropic")}
        if available and name:
            self.cb_llm.setText(f"Генерировать через {name}")
            self.cb_llm.setToolTip("")
        else:
            env, pkg = hint.get(provider, hint["anthropic"])
            self.cb_llm.setText(f"Генерировать через ИИ (провайдер: {provider})")
            self.cb_llm.setToolTip(
                f"Недоступно. Нужно в этой же сессии: RHYMER_PROVIDER={provider}, "
                f"переменная {env} и пакет {pkg} (pip install {pkg}).")
        self.cb_llm.setEnabled(available)
        self.cb_llm.setChecked(available)

    # ---------- статус / занятость ----------
    def set_status(self, msg: str):
        self.l_status.setText(msg)

    def set_busy(self, busy: bool):
        self.btn_generate.setEnabled(not busy)
        self.btn_evaluate.setEnabled(not busy)

    # ---------- результаты ----------
    def set_gen_result(self, text: str, m: dict):
        self.te_gen_best.setHtml(self._poem_html(text, m))
        self.l_gen_metrics.setText(self._fmt_metrics(m))
        leg = self._legend_html(m)
        self.l_gen_legend.setText(leg); self.l_gen_legend.setVisible(bool(leg))

    def set_eval_result(self, text: str, m: dict):
        self.te_eval_best.setHtml(self._poem_html(text, m))
        self.l_eval_metrics.setText(self._fmt_metrics(m))
        leg = self._legend_html(m)
        self.l_eval_legend.setText(leg); self.l_eval_legend.setVisible(bool(leg))

    def show_error(self, msg: str):
        """Ошибку показываем отдельным окном, а не растягиваем интерфейс."""
        QMessageBox.critical(self, "Ошибка", msg)

    def clear_candidates(self):
        self.tbl.setRowCount(0)

    def set_candidates(self, scored: list[tuple[str, dict]]):
        self.tbl.setRowCount(0)
        for text, m in scored:
            r = self.tbl.rowCount(); self.tbl.insertRow(r)
            first = text.splitlines()[0] if text.strip() else ""
            if m.get("corrected"):
                first = "✓ " + first
            self.tbl.setItem(r, 0, QTableWidgetItem(first))
            self.tbl.setItem(r, 1, QTableWidgetItem(f"{m.get('rhyme_percent', 0):.0%}"))
            self.tbl.setItem(r, 2, QTableWidgetItem(str(m.get("meter") or "—")))
            self.tbl.setItem(r, 3, QTableWidgetItem(str(m.get("detected_scheme") or "—")))

    # ---------- форматирование ----------
    @staticmethod
    def _poem_html(text: str, m: dict) -> str:
        colored = m.get("colored_lines")
        if colored:
            rows = []
            for segments in colored:
                parts = []
                for seg_text, color in segments:
                    t = html.escape(seg_text)
                    if color:
                        parts.append(f'<span style="background:{color};color:#111;'
                                     f'border-radius:3px;padding:0 2px">{t}</span>')
                    else:
                        parts.append(t)
                rows.append("".join(parts))
            body = "<br>".join(rows)
        else:
            body = html.escape(text).replace("\n", "<br>")
        return (f'<div style="font-family:Georgia,serif;font-size:18px;'
                f'line-height:1.8">{body}</div>')

    @staticmethod
    def _legend_html(m: dict) -> str:
        legend = m.get("legend") or {}
        if not legend:
            return ""
        chips = []
        for color, words in legend.items():
            w = ", ".join(html.escape(x) for x in words)
            chips.append(f'<span style="background:{color};color:#111;'
                         f'border-radius:3px;padding:0 4px">{w}</span>')
        return "Группы рифм: " + " &nbsp; ".join(chips)

    @staticmethod
    def _fmt_metrics(m: dict) -> str:
        base = (f"Зарифмовано слогов: <b>{m.get('rhyme_percent', 0):.0%}</b>"
                f" ({m.get('rhymed_syllables', 0)} из {m.get('total_syllables', 0)})")
        if m.get("method") == "yukawa":
            return ("[Юкава] " + base
                    + f"   |   Групп рифм: <b>{m.get('num_groups', 0)}</b>")
        return (base
                + f"   |   Поэтичность RPST: <b>{m.get('score', 0):.2f}</b>"
                + f"   |   Размер: <b>{m.get('meter') or '—'}</b>"
                + f"   |   Схема: <b>{m.get('detected_scheme') or '—'}</b>")

    # ---------- темы ----------
    def toggle_theme(self):
        i = self.THEMES.index(self.current_theme)
        self._set_theme(self.THEMES[(i + 1) % len(self.THEMES)])

    def _set_theme(self, theme: str):
        self.current_theme = theme
        self.apply_theme()

    def apply_theme(self):
        """Светлая/тёмная: разные фон-картинки и палитры (тёмная — тёмные блоки
        ввода и кроваво-красные кнопки). QSS — на всё приложение."""
        dark = self.current_theme == "dark"
        app = QApplication.instance()
        (app or self).setStyleSheet(self._app_qss(dark))
        if hasattr(self, "_central"):
            self._central.set_dark(dark)
        self._sync_theme_controls()

    def _sync_theme_controls(self):
        dark = self.current_theme == "dark"
        self.btn_theme.setText("☀ Светлая" if dark else "🌙 Тёмная")
        if hasattr(self, "act_light"):
            self.act_light.setChecked(not dark)
            self.act_dark.setChecked(dark)

    @staticmethod
    def _app_qss(dark: bool) -> str:
        # фон рисует DecorBackground; здесь — панели/блоки/кнопки.
        NAVY, YELLOW = "#1E293B", "#FBBF24"
        if dark:
            PANEL, PANEL_FG = "#23252b", "#E5E7EB"
            # поля ввода/вывода — заметно темнее панели, чтобы отличались
            INPUT_BG, INPUT_FG, BORDER = "#141619", "#E8E8E8", "#0b0d10"
            SECT, GRID = "#0f172a", "#3b3d44"
            BTN, BTN_H, BTN_P = "#611212", "#761616", "#4D0E0E"   # тёмно-кровавый (−30%)
        else:
            PANEL, PANEL_FG = "#F1EBDD", "#1F2937"                # молочный
            INPUT_BG, INPUT_FG, BORDER = "#FCF9F2", "#1F2937", "#1E293B"
            SECT, GRID = "#1E293B", "#D9CFE8"
            BTN, BTN_H, BTN_P = "#EC4899", "#F472B6", "#DB2777"   # розовый
        return f"""
            * {{ font-size: 15px; }}
            QWidget#page {{ background: transparent; }}
            QMenuBar {{ background:{NAVY}; color:#ffffff; font-size:15px; padding:4px; }}
            QMenuBar::item {{ padding:6px 14px; }}
            QMenuBar::item:selected {{ background:{BTN}; border-radius:6px; }}
            QMenu {{ background:{NAVY}; color:#ffffff; font-size:15px; }}
            QMenu::item:selected {{ background:{BTN}; }}

            /* подписи поверх пёстрого фона — на полупрозрачной тёмной подложке */
            QLabel {{ color:#ffffff; font-size:16px;
                      background: rgba(15,23,42,0.80); border-radius:9px;
                      padding:3px 10px; }}
            QLabel#status {{ color:{YELLOW}; font-weight:bold; font-size:16px;
                             background: rgba(15,23,42,0.85); }}
            QCheckBox {{ color:#ffffff; font-size:15px; spacing:8px; }}
            QCheckBox::indicator {{ width:22px; height:22px; }}

            /* панель-карточка сворачиваемого окошка */
            QWidget#panel {{ background:{PANEL}; border:3px solid {BORDER};
                             border-radius:14px; }}
            QWidget#panel QLabel {{ color:{PANEL_FG}; font-weight:normal;
                                    background:transparent; padding:0; }}
            QWidget#panel QCheckBox {{ color:{PANEL_FG}; }}
            /* шапка сворачиваемого окошка */
            QPushButton#sect {{ background:{SECT}; color:#ffffff; border:3px solid {SECT};
                                border-radius:12px; padding:10px 16px; font-size:16px;
                                font-weight:bold; text-align:left; }}
            QPushButton#sect:hover {{ background:#334155; }}

            QPlainTextEdit, QTextEdit, QSpinBox, QDoubleSpinBox, QComboBox,
            QLineEdit, QTableWidget {{
                background:{INPUT_BG}; color:{INPUT_FG}; border:3px solid {BORDER};
                border-radius:12px; padding:8px; font-size:15px;
                selection-background-color:#7C3AED; }}
            QTextEdit, QPlainTextEdit {{ font-size:17px; }}
            QComboBox::drop-down {{ border:none; width:26px; }}
            /* выпадающий список (выбор метода и т.п.) — свой фон, не сливается с фото */
            QComboBox QAbstractItemView {{ background:{INPUT_BG}; color:{INPUT_FG};
                border:2px solid {BORDER}; selection-background-color:{BTN};
                selection-color:#ffffff; outline:none; }}

            QPushButton {{ background:{BTN}; color:#ffffff; border:3px solid {BORDER};
                           border-radius:14px; padding:12px 20px; font-size:17px;
                           font-weight:bold; }}
            QPushButton:hover {{ background:{BTN_H}; }}
            QPushButton:pressed {{ background:{BTN_P}; }}
            QPushButton:disabled {{ background:#9CA3AF; border-color:#6B7280; color:#E5E7EB; }}

            QTabWidget::pane {{ border:3px solid {BORDER}; border-radius:16px;
                                background:transparent; top:-3px; }}
            QTabBar::tab {{ background:{PANEL}; color:{PANEL_FG}; padding:12px 28px;
                            margin-right:8px; border:3px solid {BORDER}; border-bottom:none;
                            border-top-left-radius:14px; border-top-right-radius:14px;
                            font-size:16px; font-weight:bold; }}
            QTabBar::tab:selected {{ background:{YELLOW}; color:{NAVY}; }}

            QHeaderView::section {{ background:{NAVY}; color:#ffffff; padding:8px;
                                    border:none; font-size:14px; font-weight:bold; }}
            QTableWidget {{ gridline-color:{GRID}; }}
            QScrollBar:vertical {{ background:transparent; width:14px; margin:2px; }}
            QScrollBar::handle:vertical {{ background:{BTN}; border-radius:7px; min-height:36px; }}
            QScrollBar::add-line, QScrollBar::sub-line {{ height:0; }}
        """
