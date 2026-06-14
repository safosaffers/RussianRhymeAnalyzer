# Model/RhymeEvaluator.py
import os

ACUTE = "́"   # combining acute accent — метка основного ударения в выводе RPST
VOWELS = set("аеёиоуыэюя")

# палитра для подсветки рифм (по одному цвету на группу созвучных окончаний);
# светлые тона с тёмным текстом — читаются и на светлой, и на тёмной теме
RHYME_COLORS = ["#ffd54f", "#81c784", "#64b5f6", "#e57373",
                "#ba68c8", "#4db6ac", "#ff8a65", "#a1887f"]


def _strip_to_letters(s: str) -> str:
    return "".join(ch for ch in s.lower() if ch.isalpha() and ch != ACUTE)


def rhyme_tail(stressed_line: str) -> str:
    """Рифмующийся хвост строки = от последней ударной гласной до конца.

    В выводе RPST символ U+0301 стоит сразу ПОСЛЕ ударной гласной.
    Если ударение не размечено — берём хвост от последней гласной.
    """
    s = stressed_line.lower()
    idx = s.rfind(ACUTE)
    if idx > 0:
        tail = s[idx - 1:]            # ударная гласная + всё после
    else:
        # запасной вариант: последняя гласная в строке
        letters = _strip_to_letters(s)
        pos = max((letters.rfind(v) for v in VOWELS), default=-1)
        return letters[pos:] if pos >= 0 else letters
    return _strip_to_letters(tail)


def _cons_after(tail: str) -> str:
    """Согласные после ударной гласной (tail[0] — ударная гласная)."""
    return "".join(c for c in tail[1:] if c not in VOWELS)


def rhyme_match(t1: str, t2: str) -> float:
    """Степень созвучия двух рифмующихся хвостов: 0 / 0.6 / 0.9 / 1.0.

    Русская рифма опирается на ударную гласную и согласный «скелет» после
    неё; финальная безударная гласная может отличаться (единственный/таинственной).
    """
    if not t1 or not t2:
        return 0.0
    if t1 == t2:
        return 1.0
    if t1[0] == t2[0]:                       # совпадает ударная гласная
        c1, c2 = _cons_after(t1), _cons_after(t2)
        if c1 == c2:                         # совпал согласный скелет
            return 0.9
        if c1[:2] == c2[:2] or t1[-2:] == t2[-2:]:
            return 0.6
    return 0.0


def _scheme_for(n: int, scheme: str) -> str:
    """Развернуть схему ('ABAB') под n строк (повтор/обрезка)."""
    scheme = (scheme or "ABAB").upper()
    if not scheme:
        scheme = "ABAB"
    return (scheme * (n // len(scheme) + 1))[:n]


def scheme_accuracy(tails: list[str], scheme: str, thr: float = 0.5) -> float:
    """Доля верно срифмованных пар для заданной схемы рифмовки."""
    n = len(tails)
    if n < 2:
        return 0.0
    sch = _scheme_for(n, scheme)
    groups: dict[str, list[int]] = {}
    for i, c in enumerate(sch):
        groups.setdefault(c, []).append(i)
    ok = total = 0
    for idxs in groups.values():
        for a in range(len(idxs)):
            for b in range(a + 1, len(idxs)):
                total += 1
                if rhyme_match(tails[idxs[a]], tails[idxs[b]]) >= thr:
                    ok += 1
    return ok / total if total else 0.0


def syllable_count(s: str) -> int:
    """Число слогов = число гласных (для русского)."""
    return sum(1 for ch in s.lower() if ch in VOWELS)


def clausula_split(stressed_line: str) -> tuple[str, str]:
    """Разбить строку на (начало, клаузулу).

    Клаузула — рифмующееся окончание от последней ударной гласной до конца
    строки (именно её и подсвечиваем). Возвращается исходный текст (с ударением
    и пунктуацией), а не очищенный.
    """
    idx = stressed_line.rfind(ACUTE)
    if idx > 0:
        start = idx - 1                        # позиция ударной гласной
    else:
        low = stressed_line.lower()
        positions = [i for i, ch in enumerate(low) if ch in VOWELS]
        start = positions[-1] if positions else len(stressed_line)
    return stressed_line[:start], stressed_line[start:]


def group_rhymes(tails: list[str], thr: float = 0.5) -> dict[int, str]:
    """Сгруппировать строки по созвучию окончаний и присвоить цвет.

    Возвращает отображение «индекс строки -> цвет» только для строк, у которых
    есть рифмующаяся пара (одиночные окончания не подсвечиваются).
    """
    groups: list[list[int]] = []
    for i, t in enumerate(tails):
        if not t:
            continue
        for g in groups:
            if rhyme_match(t, tails[g[0]]) >= thr:
                g.append(i)
                break
        else:
            groups.append([i])
    color_of: dict[int, str] = {}
    k = 0
    for g in groups:
        if len(g) >= 2:                         # подсвечиваем только реальные рифмы
            color = RHYME_COLORS[k % len(RHYME_COLORS)]
            k += 1
            for idx in g:
                color_of[idx] = color
    return color_of


def analyze_rhyme_coloring(stressed: str) -> dict:
    """Разметить рифмы по слогам: подсветка клаузул + доля зарифмованных слогов.

    rhyme_percent = (слоги в подсвеченных клаузулах) / (все слоги).
    """
    lines = [ln for ln in stressed.splitlines() if ln.strip()]
    tails = [rhyme_tail(ln) for ln in lines]
    color_of = group_rhymes(tails)

    colored_lines = []     # для каждой строки: [(текст, цвет|None), ...]
    legend: dict[str, list[str]] = {}
    total_syl = rhymed_syl = 0
    for i, ln in enumerate(lines):
        prefix, clausula = clausula_split(ln)
        total_syl += syllable_count(ln)
        color = color_of.get(i)
        if color:
            rhymed_syl += syllable_count(clausula)
            legend.setdefault(color, []).append(clausula.strip())
        colored_lines.append([(prefix, None), (clausula, color)])

    pct = rhymed_syl / total_syl if total_syl else 0.0
    return {
        "colored_lines": colored_lines,
        "legend": legend,
        "total_syllables": total_syl,
        "rhymed_syllables": rhymed_syl,
        "rhyme_percent": pct,
    }


class RhymeEvaluator:
    """Обёртка над RussianPoetryScansionTool (RPST).

    Даёт готовую оценку поэтичности (`score`), размер, схему рифмовки RPST,
    разметку ударений, а также собственную метрику `rhyme_accuracy`
    (доделанный распознаватель рифм) поверх размеченных ударений.
    """

    SCHEMES = ("ABAB", "AABB", "ABBA")

    def __init__(self, models_dir: str = None):
        self.models_dir = models_dir
        self._tool = None   # ленивая загрузка моделей (медленная)

    def _ensure(self):
        if self._tool is None:
            import russian_scansion
            # явно передаём models_dir: на Python 3.12 дефолтный путь в RPST
            # падает (files(...).joinpath('') -> StopIteration)
            md = self.models_dir or os.path.join(
                os.path.dirname(russian_scansion.__file__), "models")
            self._tool = russian_scansion.create_rpst_instance(models_dir=md)

    def evaluate(self, text: str, target_scheme: str = "ABAB") -> dict:
        self._ensure()
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        if not lines:
            return self._empty()
        try:
            sc = self._tool.align(lines)
            stressed = sc.get_stressed_lines(show_secondary_accentuation=False)
            score = float(sc.score)
            meter = sc.meter
            rpst_scheme = sc.rhyme_scheme
        except Exception as e:
            return {**self._empty(), "error": str(e)}

        tails = [rhyme_tail(ln) for ln in stressed.splitlines() if ln.strip()]
        rhyme_accuracy = scheme_accuracy(tails, target_scheme)
        # лучшая из типовых схем (детекция фактической рифмовки)
        detected = max(self.SCHEMES, key=lambda s: scheme_accuracy(tails, s))
        if scheme_accuracy(tails, detected) == 0.0:
            detected = None   # рифм не обнаружено — схему не показываем

        coloring = analyze_rhyme_coloring(stressed)
        # итоговый ранжирующий балл: доля зарифмованных слогов + поэтичность RPST
        rhyme_score = (0.6 * coloring["rhyme_percent"]
                       + 0.4 * min(max(score, 0.0), 1.0))
        return {
            "score": score,
            "meter": meter,
            "rpst_scheme": rpst_scheme,
            "stressed": stressed,
            "tails": tails,
            "rhyme_accuracy": rhyme_accuracy,
            "detected_scheme": detected,
            "rhyme_score": rhyme_score,
            **coloring,
        }

    @staticmethod
    def _empty() -> dict:
        return {"score": 0.0, "meter": None, "rpst_scheme": None,
                "stressed": "", "tails": [], "rhyme_accuracy": 0.0,
                "detected_scheme": None, "rhyme_score": 0.0,
                "colored_lines": [], "legend": {},
                "total_syllables": 0, "rhymed_syllables": 0, "rhyme_percent": 0.0}
