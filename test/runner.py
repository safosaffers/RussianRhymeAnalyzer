#!/usr/bin/env python
"""Генерация тест-артефактов Rhymer для презентации.

Запуск:  venv/bin/python test/runner.py
Сеть и API-ключ НЕ нужны: используются детекторы рифм (Юкава + RPST, если
доступен) и генератор-заглушка из корпуса poems/.

Для каждого кейса создаётся папка test/<name>/:
  input.txt           — входной текст
  metrics.txt         — числовой вывод детекторов
  coloring.png        — раскраска рифм (Юкава, послогово)
  coloring_rpst.png   — раскраска рифм (RPST, по клаузулам) — если RPST доступен
Кейс генерации test/gen_zima/: gen_output.txt (ранжирование best-of-N),
best.txt (победитель), coloring.png.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

import matplotlib
matplotlib.use("Agg")          # headless-рендер без дисплея
import matplotlib.pyplot as plt
matplotlib.rcParams["font.family"] = "DejaVu Sans"   # поддерживает кириллицу

from Model.YukawaDetector import YukawaDetector
from Model.Generator import GenParams

TEST_DIR = os.path.join(ROOT, "test")

# классические четверостишия (public domain) — заведомо ABAB
EVAL_CASES = {
    "pushkin": ("ABAB",
                "Буря мглою небо кроет,\n"
                "Вихри снежные крутя;\n"
                "То, как зверь, она завоет,\n"
                "То заплачет, как дитя."),
    "lermontov": ("ABAB",
                  "Белеет парус одинокий\n"
                  "В тумане моря голубом!..\n"
                  "Что ищет он в стране далёкой?\n"
                  "Что кинул он в краю родном?"),
    "tyutchev": ("ABAB",
                 "Люблю грозу в начале мая,\n"
                 "Когда весенний, первый гром,\n"
                 "как бы резвяся и играя,\n"
                 "Грохочет в небе голубом."),
    # контроль: строки из разных стихов — рифмы почти нет (низкий %)
    "noise": ("ABAB",
              "Буря мглою небо кроет,\n"
              "Люблю грозу в начале мая,\n"
              "Что ищет он в стране далёкой?\n"
              "Когда весенний, первый гром,"),
}


def write(path: str, content: str):
    with open(path, "w", encoding="utf-8") as f:
        f.write(content.rstrip("\n") + "\n")


def fmt_metrics(m: dict) -> str:
    L = [f"метод: {m.get('method') or 'rpst'}",
         f"зарифмовано слогов: {m.get('rhyme_percent', 0):.0%} "
         f"({m.get('rhymed_syllables', 0)} из {m.get('total_syllables', 0)})"]
    if m.get("method") == "yukawa":
        L.append(f"групп рифм: {m.get('num_groups', 0)}")
        p = m.get("params", {})
        L.append(f"параметры: λ={p.get('lam')}, γ={p.get('gamma')}, "
                 f"порог={p.get('link_ratio')}")
    else:
        L.append(f"точность по схеме: {m.get('rhyme_accuracy', 0):.0%}")
        L.append(f"поэтичность RPST (score): {m.get('score', 0):.2f}")
        L.append(f"размер: {m.get('meter') or '—'}")
        L.append(f"схема RPST: {m.get('rpst_scheme') or '—'}  |  "
                 f"схема (детект.): {m.get('detected_scheme') or '—'}")
    leg = m.get("legend") or {}
    if leg:
        L.append("группы рифм: " + "  |  ".join(", ".join(ws) for ws in leg.values()))
    return "\n".join(L)


def render(colored_lines, title: str, out_path: str):
    """Рендер colored_lines ([(текст, цвет|None), ...] по строкам) в PNG.
    Та же раскраска, что и в UI, но картинкой (для слайдов)."""
    if not colored_lines:
        return
    max_chars = max(sum(len(t) for t, _ in line) for line in colored_lines) or 1
    n = len(colored_lines)
    fig = plt.figure(figsize=(max(8.0, 0.10 * max_chars + 2.0), 0.5 * n + 1.0), dpi=150)
    fig.patch.set_facecolor("white")
    ax = fig.add_axes([0, 0, 1, 1]); ax.axis("off")
    ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    renderer = fig.canvas.get_renderer()
    inv = ax.transAxes.inverted()
    ax.text(0.03, 0.96, title, fontsize=12, color="#333", va="top", ha="left",
            transform=ax.transAxes, weight="bold")
    top, line_h, fs = 0.84, 0.76 / max(n, 1), 15
    for i, segments in enumerate(colored_lines):
        y, x = top - i * line_h, 0.03
        for seg_text, color in segments:
            if seg_text == "":
                continue
            txt = ax.text(x, y, seg_text, fontsize=fs, va="center", ha="left",
                          transform=ax.transAxes, color="#111" if color else "#222",
                          bbox=(dict(boxstyle="round,pad=0.12", fc=color, ec="none")
                                if color else None))
            bb = txt.get_window_extent(renderer=renderer)
            x += inv.transform((bb.x1, bb.y0))[0] - inv.transform((bb.x0, bb.y0))[0]
    fig.savefig(out_path, facecolor="white", bbox_inches="tight")
    plt.close(fig)


def run_eval():
    yk = YukawaDetector()
    rpst, rpst_ok = None, False
    try:
        from Model.RhymeEvaluator import RhymeEvaluator
        rpst, rpst_ok = RhymeEvaluator(), True
    except Exception as e:   # noqa: BLE001
        print("RPST не импортирован:", e)

    for name, (scheme, poem) in EVAL_CASES.items():
        case = os.path.join(TEST_DIR, name)
        os.makedirs(case, exist_ok=True)
        write(os.path.join(case, "input.txt"), poem)

        ym = yk.evaluate(poem, scheme)
        parts = ["=== Юкава ===", fmt_metrics(ym)]
        render(ym["colored_lines"], f"{name}: раскраска рифм (Юкава)",
               os.path.join(case, "coloring.png"))

        if rpst_ok:
            try:
                rm = rpst.evaluate(poem, scheme)
                parts += ["", "=== RPST ===", fmt_metrics(rm)]
                render(rm["colored_lines"], f"{name}: раскраска рифм (RPST)",
                       os.path.join(case, "coloring_rpst.png"))
            except Exception as e:   # noqa: BLE001
                parts += ["", "=== RPST ===", "ошибка: " + repr(e)]
                rpst_ok = False      # дальше не пытаемся
        write(os.path.join(case, "metrics.txt"), "\n".join(parts))
        print("eval ok:", name)


def run_gen():
    from Model.Model import Model
    case = os.path.join(TEST_DIR, "gen_zima")
    os.makedirs(case, exist_ok=True)
    m = Model()
    p = GenParams(theme="зима", n_lines=4, meter="ямб", scheme="ABAB")
    scored = m.generate_best(p, n=6, use_llm=False, method="yukawa")
    head = ("Тема: зима | размер: ямб | схема: ABAB | N=6 | "
            "генератор: заглушка (корпус poems/) | детектор: Юкава\n"
            "(best-of-N: кандидаты по убыванию % зарифмованных слогов)\n")
    rows = []
    for rank, (text, met) in enumerate(scored, 1):
        first = text.splitlines()[0] if text.strip() else ""
        rows.append(f"#{rank}  рифма {met.get('rhyme_percent', 0):>4.0%}  |  {first}")
    write(os.path.join(case, "gen_output.txt"), head + "\n".join(rows))
    best_text, best_m = scored[0]
    write(os.path.join(case, "best.txt"), best_text)
    render(best_m["colored_lines"], "Лучший из 6 (best-of-N), детектор Юкава",
           os.path.join(case, "coloring.png"))
    print("gen ok: gen_zima")


if __name__ == "__main__":
    os.makedirs(TEST_DIR, exist_ok=True)
    run_eval()
    run_gen()
    print("Готово. Артефакты в", TEST_DIR)
