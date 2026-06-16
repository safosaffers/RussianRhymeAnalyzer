#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Диаграмма Ганта плана работы над ВКР -> img/gantt_vkr.png.
# Данные взяты из docs/practice/02_plan_gantt.md (mermaid-гант). Кириллица —
# через шрифт DejaVu Sans (по умолчанию в matplotlib). Запуск:
#   venv/bin/python -c "import runpy; runpy.run_path('docs/practice/build_gantt.py', run_name='__main__')"
import os
from datetime import datetime, timedelta

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import Patch
from matplotlib.lines import Line2D

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
OUT = os.path.join(ROOT, "img", "gantt_vkr.png")

RU_MON = ["", "янв", "фев", "мар", "апр", "май", "июн",
          "июл", "авг", "сен", "окт", "ноя", "дек"]

# (название секции, цвет, [(этап, старт, длит_дней, crit, milestone)])
SECTIONS = [
    ("1-й курс — обзор и постановка", "#4E79A7", [
        ("Выбор направления",              "2025-09-01", 30, False, False),
        ("Формулировка темы",              "2025-10-01", 30, False, False),
        ("Отеч. литература (30–50 ист.)",  "2025-10-01", 90, False, False),
        ("Цель/задачи, объект/предмет",    "2025-11-01", 30, False, False),
        ("Гипотеза, ТЗ",                   "2025-12-01", 31, False, False),
    ]),
    ("1-й курс — прототип и практика", "#59A14F", [
        ("Прототип Rhymer (MVP)",                 "2026-01-01", 31, False, False),
        ("Заруб. литература, SOTA (70–100)",      "2026-02-01", 34, True,  False),
        ("План-график и диаграмма Ганта",         "2026-03-07", 48, True,  False),
        ("Данные: поиск/датасеты/протокол",       "2026-04-15", 39, True,  False),
        ("Спецификация системы",                  "2026-05-15", 14, True,  False),
        ("Отчёт + предзащита/защита практики",    "2026-06-01", 30, False, False),
    ]),
    ("2-й курс — модель и эксперименты", "#B07AA1", [
        ("Архитектура, baseline",                  "2026-09-01", 30, False, False),
        ("Разработка основной модели",             "2026-09-15", 75, False, False),
        ("Тезисы/статья на конференцию",           "2026-10-01", 31, False, False),
        ("Эксперименты, логи",                     "2026-11-01", 90, False, False),
        ("Формализация, целевая функция, метрики", "2027-01-10", 25, False, False),
    ]),
    ("2-й курс — оформление и защита", "#9C755F", [
        ("Доработка модели, главы ВКР",            "2027-02-01", 59, False, False),
        ("ГОСТ, иллюстрации, антиплагиат",         "2027-04-01", 20, False, False),
        ("Презентация, предзащита, рецензия",      "2027-04-10", 20, False, False),
        ("Защита ВКР перед ГЭК",                   "2027-06-01",  1, False, True),
    ]),
]

CRIT = "#E15759"      # задания практики с дедлайнами
GOLD = "#F1A92E"      # веха-защита
TODAY = datetime(2026, 6, 16)


def d(s):
    return datetime.strptime(s, "%Y-%m-%d")


def build():
    # разворачиваем строки: секции-заголовки + этапы (сверху вниз)
    rows = []
    for name, color, tasks in SECTIONS:
        rows.append(("sec", name, color))
        for t in tasks:
            rows.append(("task", color, t))

    n = len(rows)
    fig, ax = plt.subplots(figsize=(13.5, 9.0))
    yticks, ylabels = [], []

    for i, row in enumerate(rows):
        y = n - i                       # сверху вниз
        if row[0] == "sec":
            ax.text(d("2025-08-20"), y, row[1], fontweight="bold",
                    fontsize=11, va="center", ha="left", color=row[2])
            ax.axhline(y - 0.5, color="#DDDDDD", lw=0.8)
            continue
        _, color, (label, start, dur, crit, mile) = row
        s = d(start)
        yticks.append(y); ylabels.append(label)
        if mile:                        # веха — ромб (подпись уже слева, на оси Y)
            ax.plot(s, y, marker="D", markersize=13, color=GOLD,
                    markeredgecolor="#7A5200", zorder=5)
            continue
        bar_c = CRIT if crit else color
        ax.barh(y, dur, left=s, height=0.62, color=bar_c,
                edgecolor="#3A3A3A" if crit else "white",
                linewidth=1.4 if crit else 0.6, zorder=3, alpha=0.95)

    # ---- ось X: месяцы (кириллица вручную) ----
    x0, x1 = d("2025-08-25"), d("2027-07-05")
    ax.set_xlim(x0, x1)
    ax.set_ylim(0.3, n + 0.7)
    months = []
    cur = datetime(2025, 9, 1)
    while cur <= datetime(2027, 7, 1):
        months.append(cur)
        cur = datetime(cur.year + (cur.month // 12), (cur.month % 12) + 1, 1)
    ax.set_xticks(months)
    ax.set_xticklabels(
        [f"{RU_MON[m.month]} {m.year % 100:02d}" if m.month % 2 == 1 else ""
         for m in months], fontsize=8)
    for m in months:                    # вертикальная сетка по месяцам
        ax.axvline(m, color="#EEEEEE", lw=0.6, zorder=0)
    # разделители учебных лет
    for yr in (datetime(2026, 9, 1),):
        ax.axvline(yr, color="#BBBBBB", lw=1.2, ls="--", zorder=1)

    ax.axvline(TODAY, color="#2563EB", lw=1.4, ls=":", zorder=4)
    ax.text(TODAY, n + 0.55, " сегодня", color="#2563EB",
            fontsize=8.5, fontweight="bold", va="bottom", ha="left")

    ax.set_yticks(yticks)
    ax.set_yticklabels(ylabels, fontsize=9)
    ax.tick_params(axis="y", length=0)
    for sp in ("top", "right", "left"):
        ax.spines[sp].set_visible(False)
    ax.set_axisbelow(True)

    ax.set_title("Диаграмма Ганта — план работы над ВКР\n"
                 "«ИИ-генерация и автоматическая оценка рифмованной русской поэзии»",
                 fontsize=13, fontweight="bold", pad=14)

    legend = [
        Patch(facecolor=CRIT, edgecolor="#3A3A3A",
              label="Задание учебной практики (дедлайн)"),
        Line2D([0], [0], marker="D", color="w", markerfacecolor=GOLD,
               markeredgecolor="#7A5200", markersize=11, label="Защита ВКР (веха)"),
        Line2D([0], [0], color="#2563EB", ls=":", lw=1.4, label="Текущий момент"),
    ]
    ax.legend(handles=legend, loc="upper right", fontsize=8.5,
              framealpha=0.95, borderpad=0.8)

    fig.tight_layout()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    fig.savefig(OUT, dpi=200, bbox_inches="tight", facecolor="white")
    print("Сохранено:", OUT, "|", fig.get_size_inches())


if __name__ == "__main__":
    build()
