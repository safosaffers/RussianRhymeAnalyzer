# Model/LLMGenerator.py
import json
import os

from Model.Generator import Generator, GenParams
from Model.Poetics import poetics_text
from Model.PoemSpec import PoemSpec, SCHEMA as SPEC_SCHEMA

# по умолчанию — самая способная модель; можно переопределить через окружение
DEFAULT_MODEL = os.environ.get("RHYMER_MODEL", "claude-opus-4-8")

SYSTEM = (
    "Ты — русский поэт. Сочиняешь силлабо-тонические рифмованные стихи. "
    "Строго соблюдаешь заданные тему, стихотворный размер, число строк и схему рифмовки. "
    "Отвечаешь только в запрошенном формате JSON, без пояснений."
)


class LLMGenerator(Generator):
    """Генератор на Claude API (готовая модель).

    best-of-N: за один вызов модель выдаёт N разных вариантов на тему.
    Разнообразие — за счёт инструкции (Opus 4.8 не принимает temperature).
    Метод improve() — самокоррекция по обратной связи нашего RhymeEvaluator.
    """

    label = "ИИ (Claude)"   # имя для статуса в UI

    def __init__(self, model: str = None):
        self.model = model or DEFAULT_MODEL
        self._client = None

    @staticmethod
    def available() -> bool:
        if not os.environ.get("ANTHROPIC_API_KEY"):
            return False
        try:
            import anthropic  # noqa: F401
            return True
        except ImportError:
            return False

    # Цепочка вызовов на один стих длинная, поэтому ограничиваем ожидание:
    # у SDK по умолчанию 10 минут на запрос и 2 повтора, то есть до получаса
    # молчания на одном шаге.
    TIMEOUT_S = 120.0
    MAX_RETRIES = 2

    def _ensure(self):
        if self._client is None:
            import anthropic
            self._client = anthropic.Anthropic(   # ключ из ANTHROPIC_API_KEY
                timeout=self.TIMEOUT_S, max_retries=self.MAX_RETRIES)

    @staticmethod
    def _system() -> list:
        """Системный промпт блоками: роль + свод правил о смысле.

        Префикс стабилен от вызова к вызову, поэтому помечаем его
        cache_control — за серию вызовов (генерация, правка) он оплачивается
        один раз. Всё переменное уходит в сообщение пользователя, после
        точки останова кеша."""
        blocks = [{"type": "text", "text": SYSTEM}]
        rules = poetics_text()
        if rules:
            blocks.append({"type": "text", "text": rules,
                           "cache_control": {"type": "ephemeral"}})
        return blocks

    def _ask(self, user: str, schema: dict, max_tokens: int = 4000,
             system: list = None) -> dict:
        self._ensure()
        resp = self._client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system or self._system(),
            messages=[{"role": "user", "content": user}],
            output_config={"format": {"type": "json_schema", "schema": schema}},
        )
        text = next((b.text for b in resp.content if b.type == "text"), "{}")
        return json.loads(text)

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

    def judge(self, text: str, spec: PoemSpec = None) -> dict:
        """Смысловая оценка по рубрике: баллы, адресные претензии, вердикт.

        Отдельный вызов, а не продолжение диалога с генератором: модель,
        которая оценивает собственный черновик в том же контексте, завышает
        балл. Оценивается один текст — формальный отбор по рифме уже сделан."""
        rubric = "\n".join(f"- {k}: {v}" for k, v in self.RUBRIC.items())
        user = (
            "Сейчас ты не пишешь стих, а оцениваешь чужой. Будь строгим: "
            "средний балл по критерию — 1, три ставится только за то, что "
            "действительно работает.\n\n"
            f"СТИХ:\n{text}\n\n"
            + (f"ЗАМЫСЕЛ, по которому он писался:\n{spec.to_prompt()}\n\n" if spec else "")
            + f"Оцени по каждому критерию от 0 до 3:\n{rubric}\n\n"
            "total — сумма баллов. issues — конкретные претензии: line (номер "
            "строки, 0 если про весь стих), symptom (что не так, словами из "
            "свода правил), fix (что именно сделать). Не больше пяти претензий, "
            "самые важные. verdict — одно предложение о стихе в целом."
        )
        return self._ask(user, self.JUDGE_SCHEMA, max_tokens=1500)

    def plan(self, params: GenParams) -> PoemSpec:
        """Карта стиха до генерации: замысел, говорящий, сцена.

        Роль задаётся в сообщении пользователя, а не в system: системный
        префикс общий для всех ролей и потому кешируется целиком."""
        theme = params.theme.strip() or "свободная тема"
        user = (
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
            "- scene: где и когда он это произносит, что у него перед глазами;\n"
            "- punchline: чем кончается, без морали и без объясняющей строки;\n"
            "- forbidden: 3-5 слов, которых этот говорящий не скажет."
        )
        return PoemSpec.from_dict(self._ask(user, SPEC_SCHEMA, max_tokens=1200))

    def generate(self, params: GenParams, n: int) -> list[str]:
        theme = params.theme.strip() or "свободная тема"
        user = (
            f"Сочини {n} РАЗНЫХ вариантов стихотворения.\n"
            f"Тема: {theme}\n"
            f"Размер: {params.meter}\n"
            f"Число строк в каждом: {params.n_lines}\n"
            f"Схема рифмовки: {params.scheme}\n"
            f"Каждый вариант — ровно {params.n_lines} строк, строки разделяй '\\n'. "
            f"Добивайся точной рифмы по схеме {params.scheme}."
        )
        schema = {
            "type": "object",
            "properties": {"poems": {"type": "array", "items": {"type": "string"}}},
            "required": ["poems"],
            "additionalProperties": False,
        }
        data = self._ask(user, schema, max_tokens=400 + 120 * params.n_lines * n)
        return [p.strip() for p in data.get("poems", []) if p.strip()]

    def improve(self, text: str, feedback: str, params: GenParams) -> str:
        """Самокоррекция: переписать стих, улучшив рифму по фидбэку оценщика."""
        theme = params.theme.strip() or "свободная тема"
        user = (
            "Вот стихотворение и разбор его рифмы:\n\n"
            f"СТИХ:\n{text}\n\n"
            f"РАЗБОР: {feedback}\n\n"
            "Перепиши стихотворение, улучшив рифму: СОХРАНИ хорошо рифмующиеся "
            "окончания, перепиши только плохие строки — в первую очередь ЗАМЕНИ "
            "последние слова не рифмующихся строк на созвучные. Обязательно обеспечь: "
            "естественную читаемость (живой порядок слов, без неуклюжих инверсий "
            "ради рифмы), связный смысл, точную рифму по схеме "
            f"{params.scheme}, выдержанный размер {params.meter} и ровно "
            f"{params.n_lines} строк. Сохрани тему «{theme}». "
            "Верни JSON с одним полем poem (строки через '\\n')."
        )
        schema = {
            "type": "object",
            "properties": {"poem": {"type": "string"}},
            "required": ["poem"],
            "additionalProperties": False,
        }
        data = self._ask(user, schema, max_tokens=400 + 120 * params.n_lines)
        return (data.get("poem") or "").strip()
