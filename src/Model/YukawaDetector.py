# Model/YukawaDetector.py
# Авторский детектор рифм на потенциале Юкавы.
# ЯДРО (энергия слога -> схожесть -> экранирование Юкавой -> резонанс -> матрица связей S)
# из detector.py. Все константы вынесены в параметры (DEFAULTS) для настройки из UI.
# Адаптация для приложения: из S выделяются ГРУППЫ РИФМ (компоненты связности по порогу).
import numpy as np

from Model.RhymeEvaluator import RHYME_COLORS

vowels = set("аеёиоуыэюя")
consonants = set("бвгджзйклмнпрстфхцчшщъь")


# ============================================================
# ЯДРО (параметризованное)
# ============================================================
def split_into_syllables(word):
    """Слогораздел: каждый слог = одна гласная + предшествующие согласные.
    Регистр исходных букв сохраняется (для показа)."""
    syllables = []
    current = ""
    for char in word:
        low = char.lower()
        if low in consonants:
            current += char
        elif low in vowels:
            current += char
            syllables.append(current)
            current = ""
        else:
            if current:
                current += char
    if current:
        if syllables:
            syllables[-1] += current
        else:
            syllables.append(current)
    return syllables


def syllable_energy(syllable, voiced_mult=2.0, voiceless_mult=0.5):
    """«Эффективная масса» слога: гласная — база, согласные — множители."""
    vowel_energy = {
        'а': 1.0, 'я': 1.2, 'о': 2.0, 'ё': 2.2, 'у': 3.0, 'ю': 3.2,
        'ы': 4.0, 'э': 5.0, 'е': 5.2, 'и': 6.0,
    }
    voiced = set('бвгджзлмнр')
    voiceless = set('пфктшсхцчщ')
    base = 0.0
    multiplier = 1.0
    shift = 0.0
    for char in syllable.lower():
        if char in vowel_energy:
            base = vowel_energy[char]
        elif char in voiced:
            multiplier *= voiced_mult
        elif char in voiceless:
            multiplier *= voiceless_mult
        elif char in 'ьъ':
            shift += 0.5
    return base * multiplier + shift


def manhattan_distance(p1, p2):
    return abs(p1[0] - p2[0]) + abs(p1[1] - p2[1])


def yukawa_kernel(d, lam=0.8):
    """Экранированное взаимодействие: подавляет дальние связи."""
    if d == 0:
        return 1.0
    return np.exp(-lam * d) / d


def syllable_similarity(s1, s2, vowel_weight=0.6):
    """Схожесть слогов: совпадение гласной + доля общих согласных."""
    s1, s2 = s1.lower(), s2.lower()
    v1 = [c for c in s1 if c in vowels]
    v2 = [c for c in s2 if c in vowels]
    c1 = [c for c in s1 if c in consonants]
    c2 = [c for c in s2 if c in consonants]
    vowel_score = 1.0 if v1 == v2 else 0.0
    if not c1 and not c2:
        cons_score = 1.0
    elif not c1 or not c2:
        cons_score = 0.0
    else:
        common = len(set(c1) & set(c2))
        cons_score = common / max(len(set(c1)), len(set(c2)))
    return vowel_weight * vowel_score + (1.0 - vowel_weight) * cons_score


def apply_resonance(S, gamma=0.3):
    """Тройные корреляции (ритм): усиливаем связи с общими «друзьями»."""
    S_new = S.copy()
    N = S.shape[0]
    for a in range(N):
        for b in range(a + 1, N):
            resonance = 0.0
            for c in range(N):
                if c != a and c != b:
                    resonance += S[a, c] * S[b, c]
            resonance /= N
            S_new[a, b] += gamma * resonance
            S_new[b, a] = S_new[a, b]
    return S_new


# ============================================================
# ОБЁРТКА ДЛЯ ПРИЛОЖЕНИЯ
# ============================================================
class YukawaDetector:
    """Детектор рифм по матрице связей Юкавы. Интерфейс — как у RhymeEvaluator.

    Все настраиваемые константы — в DEFAULTS; переопределяются через
    evaluate(..., params=...) (для подбора из UI)."""

    DEFAULTS = {
        "use_distance": True,   # учитывать экранирование по расстоянию
        "lam": 0.8,             # λ — сила экранирования (больше → дальние связи слабее)
        "gamma": 0.3,           # γ — вес резонанса (общие «друзья»)
        "link_ratio": 0.6,      # порог рифмы как доля от максимума связи
        "vowel_weight": 0.6,    # вес совпадения гласной в схожести (согласные = 1−вес)
        "use_energy": True,     # домножать связь на энергии слогов
        "energy_div": 10.0,     # делитель произведения энергий
        "voiced_mult": 2.0,     # множитель энергии для звонких согласных
        "voiceless_mult": 0.5,  # множитель энергии для глухих согласных
    }

    def evaluate(self, text: str, target_scheme: str = "ABAB",
                 params: dict = None) -> dict:
        p = dict(self.DEFAULTS)
        if params:
            p.update({k: v for k, v in params.items() if v is not None})

        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        nodes = []            # [(i, j, syllable_text)]
        line_render = []      # для каждой строки: [('syl', gidx) | ('space', None)]
        for i, line in enumerate(lines):
            items = []
            col = 0
            for wi, word in enumerate(line.split()):
                if wi > 0:
                    items.append(("space", None))
                for syl in split_into_syllables(word):
                    items.append(("syl", len(nodes)))
                    nodes.append((i, col, syl))
                    col += 1
            line_render.append(items)

        N = len(nodes)
        color_of, groups = ({}, [])
        if N >= 2:
            color_of, groups = self._detect(nodes, N, p)

        colored_lines = []
        for items in line_render:
            segs = []
            for kind, gidx in items:
                if kind == "space":
                    segs.append((" ", None))
                else:
                    segs.append((nodes[gidx][2], color_of.get(gidx)))
            colored_lines.append(segs)

        legend = {}
        for gidx, color in color_of.items():
            legend.setdefault(color, []).append(nodes[gidx][2])

        rhymed = len(color_of)
        pct = rhymed / N if N else 0.0
        return {
            "score": 0.0, "meter": None, "rpst_scheme": None,
            "stressed": "", "tails": [],
            "rhyme_accuracy": pct, "detected_scheme": None,
            "rhyme_score": pct, "rhyme_percent": pct,
            "rhymed_syllables": rhymed, "total_syllables": N,
            "colored_lines": colored_lines, "legend": legend,
            "method": "yukawa", "num_groups": len(groups), "params": p,
        }

    @staticmethod
    def _detect(nodes, N, p):
        energy = [syllable_energy(t, p["voiced_mult"], p["voiceless_mult"])
                  for (_, _, t) in nodes]
        S = np.zeros((N, N))
        for a in range(N):
            for b in range(a + 1, N):
                d = manhattan_distance(nodes[a][:2], nodes[b][:2])
                sim = syllable_similarity(nodes[a][2], nodes[b][2], p["vowel_weight"])
                k = yukawa_kernel(d, p["lam"]) if p["use_distance"] else 1.0
                ef = abs(energy[a] * energy[b]) / p["energy_div"] if p["use_energy"] else 1.0
                S[a, b] = S[b, a] = sim * k * ef
        for a in range(N):
            S[a, a] = 1.0
        S = apply_resonance(S, gamma=p["gamma"])
        mx = S.max()
        if mx > 0:
            S = S / mx

        off = S.copy()
        np.fill_diagonal(off, 0.0)
        peak = off.max()
        thr = p["link_ratio"] * peak
        parent = list(range(N))

        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        if peak > 0:
            for a in range(N):
                for b in range(a + 1, N):
                    if off[a, b] >= thr and off[a, b] > 0:
                        parent[find(a)] = find(b)

        comps = {}
        for x in range(N):
            comps.setdefault(find(x), []).append(x)
        groups = [m for m in comps.values() if len(m) >= 2]

        color_of = {}
        for k, members in enumerate(groups):
            color = RHYME_COLORS[k % len(RHYME_COLORS)]
            for gidx in members:
                color_of[gidx] = color
        return color_of, groups
