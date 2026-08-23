# Архитектура приложения «Rhymer»

Десктоп-приложение: генерирует русский силлабо-тонический стих, численно
оценивает его рифму и через **best-of-N** выбирает лучший вариант. UI на
**PySide6**, паттерн **MVP** (как в дипломе HallsSequences).

## Структура

```
src/
  main.py                     точка входа: Model() + View() + Presenter(m, v)
  Model/                      бизнес-логика (без Qt)
    Model.py                  фасад: evaluate(...), generate_best(...)
    Generator.py              Generator(ABC) + StubGenerator (корпус poems/)
    LLMGenerator.py           Claude API: роли generate/plan/judge/rework
    PoemSpec.py               карта смысла: 7 шагов замысла + повод, лицо, сцена
    Poetics.py                загрузка свода правил (resources/poetics.md)
    AiTraces.py               детерминированный детектор машинного следа
    Pipeline.py               глубокий режим: замысел -> черновики -> оценка -> правка
    RhymeEvaluator.py         детектор "rpst": обёртка RPST + матчер хвостов
    YukawaDetector.py         детектор "yukawa": авторский алгоритм
    Phonetics.py              векторизация слогов: схожесть = косинус признаков
    TextConverter.py          утилита препроцессинга текста (вне основного потока)
  View/
    View.py                   QWidget: вкладки «Генерация» / «Оценка рифм»,
                              подсветка рифм, тема свет/тьма, тюнинг Юкавы
  Presenter/
    Presenter.py              связь View↔Model; тяжёлые задачи в QThread (Worker)
  Research/
    detector.py               прототип детектора Юкавы (matplotlib-визуализация)
```

Свод правил о смысле стиха, который подмешивается в системный промпт, —
в `resources/poetics.md` (полный справочник — `docs/sense-and-structure.html`,
схема конвейера — `docs/poem-pipeline.drawio`).

Документация и план — в `docs/`. Корпус классики — в `poems/`. Скриншоты UI —
в `Rhymer/`.

## Паттерн MVP

- **View** не знает про Model. Наружу выставляет только сигналы
  (`btn_generate.clicked`, `btn_evaluate.clicked`, `candidate_selected`,
  `tune_changed`) и геттеры/сеттеры (`theme_text()`, `scheme()`,
  `set_gen_result()`, `set_busy()` …).
- **Model** не знает про Qt — чистая логика, тестируема отдельно.
- **Presenter** — единственный мост. Это `QObject`, живёт в главном потоке;
  его слоты, подключённые к сигналам `Worker`, исполняются в главном потоке
  (где можно трогать виджеты).

## Поток данных

```
тема/параметры ─▶ Генератор ─▶ N кандидатов
                                  │
                       Детектор рифмы (rpst | yukawa)
                                  │
                 best-of-N (сортировка по rhyme_score)
                  + для LLM: 1 проход самокоррекции по фидбэку
                                  │
                       View: лучший стих + метрики + подсветка
```

Два сценария (`Presenter._mode`):
- **`gen`** — `Model.generate_best(params, n, use_llm, method)`:
  генерим N кандидатов выбранным генератором → каждого оцениваем детектором →
  сортируем по убыванию `rhyme_score`. Для LLM, если у лучшего
  детектор нашёл незарифмованные строки (`needs_rhyme_fix`), добавляется один
  вызов `improve()` с построчным разбором рифмы, результат тоже скорится и
  пересортировывается.
- **`deep`** — `Model.compose_deep(params, n, method, yk_params, on_step)`:
  `Pipeline.compose()` строит карту смысла (`plan`), генерит по ней N
  черновиков, отбирает лучший по рифме, оценивает по рубрике из 10 критериев
  (`judge`) и детектором машинного следа (`ai_traces`), затем одним вызовом
  `rework()` чинит названные претензии. Правка принимается, только если
  смысловой балл не упал. Роли есть лишь у `LLMGenerator`, поэтому режим
  закрыт флагом `Model.deep_available`.
- **`eval`** — `Model.evaluate(text, scheme, method, yk_params)`: оценка
  пользовательского стиха.

## Асинхронность

Загрузка моделей RPST (~15–30 с на первом вызове), генерация и оценка идут в
`QThread` через `Presenter.Worker` (сигналы `done`/`failed`/`progress`;
`progress` показывает стадию длинной цепочки глубокого режима). UI не виснет;
во время работы — `set_busy(True)`. Исключение — живой тюнинг Юкавы
(`on_tune`): он быстрый и считается прямо в главном потоке.

## Ключевые контракты

**Единый интерфейс детектора** — `evaluate(text, scheme[, params]) -> dict`.
`Model._detector(method)` выбирает реализацию по строке `"rpst"` / `"yukawa"`;
`Model._score(...)` прокидывает Юкаве настраиваемые `yk_params`. Оба детектора
возвращают dict с общими ключами:

| ключ | смысл |
|---|---|
| `rhyme_score` | балл для ранжирования best-of-N |
| `rhyme_percent` | доля зарифмованных слогов |
| `rhyme_accuracy` | RPST: точность по заданной схеме; Юкава: доля зарифмованных слогов (схему она не проверяет) |
| `colored_lines` | строки, разбитые на сегменты `(текст, цвет\|None)` |
| `legend` | цвет → список созвучных окончаний/слогов |
| `total_syllables`, `rhymed_syllables` | счётчики слогов |

(RPST дополнительно отдаёт `score`, `meter`, `rpst_scheme`, `stressed`,
`detected_scheme`; Юкава — `num_groups`, `params`, `method`.)

**Единый интерфейс генератора** — `generate(params: GenParams, n) -> list[str]`
(в глубоком режиме карта смысла едет в `GenParams.spec`; заглушка её игнорирует)
(каждый кандидат — строки через `\n`). Реализации `StubGenerator` и
`LLMGenerator` взаимозаменяемы без изменения UI. LLM включается, только если
есть `ANTHROPIC_API_KEY` и установлен пакет `anthropic`
(`LLMGenerator.available()` → `Model.llm_available` → чекбокс во View).

**Общая палитра** — `RHYME_COLORS` (в `RhymeEvaluator.py`) переиспользуется
детектором Юкавы, чтобы подсветка выглядела одинаково.

Подробно про оба детектора — в [RHYME_DETECTOR.md](RHYME_DETECTOR.md);
про фонетическую векторизацию слогов (ядро схожести в Юкаве) —
в [SYLLABLE_SIMILARITY.md](SYLLABLE_SIMILARITY.md).

## Запуск

```bash
export ANTHROPIC_API_KEY=...        # опционально, для ИИ-генерации
cd src && ../venv/bin/python main.py
```

Без ключа чекбокс «Генерировать через ИИ» неактивен — работает
`StubGenerator` из корпуса `poems/`.
