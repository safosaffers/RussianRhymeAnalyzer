# Model/Generator.py
import os
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class GenParams:
    """Параметры генерации стиха."""
    theme: str = ""          # тема (для реальной модели; заглушка её игнорирует)
    n_lines: int = 4         # сколько строк в стихе
    meter: str = "ямб"       # желаемый размер
    scheme: str = "ABAB"     # желаемая схема рифмовки
    spec: object = None      # PoemSpec: карта смысла; заглушка её игнорирует
    techniques: list = field(default_factory=list)   # [{id, param}] — твёрдые требования


class Generator(ABC):
    """Единый интерфейс генератора. Реализации взаимозаменяемы:
    StubGenerator (день 1) и LLMGenerator (реальная модель) — позже."""

    @abstractmethod
    def generate(self, params: GenParams, n: int) -> list[str]:
        """Вернуть n кандидатов-стихов (каждый — строки через '\\n')."""
        raise NotImplementedError


class StubGenerator(Generator):
    """Генератор-заглушка на корпусе классики (poems/).

    Чтобы верификатору рифмы было что отбирать, кандидаты намеренно разного
    качества: часть — связные строфы из реальных стихов (хорошая рифма),
    часть — случайно собранные строки из разных стихов (рифмы почти нет).
    Это честно демонстрирует механику best-of-N: оценщик должен поднять
    наверх связную строфу.
    """

    def __init__(self, poems_dir: str):
        self.poems_dir = poems_dir
        self.stanzas: list[list[str]] = []   # строфы (списки строк)
        self.all_lines: list[str] = []       # все строки вперемешку
        self._load()

    def _load(self):
        if not os.path.isdir(self.poems_dir):   # каталог не вшит в сборку
            return
        for name in sorted(os.listdir(self.poems_dir)):
            path = os.path.join(self.poems_dir, name)
            if not os.path.isfile(path):
                continue
            with open(path, encoding="utf-8") as f:
                text = f.read()
            # строфы разделены пустой строкой
            for block in text.split("\n\n"):
                lines = [ln.strip() for ln in block.splitlines() if ln.strip()]
                if len(lines) >= 2:
                    self.stanzas.append(lines)
                    self.all_lines.extend(lines)

    def _coherent(self, n_lines: int) -> str:
        """Связный кандидат: реальная строфа нужной длины."""
        big = [s for s in self.stanzas if len(s) >= n_lines]
        stanza = random.choice(big if big else self.stanzas)
        return "\n".join(stanza[:n_lines])

    def _shuffled(self, n_lines: int) -> str:
        """Шумовой кандидат: случайные строки из разных мест."""
        return "\n".join(random.sample(self.all_lines, k=min(n_lines, len(self.all_lines))))

    def generate(self, params: GenParams, n: int) -> list[str]:
        if not self.stanzas:
            return []
        n_lines = max(2, params.n_lines)
        n_good = max(1, n // 2)
        cands = [self._coherent(n_lines) for _ in range(n_good)]
        cands += [self._shuffled(n_lines) for _ in range(n - n_good)]
        random.shuffle(cands)
        return cands
