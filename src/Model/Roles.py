# Model/Roles.py
# Тексты ролей конвейера: замысел, оценка, правка.
# Общие для всех провайдеров: Claude получает их вместе со схемой structured
# output, OpenAI-совместимые — с описанием той же структуры словами (json_schema
# там не гарантирован). Иначе роли пришлось бы дублировать в двух генераторах
# и они бы разъехались.

# Рубрика §11: десять критериев по 0-3 балла, максимум 30.
RUBRIC = {
    "occasion": "есть ли повод: почему это сказано именно сейчас",
    "stakes": "что поставлено на карту, что теряется",
    "concretion": "конкретные предметы против отвлечённых слов",
    "figuration": "работают ли образы и сравнения, нет ли стёртых",
    "tension": "есть ли сила, тянущая в другую сторону",
    "turn": "есть ли поворот, узнаёт ли стих что-то к концу",
    "voice": "цельность голоса, соответствие говорящему",
    "form": "оправданы ли строки и строфы, работает ли разбивка",
    "closure": "финал завершает, не объясняя",
    "surprise": "есть ли непредсказуемость, не собран ли стих из готового",
}

JUDGE_SCHEMA = {
    "type": "object",
    "properties": {
        "scores": {
            "type": "object",
            "properties": {k: {"type": "integer"} for k in RUBRIC},
            "required": list(RUBRIC),
            "additionalProperties": False,
        },
        "total": {"type": "integer"},
        "issues": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "line": {"type": "integer"},
                    "symptom": {"type": "string"},
                    "fix": {"type": "string"},
                },
                "required": ["line", "symptom", "fix"],
                "additionalProperties": False,
            },
        },
        "verdict": {"type": "string"},
    },
    "required": ["scores", "total", "issues", "verdict"],
    "additionalProperties": False,
}

POEM_SCHEMA = {
    "type": "object",
    "properties": {"poem": {"type": "string"}},
    "required": ["poem"],
    "additionalProperties": False,
}

# Те же структуры словами — для провайдеров без гарантии схемы.
SPEC_SHAPE = ('{"thought": "...", "occasion": "...", "palette": "...", '
              '"objects": ["...", "..."], "motion": "...", "speaker": "...", '
              '"addressee": "...", "scene": "...", "thread": "...", '
              '"punchline": "...", "forbidden": ["...", "..."]}')
JUDGE_SHAPE = ('{"scores": {' + ', '.join(f'"{k}": 0' for k in RUBRIC) + '}, '
               '"total": 0, "issues": [{"line": 0, "symptom": "...", "fix": "..."}], '
               '"verdict": "..."}')
POEM_SHAPE = '{"poem": "строка\\nстрока"}'


def json_hint(shape: str) -> str:
    return f"\n\nОтветь только JSON вида: {shape}"


def plan_prompt(theme: str) -> str:
    return (
        "Сейчас ты не пишешь стих, а готовишь замысел. Верни карту будущего "
        f"стихотворения на тему: {theme}.\n"
        "Требования к карте:\n"
        "- thought: одна мысль одним предложением, без красивостей;\n"
        "- occasion: что заставило говорить именно сейчас (событие, час, место);\n"
        "- objects: 4-6 конкретных предметов и деталей, которые можно потрогать "
        "или увидеть; никаких отвлечённых слов;\n"
        "- motion: режим движения (медитативный, аргументативный, ассоциативный, "
        "каталог, сопоставление) и в какой примерно строке перелом;\n"
        "- speaker: живой человек с возрастом, занятием и усталостью, а не «поэт»;\n"
        "- addressee: кому это говорится;\n"
        "- scene: где и когда он это произносит, что у него перед глазами;\n"
        "- thread: сквозной образ, который держит стих;\n"
        "- palette: тон и градус напряжения;\n"
        "- punchline: чем кончается, без морали и без объясняющей строки;\n"
        "- forbidden: 3-5 слов, которых этот говорящий не скажет."
    )


def judge_prompt(text: str, spec_text: str = "") -> str:
    rubric = "\n".join(f"- {k}: {v}" for k, v in RUBRIC.items())
    return (
        "Сейчас ты не пишешь стих, а оцениваешь чужой. Будь строгим: средний "
        "балл по критерию — 1, три ставится только за то, что действительно "
        "работает.\n\n"
        f"СТИХ:\n{text}\n\n"
        + (f"ЗАМЫСЕЛ, по которому он писался:\n{spec_text}\n\n" if spec_text else "")
        + f"Оцени по каждому критерию от 0 до 3:\n{rubric}\n\n"
        "total — сумма баллов. issues — конкретные претензии: line (номер строки, "
        "0 если про весь стих), symptom (что не так), fix (что именно сделать). "
        "Не больше пяти претензий, самые важные. verdict — одно предложение о "
        "стихе в целом."
    )


def rework_prompt(text: str, claims: str, meter: str, scheme: str,
                  n_lines: int, spec_text: str = "") -> str:
    return (
        "Перепиши стихотворение, починив ТОЛЬКО перечисленное. Остальное "
        "сохрани дословно: удачные строки не трогай.\n\n"
        f"СТИХ:\n{text}\n\n"
        f"ЧТО ПОЧИНИТЬ:\n{claims}\n\n"
        + (f"ЗАМЫСЕЛ:\n{spec_text}\n\n" if spec_text else "")
        + f"Сохрани размер {meter}, схему рифмовки {scheme} и ровно {n_lines} "
        "строк. Не добавляй вывод и мораль в финале."
    )


def normalize_report(d: dict) -> dict:
    """Привести ответ судьи к ожидаемому виду: у провайдеров без схемы часть
    полей может отсутствовать или приехать строкой."""
    d = dict(d or {})
    scores = {k: int(v) for k, v in (d.get("scores") or {}).items()
              if k in RUBRIC and str(v).lstrip("-").isdigit()}
    d["scores"] = scores
    try:
        d["total"] = int(d.get("total"))
    except (TypeError, ValueError):
        d["total"] = sum(scores.values())
    issues = []
    for it in d.get("issues") or []:
        if not isinstance(it, dict):
            continue
        try:
            line = int(it.get("line", 0))
        except (TypeError, ValueError):
            line = 0
        issues.append({"line": line, "symptom": str(it.get("symptom", "")),
                       "fix": str(it.get("fix", ""))})
    d["issues"] = issues
    d["verdict"] = str(d.get("verdict") or "")
    return d
