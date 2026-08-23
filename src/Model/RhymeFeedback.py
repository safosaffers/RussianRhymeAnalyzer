# Model/RhymeFeedback.py
# Из результата детектора рифмы собираем текстовую подсказку для ИИ:
# какие окончания строк хорошо рифмуются (оставить), а какие — нет
# (перерифмовать). Без Qt — чистая логика.
from collections import OrderedDict


def line_endings(m: dict) -> list:
    """Последние слова строк с цветом их рифмы: [(номер, слово, цвет|None)]."""
    ends = []
    for i, segs in enumerate(m.get("colored_lines") or [], 1):
        full = "".join(s for s, _ in segs).strip()
        words = full.split()
        if not words:
            continue
        color = None
        for s, c in segs:          # цвет последнего окрашенного сегмента = рифма
            if c and s.strip():
                color = c
        ends.append((i, words[-1], color))
    return ends


def rhyme_split(m: dict) -> tuple:
    """Разделить строки на созвучные группы (2 и более строк одного цвета) и
    одиночные, которым пары не нашлось. Одиночные - это и есть то, что чинится.

    Отделено от rhyme_feedback: вызывающему бывает нужно решение (есть ли что
    править), а не готовый текст подсказки."""
    ends = line_endings(m)
    groups = OrderedDict()
    for i, w, c in ends:
        if c:
            groups.setdefault(c, []).append((i, w))
    good = [mem for mem in groups.values() if len(mem) >= 2]
    used = {i for mem in good for i, _ in mem}
    unrhymed = [(i, w) for i, w, _ in ends if i not in used]
    return good, unrhymed


def rhyme_feedback(m: dict, scheme: str = None) -> str:
    """`m` — словарь детектора (с ключом colored_lines). Возвращает строку-разбор."""
    good, bad = rhyme_split(m)
    parts = []
    if scheme:
        parts.append(f"Целевая схема рифмовки: {scheme}.")
    if good:
        g = "; ".join("строки " + "–".join(str(i) for i, _ in mem)
                      + " (" + ", ".join(w for _, w in mem) + ")" for mem in good)
        parts.append("Хорошо рифмуются — ОСТАВЬ эти окончания: " + g + ".")
    if bad:
        b = ", ".join(f"строка {i} («{w}»)" for i, w in bad)
        parts.append("НЕ рифмуются — перепиши, чтобы зарифмовать: " + b + ".")
    if not good and not bad:
        parts.append("Рифмовка слабая по всей строфе — улучшить целиком.")
    return " ".join(parts)
