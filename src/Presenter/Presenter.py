# Presenter/Presenter.py
from PySide6.QtCore import QObject, QThread, Signal, QTimer

from Model.Generator import GenParams


class Worker(QObject):
    """Выполняет тяжёлую задачу (загрузка моделей RPST, генерация, оценка)
    в отдельном потоке. ВАЖНО: здесь только вычисления, без виджетов."""
    done = Signal(object)
    failed = Signal(str)

    def __init__(self, fn):
        super().__init__()
        self.fn = fn

    def run(self):
        try:
            self.done.emit(self.fn())
        except Exception as e:   # noqa: BLE001
            self.failed.emit(repr(e))


class Presenter(QObject):
    """Связывает View и Model (паттерн MVP).

    Presenter — QObject и живёт в главном потоке, поэтому его методы-слоты,
    подключённые к сигналам Worker, вызываются через очередь в главном потоке
    (там, где можно трогать виджеты).
    """

    def __init__(self, m, v):
        super().__init__()
        self.m = m
        self.v = v
        self.last_scored: list[tuple[str, dict]] = []
        self._thread = None
        self._worker = None
        self._mode = None          # 'gen' | 'eval' | 'improve'
        self._eval_text = ""
        self._current_gen = None   # выбранный сейчас вариант (текст, метрики)

        # дебаунс живой оценки: перезапускается при каждом изменении текста/метода
        self._eval_timer = QTimer(self)
        self._eval_timer.setSingleShot(True)
        self._eval_timer.setInterval(300)
        self._eval_timer.timeout.connect(self._do_eval)
        # токен отменяет устаревший анализ: любое изменение делает прошлый результат
        # неактуальным (его отбросим), UI при этом не блокируется
        self._eval_token = 0
        self._eval_threads = set()   # живые потоки анализа (держим от сборки мусора)

        self.v.set_llm_available(self.m.llm_available, self.m.llm_name, self.m.provider)
        self.v.btn_generate.clicked.connect(self.on_generate)
        self.v.btn_improve.clicked.connect(self.on_improve)
        self.v.candidate_selected.connect(self.on_select)
        self.v.tune_changed.connect(self._schedule_eval)
        self.v.eval_changed.connect(self._schedule_eval)
        self.v.settings_applied.connect(self.on_settings)

    # ---------- применение настроек (провайдер/ключи) ----------
    def on_settings(self, cfg):
        self.m.reload_llm()
        self.v.set_llm_available(self.m.llm_available, self.m.llm_name, self.m.provider)
        ok = "доступен" if self.m.llm_available else "ключ не задан/нет пакета"
        self.v.set_status(f"Настройки применены: провайдер {self.m.provider} ({ok})")

    # ---------- асинхронный запуск ----------
    def _run_async(self, fn):
        if self._thread is not None:        # уже идёт работа
            return
        self.v.set_busy(True)
        self._thread = QThread()
        self._worker = Worker(fn)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        # слоты-методы Presenter -> очередь в главный поток (безопасно для UI)
        self._worker.done.connect(self._on_done)
        self._worker.failed.connect(self._on_failed)
        self._worker.done.connect(self._thread.quit)
        self._worker.failed.connect(self._thread.quit)
        self._thread.finished.connect(self._cleanup)
        self._thread.start()

    def _cleanup(self):
        self._thread = None
        self._worker = None
        self.v.set_busy(False)

    def _on_done(self, result):
        if self._mode == "gen":
            self._on_generated(result)
        elif self._mode == "improve":
            self._on_improved(result)
        else:
            self._on_evaluated(self._eval_text, result)

    def _on_failed(self, msg):
        self.v.set_status("Ошибка")
        self.v.show_error(msg)

    # ---------- генерация ----------
    def on_generate(self):
        p = GenParams(theme=self.v.theme_text(), n_lines=self.v.n_lines(),
                      meter=self.v.meter(), scheme=self.v.scheme())
        n = self.v.n_candidates()
        use_llm = self.v.use_llm()
        method = self.v.rhyme_method()
        self._mode = "gen"
        src = self.m.llm_name if use_llm else "корпус классики"
        det = "Юкава" if method == "yukawa" else "RPST"
        note = " (первый запуск грузит модели RPST ~15–30 с)" if method == "rpst" else ""
        # Юкаве передаём те же параметры из «Настройка Юкавы», что и на вкладке
        # «Оценка рифм», — иначе выделения для одного текста расходятся.
        yk = self.v.yukawa_params() if method == "yukawa" else None
        self.v.set_status(f"Генерация ({src}), детектор: {det}…{note}")
        self._run_async(lambda: self.m.generate_best(p, n, use_llm, method, yk))

    def _on_generated(self, scored):
        self.last_scored = scored
        if scored:
            best_text, best_m = scored[0]
            self._current_gen = (best_text, best_m)
            self.v.set_gen_result(best_text, best_m)
            self.v.set_candidates(scored)
            self.v.show_generated_layout()   # свернуть параметры, раскрыть кандидатов
            self.v.set_status(f"Готово: лучший из {len(scored)} кандидатов")
        else:
            self.v.set_status("Нет кандидатов")

    # ---------- улучшение выбранного варианта через ИИ ----------
    def on_improve(self):
        if not self.m.llm_available:
            self.v.show_error("ИИ недоступен. Задай провайдера и ключ в «Настройки».")
            return
        if not self._current_gen:
            self.v.set_status("Сначала сгенерируй и выбери вариант")
            return
        text, _ = self._current_gen
        p = GenParams(theme=self.v.theme_text(), n_lines=self.v.n_lines(),
                      meter=self.v.meter(), scheme=self.v.scheme())
        method = self.v.rhyme_method()
        yk = self.v.yukawa_params() if method == "yukawa" else None
        self._mode = "improve"
        self.v.set_status(f"Улучшаю рифму через {self.m.llm_name}…")
        self._run_async(lambda: self.m.improve_poem(text, p, method, yk))

    def _on_improved(self, result):
        if not result:
            self.v.set_status("ИИ не вернул улучшенный вариант")
            return
        text, m = result
        if m.get("unchanged"):
            # текст не изменился — не дублируем кандидата и не показываем «новый» %
            self.v.set_status("ИИ вернул тот же текст без изменений — улучшать нечего "
                              "или это готовый/классический стих (improve рассчитан "
                              "на черновики ИИ).")
            return
        self._current_gen = (text, m)
        self.last_scored = [(text, m)] + self.last_scored
        self.v.set_gen_result(text, m)
        self.v.set_candidates(self.last_scored)
        self.v.set_status("Готово: рифма улучшена ИИ (вариант добавлен сверху)")

    # ---------- живая оценка (без кнопки, с дебаунсом) ----------
    def _schedule_eval(self):
        self._eval_timer.start()          # перезапуск: считаем после паузы ввода

    def _do_eval(self):
        text = self.v.eval_text()
        self._eval_token += 1             # любое изменение отменяет прошлый анализ
        if not text.strip():
            self.v.clear_eval()
            self.v.set_status("Готово")
            return
        tok = self._eval_token
        method = self.v.rhyme_method()
        scheme = self.v.scheme()
        yk = self.v.yukawa_params() if method == "yukawa" else None
        det = "Юкава" if method == "yukawa" else "RPST"
        note = " (первый запуск грузит модели ~15-30 с)" if method == "rpst" else ""
        self.v.set_status(f"Анализ рифм ({det})...{note}")

        def on_ok(m):
            self.v.set_eval_result(text, m)
            if "rhyme_percent" in m and "num_groups" in m:
                extra = ""
                if yk:
                    extra = (f" (λ={yk['lam']:.2f}, γ={yk['gamma']:.2f},"
                             f" порог={yk['link_ratio']:.2f},"
                             f" энергия={'вкл' if yk['use_energy'] else 'выкл'})")
                self.v.set_status(f"{det}: зарифмовано {m['rhyme_percent']:.0%} слогов,"
                                  f" групп {m['num_groups']}{extra}")
            else:
                self.v.set_status(f"{det}: анализ готов")

        self._run_eval_async(lambda: self.m.evaluate(text, scheme, method, yk), tok, on_ok)

    def _run_eval_async(self, fn, tok, on_ok):
        """Считает анализ в отдельном потоке (UI не блокируется). Результат
        применяется, только если он ещё актуален (tok == текущий); устаревший —
        молча отбрасывается. Никаких очередей: новый запуск просто перебивает старый.

        Получатели сигналов — bound-методы Presenter (живёт в главном потоке),
        поэтому Qt использует QueuedConnection и виджеты трогаются только из
        главного потока (контекст запроса храним на самом воркере)."""
        thread = QThread()
        worker = Worker(fn)
        worker.moveToThread(thread)
        worker._tok = tok                 # контекст запроса
        worker._on_ok = on_ok
        thread._worker = worker           # держим ссылку, иначе соберёт GC
        thread.started.connect(worker.run)
        worker.done.connect(self._eval_worker_done)
        worker.failed.connect(self._eval_worker_failed)
        worker.done.connect(thread.quit)
        worker.failed.connect(thread.quit)
        self._eval_threads.add(thread)
        thread.finished.connect(lambda: self._eval_threads.discard(thread))
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.start()

    def _eval_worker_done(self, m):
        w = self.sender()
        if getattr(w, "_tok", None) == self._eval_token:   # актуальный результат
            w._on_ok(m)

    def _eval_worker_failed(self, msg):
        w = self.sender()
        if getattr(w, "_tok", None) == self._eval_token:
            self.v.set_status("Ошибка анализа")
            self.v.show_error(msg)

    def _on_evaluated(self, text, m):
        self.v.set_eval_result(text, m)
        self.v.set_status("Оценка готова")

    # ---------- выбор кандидата в таблице (вкладка «Генерация») ----------
    def on_select(self, row):
        if 0 <= row < len(self.last_scored):
            text, m = self.last_scored[row]
            self._current_gen = (text, m)
            self.v.set_gen_result(text, m)
