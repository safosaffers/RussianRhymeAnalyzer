# Подключение ИИ-генерации

Приложение умеет генерировать стихи через LLM. Поддерживаются три провайдера,
выбор — переменной окружения `RHYMER_PROVIDER`:

| `RHYMER_PROVIDER` | класс | ключ (env) | SDK | оплата |
|---|---|---|---|---|
| `anthropic` (по умолч.) | `LLMGenerator` | `ANTHROPIC_API_KEY` | `anthropic` | кредиты Console |
| `gemini` | `OpenAICompatGenerator` | `GEMINI_API_KEY` | `openai` | **есть free tier** |
| `deepseek` | `OpenAICompatGenerator` | `DEEPSEEK_API_KEY` | `openai` | очень дёшево |

Генератор включается, только когда для выбранного провайдера есть ключ и стоит
его SDK (`Model._make_llm()` → `Model.llm_available` → активирует чекбокс
«Генерировать через ИИ» в UI). Иначе работает `StubGenerator` из корпуса `poems/`.

Ключ — секрет: **не коммитить**. В коде его нет, только через env.

---

## Вариант A — Gemini (бесплатный тариф) ⭐

### Где взять ключ
1. https://aistudio.google.com → войти Google-аккаунтом.
2. **Get API key → Create API key**. Биллинг **не нужен**, free tier сразу
   (есть лимиты запросов в минуту/в день).

### Проверка
```bash
# 1. SDK (OpenAI-совместимый endpoint Gemini)
../venv/bin/python -m pip install openai

# 2. провайдер + ключ — в ТУ ЖЕ сессию
export RHYMER_PROVIDER=gemini
export GEMINI_API_KEY=...

# 3. видит ли приложение ключ (без GUI)
cd src && ../venv/bin/python -c "from Model.Model import Model; m=Model(); print('available:', m.llm_available, '|', m.llm_name)"
# available: True | ИИ (Gemini)

# 4. живой тест генерации одного кандидата
../venv/bin/python -c "
from Model.OpenAICompatGenerator import OpenAICompatGenerator
from Model.Generator import GenParams
g = OpenAICompatGenerator('gemini')
print(g.generate(GenParams(theme='зима', n_lines=4, scheme='ABAB'), n=1)[0])
"

# 5. полный UI
../venv/bin/python main.py
```

Модель по умолчанию — `gemini-2.5-flash`. Если AI Studio покажет другое имя —
`export RHYMER_MODEL=<имя-модели>`.

---

## Вариант B — DeepSeek (очень дёшево)

1. https://platform.deepseek.com → API keys → создать (`sk-...`), пополнить баланс.
2. ```bash
   ../venv/bin/python -m pip install openai
   export RHYMER_PROVIDER=deepseek
   export DEEPSEEK_API_KEY=sk-...
   ```
3. Проверка — как у Gemini (шаги 3–5), но `OpenAICompatGenerator('deepseek')`.
   Модель по умолчанию `deepseek-chat`; `deepseek-reasoner` — через `RHYMER_MODEL`.

---

## Вариант C — Anthropic (Claude)

### Где взять ключ
Отдельная оплата по кредитам, не связана с подпиской Claude Code:
1. https://console.anthropic.com → войти / зарегистрироваться.
2. **Settings → API Keys → Create Key** (`sk-ant-...`). Показывают один раз.
3. **Billing → Credits** — нужен положительный баланс.

### Проверка
```bash
../venv/bin/python -m pip install anthropic
# anthropic — провайдер по умолчанию, RHYMER_PROVIDER можно не задавать
export ANTHROPIC_API_KEY=sk-ant-...
cd src && ../venv/bin/python -c "from Model.LLMGenerator import LLMGenerator; print('available:', LLMGenerator.available())"
../venv/bin/python main.py
```
Модель по умолчанию `claude-opus-4-8`; дешевле — `export RHYMER_MODEL=claude-haiku-4-5-20251001`.

---

## Замечания

- `RHYMER_PROVIDER`, ключ и (если нужно) `RHYMER_MODEL` задавай **в той же
  сессии терминала**, откуда запускаешь приложение. Если `llm_available=False` —
  проверь, что `export` сделан здесь же и установлен нужный SDK.
- `RHYMER_MODEL` переопределяет модель **активного** провайдера. При смене
  провайдера не забудь сменить/сбросить `RHYMER_MODEL` (иначе, например, имя
  модели Claude уедет в Gemini и вызов упадёт).
- Различие форматов: Anthropic просит строгую JSON-схему (`json_schema`),
  Gemini/DeepSeek — `json_object` + описание структуры словами в промпте
  (см. `OpenAICompatGenerator`). На качество рифмы это не влияет, только на
  способ получения JSON.
- Чтобы не вводить каждый раз — `export ...` в `~/.bashrc` или в `.env` под
  `.gitignore`.
