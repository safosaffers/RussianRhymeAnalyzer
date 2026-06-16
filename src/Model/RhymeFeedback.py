# Model/RhymeFeedback.py
# Из результата детектора рифмы собираем текстовую подсказку для ИИ:
# какие окончания строк хорошо рифмуются (оставить), а какие — нет
# (перерифмовать). Без Qt — чистая логика.
from collections import OrderedDict


def rhyme_feedback(m: dict, scheme: str = None) -> str:
    """`m` — словарь детектора (с ключом colored_lines). Возвращает строку-разбор."""
    lines = m.get("colored_lines") or []
    ends = []   # (номер строки, последнее слово, цвет рифмы | None)
    for i, segs in enumerate(lines, 1):
        full = "".join(s for s, _ in segs).strip()
        words = full.split()
        if not words:
            continue
        color = None
        for s, c in segs:          # цвет последнего окрашенного сегмента = рифма
            if c and s.strip():
                color = c
        ends.append((i, words[-1], color))

    groups = OrderedDict()
    for i, w, c in ends:
        if c:
            groups.setdefault(c, []).append((i, w))

    good, used = [], set()
    for c, mem in groups.items():
        if len(mem) >= 2:          # рифма «работает», если ≥2 строк созвучны
            good.append(mem)
            used.update(i for i, _ in mem)
    bad = [(i, w) for i, w, _ in ends if i not in used]

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
