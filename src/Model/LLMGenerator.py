# Model/LLMGenerator.py
import json
import os

from Model.Generator import Generator, GenParams
from Model.Poetics import poetics_text
from Model.PoemSpec import PoemSpec, SCHEMA as SPEC_SCHEMA
from Model import Roles, Techniques

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
    TIMEOUT_S = 120.0       # база; на длинный ответ ждём дольше, см. _ask
    MAX_RETRIES = 2
    TOKENS_PER_S = 40.0     # осторожная оценка скорости письма модели
    TIMEOUT_MAX_S = 600.0

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
        # 20 строк на 16 кандидатов — это десятки тысяч токенов ответа, которые
        # физически не успеют записаться за базовый таймаут. Ждём соразмерно
        # запрошенному объёму, но не бесконечно.
        timeout = min(self.TIMEOUT_MAX_S,
                      self.TIMEOUT_S + max_tokens / self.TOKENS_PER_S)
        resp = self._client.with_options(timeout=timeout).messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system or self._system(),
            messages=[{"role": "user", "content": user}],
            output_config={"format": {"type": "json_schema", "schema": schema}},
        )
        text = next((b.text for b in resp.content if b.type == "text"), "{}")
        return json.loads(text)

    def judge(self, text: str, spec: PoemSpec = None) -> dict:
        """Смысловая оценка по рубрике: баллы, адресные претензии, вердикт.

        Отдельный вызов, а не продолжение диалога с генератором: модель,
        которая оценивает собственный черновик в том же контексте, завышает
        балл. Оценивается один текст — формальный отбор по рифме уже сделан."""
        user = Roles.judge_prompt(text, spec.to_prompt() if spec else "")
        return Roles.normalize_report(
            self._ask(user, Roles.JUDGE_SCHEMA, max_tokens=1500))

    def plan(self, params: GenParams) -> PoemSpec:
        """Карта стиха до генерации: замысел, говорящий, сцена.

        Роль задаётся в сообщении пользователя, а не в system: системный
        префикс общий для всех ролей и потому кешируется целиком."""
        user = Roles.plan_prompt(params.theme.strip() or "свободная тема")
        return PoemSpec.from_dict(self._ask(user, SPEC_SCHEMA, max_tokens=1200))

    def generate(self, params: GenParams, n: int) -> list[str]:
        theme = params.theme.strip() or "свободная тема"
        # акростих и родня задают длину жёстко — иначе требование невыполнимо
        n_lines = Techniques.required_lines(params.techniques) or params.n_lines
        user = (
            f"Сочини {n} РАЗНЫХ вариантов стихотворения.\n"
            f"Тема: {theme}\n"
            f"Размер: {params.meter}\n"
            f"Число строк в каждом: {n_lines}\n"
            f"Схема рифмовки: {params.scheme}\n"
            f"Каждый вариант — ровно {n_lines} строк, строки разделяй '\\n'. "
            f"Добивайся точной рифмы по схеме {params.scheme}."
        )
        demands = Techniques.demands_text(params.techniques)
        if demands:                                     # техника важнее темы
            user = ("ТРЕБОВАНИЯ К ТЕХНИКЕ (нарушать нельзя, они проверяются "
                    f"автоматически):\n{demands}\n\n" + user)
        if params.spec is not None:                     # глубокий режим: пишем по карте
            user = (
                "Ты пишешь не по теме, а по готовому замыслу. Следуй ему.\n\n"
                f"ЗАМЫСЕЛ:\n{params.spec.to_prompt()}\n\n" + user
            )
        schema = {
            "type": "object",
            "properties": {"poems": {"type": "array", "items": {"type": "string"}}},
            "required": ["poems"],
            "additionalProperties": False,
        }
        data = self._ask(user, schema, max_tokens=400 + 120 * params.n_lines * n)
        return [p.strip() for p in data.get("poems", []) if p.strip()]

    def rework(self, text: str, claims: str, params: GenParams,
               spec: PoemSpec = None) -> str:
        """Правка по адресным претензиям: рифма, смысл и машинный след разом.

        Отдельно от improve(): тот чинит только рифму и вызывается из ручного
        улучшения — менять его промпт значило бы менять и ту кнопку."""
        user = Roles.rework_prompt(text, claims, params.meter, params.scheme,
                                   params.n_lines,
                                   spec.to_prompt() if spec else "",
                                   Techniques.demands_text(params.techniques))
        user += " Верни JSON с одним полем poem (строки через '\\n')."
        data = self._ask(user, Roles.POEM_SCHEMA,
                         max_tokens=400 + 120 * params.n_lines)
        return (data.get("poem") or "").strip()

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
