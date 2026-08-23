# Model/OpenAICompatGenerator.py
# Генератор для провайдеров с OpenAI-совместимым API (Gemini, DeepSeek).
# Один класс на оба: отличаются base_url, моделью и именем env-переменной с ключом.
import json
import os

from Model.Generator import Generator, GenParams
from Model.LLMGenerator import SYSTEM   # та же системная инструкция, что и для Claude
from Model.Poetics import poetics_text
from Model.PoemSpec import PoemSpec
from Model import Roles

# конфиги OpenAI-совместимых провайдеров
PROVIDERS = {
    "gemini": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "key_env": "GEMINI_API_KEY",
        "default_model": "gemini-2.5-flash",
        "label": "ИИ (Gemini)",
    },
    "deepseek": {
        "base_url": "https://api.deepseek.com",
        "key_env": "DEEPSEEK_API_KEY",
        "default_model": "deepseek-chat",
        "label": "ИИ (DeepSeek)",
    },
}


def _extract_json(content: str) -> str:
    """Достаём JSON из ответа: снимаем markdown-ограждение ```json … ``` и
    обрезаем по внешним фигурным скобкам, если модель добавила пояснений."""
    if not content:
        return ""
    t = content.strip()
    if t.startswith("```"):
        nl = t.find("\n")
        t = (t[nl + 1:] if nl != -1 else t[3:])
        if t.endswith("```"):
            t = t[:-3]
        t = t.strip()
    start, end = t.find("{"), t.rfind("}")
    if start != -1 and end != -1 and end > start:
        return t[start:end + 1]
    return t


class OpenAICompatGenerator(Generator):
    """Генератор через OpenAI-совместимый endpoint (SDK `openai`).

    best-of-N: за один вызов модель выдаёт N вариантов на тему. Формат —
    response_format=json_object (json_schema, как у Anthropic, тут не гарантирован),
    поэтому требуемую структуру JSON описываем словами в промпте.
    improve() — самокоррекция по обратной связи нашего RhymeEvaluator.
    """

    def __init__(self, provider: str, model: str = None):
        cfg = PROVIDERS[provider]
        self.provider = provider
        self.base_url = cfg["base_url"]
        self.key_env = cfg["key_env"]
        self.label = cfg["label"]
        # RHYMER_MODEL переопределяет модель активного провайдера
        self.model = model or os.environ.get("RHYMER_MODEL", cfg["default_model"])
        self._client = None

    @staticmethod
    def available(provider: str) -> bool:
        cfg = PROVIDERS.get(provider)
        if not cfg or not os.environ.get(cfg["key_env"]):
            return False
        try:
            import openai  # noqa: F401
            return True
        except ImportError:
            return False

    def _ensure(self):
        if self._client is None:
            from openai import OpenAI
            self._client = OpenAI(api_key=os.environ[self.key_env],
                                  base_url=self.base_url)

    @staticmethod
    def _system_text() -> str:
        """Роль плюс свод правил о смысле — тот же, что уходит Claude."""
        rules = poetics_text()
        return f"{SYSTEM}\n\n{rules}" if rules else SYSTEM

    def _ask(self, user: str, max_tokens: int = 4000) -> dict:
        self._ensure()
        kwargs = dict(
            model=self.model,
            max_tokens=max_tokens,
            messages=[{"role": "system", "content": self._system_text()},
                      {"role": "user", "content": user}],
            response_format={"type": "json_object"},
        )
        if self.provider == "gemini":
            # gemini-2.5-* — «думающие» модели: reasoning-токены берутся из того же
            # лимита max_tokens и обрезают JSON ("Unterminated string"). Отключаем
            # размышление (extra_body, чтобы не зависеть от версии SDK).
            kwargs["extra_body"] = {"reasoning_effort": "none"}
        resp = self._client.chat.completions.create(**kwargs)
        choice = resp.choices[0]
        text = _extract_json(choice.message.content)
        if not text:
            raise RuntimeError(
                f"{self.label}: пустой ответ модели "
                f"(finish_reason={choice.finish_reason}). Проверьте ключ и имя модели.")
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            if choice.finish_reason == "length":
                raise RuntimeError(
                    f"{self.label}: ответ обрезан по лимиту токенов. Уменьшите число "
                    f"строк/кандидатов или увеличьте лимит.") from e
            raise RuntimeError(
                f"{self.label}: не удалось разобрать JSON ответа ({e}).") from e

    def generate(self, params: GenParams, n: int) -> list[str]:
        theme = params.theme.strip() or "свободная тема"
        user = (
            f"Сочини {n} РАЗНЫХ вариантов стихотворения.\n"
            f"Тема: {theme}\n"
            f"Размер: {params.meter}\n"
            f"Число строк в каждом: {params.n_lines}\n"
            f"Схема рифмовки: {params.scheme}\n"
            f"Каждый вариант — ровно {params.n_lines} строк, строки разделяй '\\n'. "
            f"Добивайся точной рифмы по схеме {params.scheme}.\n"
            'Верни JSON строго вида: {"poems": ["стих1", "стих2", ...]} — '
            "массив из строк-стихов, без каких-либо пояснений."
        )
        if params.spec is not None:                     # глубокий режим: пишем по карте
            user = (
                "Ты пишешь не по теме, а по готовому замыслу. Следуй ему.\n\n"
                f"ЗАМЫСЕЛ:\n{params.spec.to_prompt()}\n\n" + user
            )
        data = self._ask(user, max_tokens=400 + 120 * params.n_lines * n)
        poems = data.get("poems", [])
        return [p.strip() for p in poems if isinstance(p, str) and p.strip()]

    # ---------- роли глубокого режима ----------
    # Схему JSON эти провайдеры не гарантируют, поэтому структуру описываем
    # словами (json_hint), а ответ нормализуем перед возвратом.
    def plan(self, params: GenParams) -> PoemSpec:
        user = (Roles.plan_prompt(params.theme.strip() or "свободная тема")
                + Roles.json_hint(Roles.SPEC_SHAPE))
        return PoemSpec.from_dict(self._ask(user, max_tokens=1500))

    def judge(self, text: str, spec: PoemSpec = None) -> dict:
        user = (Roles.judge_prompt(text, spec.to_prompt() if spec else "")
                + Roles.json_hint(Roles.JUDGE_SHAPE))
        return Roles.normalize_report(self._ask(user, max_tokens=2000))

    def rework(self, text: str, claims: str, params: GenParams,
               spec: PoemSpec = None) -> str:
        user = (Roles.rework_prompt(text, claims, params.meter, params.scheme,
                                    params.n_lines,
                                    spec.to_prompt() if spec else "")
                + Roles.json_hint(Roles.POEM_SHAPE))
        data = self._ask(user, max_tokens=400 + 120 * params.n_lines)
        return (data.get("poem") or "").strip()

    def improve(self, text: str, feedback: str, params: GenParams) -> str:
        """Самокоррекция: переписать стих, улучшив рифму по фидбэку оценщика."""
        theme = params.theme.strip() or "свободная тема"
        user = (
            "Вот стихотворение и разбор его рифмы:\n\n"
            f"СТИХ:\n{text}\n\n"
            f"РАЗБОР: {feedback}\n\n"
            "Исравь стихотворение строго с тем набором параметров который я тебе ранее передал! Схема рифмовки - должна строго учитывастья."
            "Улучши рифму: СОХРАНИ хорошо уже рифмующиеся моменты, перепиши только плохие строки."
            "Обязательно обеспечь: "
            "естественную читаемость (живой порядок слов, без неуклюжих инверсий "
            "ради рифмы), связный смысл, точную рифму по схеме "
            f"{params.scheme}, выдержанный размер {params.meter} и ровно "
            f"{params.n_lines} строк. Сохрани тему «{theme}».\n"
         'Верни JSON строго вида: {"poem": "строки через \\n"}, без пояснений.'
            "Перед отправкой всё ещё раз хорошо перепроверь, мне очень важно чтобы ты не испортил имеющиеся рифмы но в тоже время улучшил худшие места."
        )
        data = self._ask(user, max_tokens=400 + 120 * params.n_lines)
        return (data.get("poem") or "").strip()
