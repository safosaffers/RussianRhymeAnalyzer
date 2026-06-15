# Model/OpenAICompatGenerator.py
# Генератор для провайдеров с OpenAI-совместимым API (Gemini, DeepSeek).
# Один класс на оба: отличаются base_url, моделью и именем env-переменной с ключом.
import json
import os

from Model.Generator import Generator, GenParams
from Model.LLMGenerator import SYSTEM   # та же системная инструкция, что и для Claude

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

    def _ask(self, user: str, max_tokens: int = 4000) -> dict:
        self._ensure()
        resp = self._client.chat.completions.create(
            model=self.model,
            max_tokens=max_tokens,
            messages=[{"role": "system", "content": SYSTEM},
                      {"role": "user", "content": user}],
            response_format={"type": "json_object"},
        )
        text = (resp.choices[0].message.content or "{}").strip()
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
            f"Добивайся точной рифмы по схеме {params.scheme}.\n"
            'Верни JSON строго вида: {"poems": ["стих1", "стих2", ...]} — '
            "массив из строк-стихов, без каких-либо пояснений."
        )
        data = self._ask(user, max_tokens=400 + 120 * params.n_lines * n)
        poems = data.get("poems", [])
        return [p.strip() for p in poems if isinstance(p, str) and p.strip()]

    def improve(self, text: str, feedback: str, params: GenParams) -> str:
        """Самокоррекция: переписать стих, улучшив рифму по фидбэку оценщика."""
        theme = params.theme.strip() or "свободная тема"
        user = (
            "Вот стихотворение и оценка его рифмы от анализатора:\n\n"
            f"СТИХ:\n{text}\n\n"
            f"ОЦЕНКА: {feedback}\n\n"
            f"Перепиши стихотворение так, чтобы рифма стала лучше (схема {params.scheme}), "
            f"сохрани тему «{theme}», размер {params.meter} и число строк {params.n_lines}.\n"
            'Верни JSON строго вида: {"poem": "строки через \\n"}, без пояснений.'
        )
        data = self._ask(user, max_tokens=400 + 120 * params.n_lines)
        return (data.get("poem") or "").strip()
