# Model/LLMGenerator.py
import json
import os

from Model.Generator import Generator, GenParams

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

    def _ensure(self):
        if self._client is None:
            import anthropic
            self._client = anthropic.Anthropic()   # ключ из ANTHROPIC_API_KEY

    def _ask(self, user: str, schema: dict, max_tokens: int = 4000) -> dict:
        self._ensure()
        resp = self._client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=SYSTEM,
            messages=[{"role": "user", "content": user}],
            output_config={"format": {"type": "json_schema", "schema": schema}},
        )
        text = next((b.text for b in resp.content if b.type == "text"), "{}")
        return json.loads(text)

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
            "окончания, перепиши только плохие строки. Обязательно обеспечь: "
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
