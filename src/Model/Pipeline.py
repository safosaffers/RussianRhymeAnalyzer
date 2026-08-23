# Model/Pipeline.py
# Глубокий режим: замысел -> черновики -> отбор -> оценка -> адресная правка.
# Склейка ролей модели и детекторов; сам по себе вызовов API не делает.
# Вызовов на один стих: 1 (карта) + 1 (N черновиков) + 1 (оценка)
# + до max_fix * 2 (правка и переоценка).
from dataclasses import replace

from Model.AiTraces import ai_traces, traces_text
from Model.RhymeFeedback import rhyme_feedback, needs_rhyme_fix

THRESHOLD = 21          # из 30 баллов рубрики; калибруется на своих текстах
MAX_FIX = 1             # проходов правки


def claims_text(m: dict, report: dict, traces: list, scheme: str) -> str:
    """Свести три источника претензий в одну адресную подсказку."""
    parts = []
    if needs_rhyme_fix(m):
        parts.append(rhyme_feedback(m, scheme))
    for it in (report or {}).get("issues", []):
        where = f"строка {it['line']}" if it.get("line") else "весь стих"
        parts.append(f"{where}: {it.get('symptom', '')} -> {it.get('fix', '')}")
    if traces:
        parts.append(traces_text(traces))
    return "\n".join(p for p in parts if p)


def _ok(report: dict, traces: list, m: dict, threshold: int) -> bool:
    return (report.get("total", 0) >= threshold
            and not traces
            and not needs_rhyme_fix(m))


def compose(llm, score, params, n: int = 6, max_fix: int = MAX_FIX,
            threshold: int = THRESHOLD, on_step=None) -> dict:
    """Собрать стих по полному конвейеру.

    llm    — генератор с ролями plan/generate/judge/rework;
    score  — функция text -> метрики детектора рифмы;
    on_step— необязательный колбэк для показа стадии в интерфейсе.
    """
    step = on_step or (lambda _: None)

    step("замысел")
    spec = llm.plan(params)

    step("черновики")
    cands = llm.generate(replace(params, spec=spec), n)
    if not cands:
        return None
    scored = sorted(((c, score(c)) for c in cands),
                    key=lambda x: x[1]["rhyme_score"], reverse=True)
    text, m = scored[0]

    step("оценка")
    report = llm.judge(text, spec)
    traces = ai_traces(text)
    history = [{"stage": "черновик", "total": report.get("total"),
                "rhyme": m.get("rhyme_score"), "traces": len(traces)}]

    for _ in range(max_fix):
        if _ok(report, traces, m, threshold):
            break
        claims = claims_text(m, report, traces, params.scheme)
        if not claims:
            break
        step("правка")
        fixed = llm.rework(text, claims, params, spec)
        if not fixed or fixed.strip() == text.strip():
            break
        fm = score(fixed)
        step("переоценка")
        freport = llm.judge(fixed, spec)
        ftraces = ai_traces(fixed)
        history.append({"stage": "правка", "total": freport.get("total"),
                        "rhyme": fm.get("rhyme_score"), "traces": len(ftraces)})
        # правка принимается, только если стало не хуже по смыслу
        if freport.get("total", 0) >= report.get("total", 0):
            text, m, report, traces = fixed, fm, freport, ftraces

    m = dict(m)
    m["deep"] = True
    return {"text": text, "metrics": m, "spec": spec, "report": report,
            "traces": traces, "history": history, "candidates": scored}
