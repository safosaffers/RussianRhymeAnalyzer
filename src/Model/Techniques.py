# Model/Techniques.py
# Твёрдые требования к технике стиха: акростих, телестих, кольцо, липограмма и т.д.
# Каждое требование умеет две вещи - сказать себя словами для промпта и
# ПРОВЕРИТЬСЯ детерминированно. Проверка одна и та же и после генерации, и на
# вкладке оценки: требование, которое нельзя проверить, требованием не считается.
import re

_WORD_RE = re.compile(r"[^\W\d_]+", re.UNICODE)


def _lines(text: str) -> list[str]:
    return [ln.strip() for ln in (text or "").splitlines() if ln.strip()]


def _letters(s: str) -> str:
    return "".join(ch for ch in s if ch.isalpha())


def _edge_letters(lines: list[str], first: bool) -> str:
    """Первые (или последние) буквы строк — из них складывается слово."""
    out = []
    for ln in lines:
        letters = _letters(ln)
        if letters:
            out.append(letters[0] if first else letters[-1])
    return "".join(out).upper()


def _cmp_word(got: str, want: str, where: str) -> tuple[bool, str]:
    want = _letters(want).upper()
    if not want:
        return True, ""
    if len(got) != len(want):
        return False, (f"{where}: строк {len(got)}, а в слове «{want}» "
                       f"{len(want)} букв — сложилось «{got}»")
    bad = [i + 1 for i, (a, b) in enumerate(zip(got, want)) if a != b]
    if bad:
        pairs = ", ".join(f"строка {i}: нужна «{want[i-1]}», стоит «{got[i-1]}»"
                          for i in bad)
        return False, f"{where}: сложилось «{got}» вместо «{want}» ({pairs})"
    return True, f"{where}: «{got}»"


def _check_acrostic(text, param):
    return _cmp_word(_edge_letters(_lines(text), True), param, "по первым буквам")


def _check_telestich(text, param):
    return _cmp_word(_edge_letters(_lines(text), False), param, "по последним буквам")


def _check_acrotelestich(text, param):
    """Одно слово — читается и по первым, и по последним буквам; два через
    пробел или запятую — первое по первым, второе по последним."""
    parts = [p for p in re.split(r"[,\s]+", (param or "").strip()) if p]
    first = parts[0] if parts else ""
    last = parts[1] if len(parts) > 1 else first
    ok1, d1 = _check_acrostic(text, first)
    ok2, d2 = _check_telestich(text, last)
    return ok1 and ok2, "; ".join(d for d in (d1, d2) if d)


def _check_ring(text, param):
    lines = _lines(text)
    if len(lines) < 2:
        return False, "кольцо: в стихе меньше двух строк"
    a, b = lines[0].lower().rstrip(".,;:!?-—"), lines[-1].lower().rstrip(".,;:!?-—")
    return (a == b, "кольцо: первая и последняя строки совпадают" if a == b
            else f"кольцо: последняя строка «{lines[-1]}» не повторяет первую")


def _check_anaphora(text, param):
    lines = _lines(text)
    want = (param or "").strip().lower()
    if not want:
        heads = {(_WORD_RE.findall(ln.lower()) or [""])[0] for ln in lines}
        ok = len(heads) == 1
        return ok, ("анафора: все строки начинаются одинаково" if ok
                    else "анафора: строки начинаются по-разному")
    bad = [i + 1 for i, ln in enumerate(lines)
           if not ln.lower().startswith(want)]
    return (not bad, "анафора выдержана" if not bad
            else f"анафора «{param}»: не начинаются строки {bad}")


def _check_refrain(text, param):
    lines = [ln.lower().strip() for ln in _lines(text)]
    want = (param or "").strip().lower()
    if want:
        n = sum(1 for ln in lines if want in ln)
        return (n >= 2, f"рефрен «{param}»: повторов {n}")
    dup = [ln for ln in set(lines) if lines.count(ln) >= 2]
    return (bool(dup), "рефрен: есть повторяющаяся строка" if dup
            else "рефрен: ни одна строка не повторяется")


def _check_lipogram(text, param):
    ban = _letters(param).lower()
    if not ban:
        return True, ""
    hit = [i + 1 for i, ln in enumerate(_lines(text))
           if any(ch in ln.lower() for ch in ban)]
    return (not hit, f"липограмма без «{ban}»: выдержана" if not hit
            else f"липограмма: буква «{ban}» встречается в строках {hit}")


def _check_tautogram(text, param):
    letter = _letters(param).lower()[:1]
    bad = []
    for i, ln in enumerate(_lines(text), 1):
        words = _WORD_RE.findall(ln.lower())
        if letter and any(not w.startswith(letter) for w in words):
            bad.append(i)
    return (not bad, f"тавтограмма на «{letter}»: выдержана" if not bad
            else f"тавтограмма на «{letter}»: нарушена в строках {bad}")


def _check_required_words(text, param):
    want = [w.strip().lower() for w in re.split(r"[,\n]+", param or "") if w.strip()]
    low = (text or "").lower()
    missing = [w for w in want if w not in low]
    return (not missing, "обязательные слова на месте" if not missing
            else "не хватает слов: " + ", ".join(missing))


# id -> описание. demand() говорит требование словами для промпта.
TECHNIQUES = {
    "acrostic": {
        "label": "Акростих", "param": "слово",
        "hint": "первые буквы строк складывают слово",
        "check": _check_acrostic,
        "demand": lambda p: (
            f"АКРОСТИХ: первые буквы строк должны сложить слово «{p.upper()}» "
            f"(строка 1 начинается с «{p[0].upper()}»"
            + "".join(f", строка {i+1} — с «{c.upper()}»" for i, c in enumerate(p[1:], 1))
            + f"). Ровно {len(_letters(p))} строк."),
    },
    "telestich": {
        "label": "Телестих", "param": "слово",
        "hint": "последние буквы строк складывают слово",
        "check": _check_telestich,
        "demand": lambda p: (
            f"ТЕЛЕСТИХ: последние буквы строк должны сложить слово «{p.upper()}» "
            f"(строка 1 кончается на «{p[0].upper()}»"
            + "".join(f", строка {i+1} — на «{c.upper()}»" for i, c in enumerate(p[1:], 1))
            + f"). Ровно {len(_letters(p))} строк."),
    },
    "acrotelestich": {
        "label": "Акротелестих", "param": "слово или два через пробел",
        "hint": "слово читается и по первым, и по последним буквам",
        "check": _check_acrotelestich,
        "demand": lambda p: (
            "АКРОТЕЛЕСТИХ: слово читается и по первым буквам строк, и по "
            f"последним. Задано: «{p.upper()}». Если слов два — первое по "
            "первым буквам, второе по последним. Каждая строка обязана "
            "одновременно начинаться и кончаться нужной буквой."),
    },
    "ring": {
        "label": "Кольцо", "param": "",
        "hint": "последняя строка повторяет первую",
        "check": _check_ring,
        "demand": lambda p: "КОЛЬЦО: последняя строка дословно повторяет первую.",
    },
    "anaphora": {
        "label": "Анафора", "param": "слово (необязательно)",
        "hint": "строки начинаются одинаково",
        "check": _check_anaphora,
        "demand": lambda p: (f"АНАФОРА: каждая строка начинается со слова «{p}»."
                             if p else "АНАФОРА: все строки начинаются одинаково."),
    },
    "refrain": {
        "label": "Рефрен", "param": "строка (необязательно)",
        "hint": "строка повторяется в стихе",
        "check": _check_refrain,
        "demand": lambda p: (f"РЕФРЕН: строка «{p}» повторяется не меньше двух раз."
                             if p else "РЕФРЕН: одна из строк повторяется дословно."),
    },
    "lipogram": {
        "label": "Липограмма", "param": "запрещённые буквы",
        "hint": "буква не встречается ни разу",
        "check": _check_lipogram,
        "demand": lambda p: f"ЛИПОГРАММА: буква «{p}» не должна встретиться ни разу.",
    },
    "tautogram": {
        "label": "Тавтограмма", "param": "буква",
        "hint": "все слова на одну букву",
        "check": _check_tautogram,
        "demand": lambda p: f"ТАВТОГРАММА: все слова начинаются с буквы «{p}».",
    },
    "required_words": {
        "label": "Обязательные слова", "param": "слова через запятую",
        "hint": "слова должны встретиться в тексте",
        "check": _check_required_words,
        "demand": lambda p: f"ОБЯЗАТЕЛЬНЫЕ СЛОВА: в стихе должны быть {p}.",
    },
}


def required_lines(reqs: list) -> int | None:
    """Сколько строк требует техника (акростих задаёт длину жёстко)."""
    for r in reqs or []:
        if r.get("id") in ("acrostic", "telestich", "acrotelestich"):
            word = re.split(r"[,\s]+", (r.get("param") or "").strip())[0]
            if _letters(word):
                return len(_letters(word))
    return None


def demands_text(reqs: list) -> str:
    """Требования словами — уходит в промпт генерации и правки."""
    out = []
    for r in reqs or []:
        t = TECHNIQUES.get(r.get("id"))
        if t:
            out.append("- " + t["demand"](r.get("param") or ""))
    return "\n".join(out)


def check_all(text: str, reqs: list) -> list:
    """Проверка техники: [{id, label, ok, detail}]. Пустой список — требований нет."""
    res = []
    for r in reqs or []:
        t = TECHNIQUES.get(r.get("id"))
        if not t:
            continue
        ok, detail = t["check"](text, r.get("param") or "")
        res.append({"id": r["id"], "label": t["label"], "ok": bool(ok),
                    "detail": detail})
    return res


def failures_text(results: list) -> str:
    """Нарушения одной строкой — для подсказки модели при переписывании."""
    bad = [r for r in results or [] if not r["ok"]]
    return "; ".join(f"{r['label']} нарушена -> {r['detail']}" for r in bad)
