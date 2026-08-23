# Model/Model.py
import importlib.util
import os
import sys
from pathlib import Path

from Model.Generator import StubGenerator, GenParams
from Model.LLMGenerator import LLMGenerator
from Model.OpenAICompatGenerator import OpenAICompatGenerator
from Model.RhymeEvaluator import RhymeEvaluator
from Model.YukawaDetector import YukawaDetector
from Model.RhymeFeedback import rhyme_feedback, rhyme_split


class Model:
    """Фасад бизнес-логики: связывает генераторы и детекторы рифм.

    Detector выбирается параметром method: 'rpst' (RPST + хвосты) или
    'yukawa' (авторский алгоритм). У обоих один интерфейс — .evaluate(text, scheme).
    """

    def __init__(self, poems_dir: str = None, models_dir: str = None):
        if getattr(sys, "frozen", False):            # сборка PyInstaller
            root = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
        else:
            root = Path(__file__).resolve().parents[2]   # корень репозитория __RHYMER
        poems_dir = poems_dir or str(root / "poems")
        self.evaluator = RhymeEvaluator(models_dir)   # models_dir=None -> авто
        self.yukawa = YukawaDetector()
        self.stub = StubGenerator(poems_dir)
        self.llm = self._make_llm()

    @staticmethod
    def _make_llm():
        """Выбор ИИ-генератора по RHYMER_PROVIDER (anthropic|gemini|deepseek).
        None, если для выбранного провайдера нет ключа или пакета SDK."""
        provider = os.environ.get("RHYMER_PROVIDER", "anthropic").lower()
        if provider == "anthropic":
            return LLMGenerator() if LLMGenerator.available() else None
        if OpenAICompatGenerator.available(provider):
            return OpenAICompatGenerator(provider)
        return None

    def reload_llm(self):
        """Пересобрать ИИ-генератор (после смены провайдера/ключа в настройках)."""
        self.llm = self._make_llm()

    @property
    def llm_available(self) -> bool:
        return self.llm is not None

    @staticmethod
    def rpst_available() -> bool:
        """Есть ли RPST-детектор. В облегчённой сборке (без torch/моделей)
        пакет russian_scansion не вшит — определяем без его импорта."""
        return importlib.util.find_spec("russian_scansion") is not None

    @property
    def llm_name(self) -> str:
        """Человекочитаемое имя активного ИИ-генератора (для статуса в UI)."""
        return getattr(self.llm, "label", "ИИ") if self.llm else ""

    @property
    def provider(self) -> str:
        """Выбранный провайдер ИИ (для подсказок в UI, даже если ключа нет)."""
        return os.environ.get("RHYMER_PROVIDER", "anthropic").lower()

    def _detector(self, method: str):
        return self.yukawa if method == "yukawa" else self.evaluator

    def _score(self, det, text, scheme, yk_params):
        """Единый вызов оценки: Юкаве передаём настраиваемые параметры."""
        if det is self.yukawa:
            return det.evaluate(text, scheme, yk_params)
        return det.evaluate(text, scheme)

    def evaluate(self, text: str, target_scheme: str = "ABAB",
                 method: str = "yukawa", yk_params: dict = None) -> dict:
        return self._score(self._detector(method), text, target_scheme, yk_params)

    def improve_poem(self, text: str, params: GenParams, method: str = "yukawa",
                     yk_params: dict = None):
        """Ручное улучшение выбранного варианта: оцениваем рифму, помечаем хорошие
        и плохие окончания и просим ИИ перерифмовать плохие (с проверкой
        читаемости и формы). Возвращает (улучшенный_текст, метрики) или None."""
        if not self.llm:
            return None
        det = self._detector(method)
        m = self._score(det, text, params.scheme, yk_params)
        feedback = rhyme_feedback(m, params.scheme)
        improved = self.llm.improve(text, feedback, params)
        if not improved:
            return None
        im = self._score(det, improved, params.scheme, yk_params)
        im["corrected"] = True
        # ИИ может вернуть текст без изменений (например, классику из корпуса он
        # не переписывает). Помечаем, чтобы не показывать «новый» результат с
        # другим %, который сбивает с толку.
        im["unchanged"] = improved.strip() == text.strip()
        return improved, im

    @staticmethod
    def _needs_rework(m: dict) -> bool:
        """Нужен ли проход самокоррекции: есть незарифмованные строки, либо
        детектор действительно проверяет схему и она не выдержана.

        rhyme_accuracy в условие напрямую не берём: у Юкавы это доля
        зарифмованных слогов (схема не проверяется, detected_scheme=None), она
        почти никогда не равна 1.0 — по такому условию правка запускалась бы
        всегда, добавляя лишний вызов API к каждой генерации."""
        _, unrhymed = rhyme_split(m)
        if unrhymed:
            return True
        return bool(m.get("detected_scheme")) and m.get("rhyme_accuracy", 1.0) < 1.0

    def generate_best(self, params: GenParams, n: int = 6, use_llm: bool = False,
                      method: str = "yukawa", yk_params: dict = None) -> list[tuple[str, dict]]:
        """Best-of-N: сгенерировать n кандидатов, оценить выбранным детектором,
        вернуть отсортированными по убыванию rhyme_score (лучший — первый).

        Для ИИ-генератора добавляется один проход самокоррекции по фидбэку
        детектора — но только если детектору есть на что пожаловаться.
        """
        det = self._detector(method)
        gen = self.llm if (use_llm and self.llm) else self.stub
        cands = gen.generate(params, n)
        scored = [(c, self._score(det, c, params.scheme, yk_params)) for c in cands]
        scored.sort(key=lambda x: x[1]["rhyme_score"], reverse=True)

        if use_llm and self.llm and scored:
            best_text, best_m = scored[0]
            if self._needs_rework(best_m):
                feedback = rhyme_feedback(best_m, params.scheme)
                improved = self.llm.improve(best_text, feedback, params)
                if improved:
                    im = self._score(det, improved, params.scheme, yk_params)
                    im["corrected"] = True
                    scored.append((improved, im))
                    scored.sort(key=lambda x: x[1]["rhyme_score"], reverse=True)
        return scored
