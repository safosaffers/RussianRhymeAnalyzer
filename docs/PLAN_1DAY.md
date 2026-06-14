# План на 1 день: минимальное ИИ-приложение «Rhymer» + презентация

## Идея (одно предложение)
LLM генерирует русский стих → готовый анализатор **RPST (`russian_scansion`)** численно оценивает рифму/размер →
приложение делает **best-of-N** (выбирает лучший вариант) и одну итерацию **самокоррекции** по обратной связи.
UI на **PySide6**. Авторский детектор Юкавы (`detector.py`) — как исследовательская визуализация (новизна).

```
тема/параметры → [Генератор: LLM] → N кандидатов
                                        │
                          [Верификатор: RPST score/meter/scheme]
                                        │
                 best-of-N + 1 проход самокоррекции по фидбэку
                                        │
                              [UI PySide6: лучший стих + метрики]
                              (+ вкладка: цветокарта Юкавы)
```

## Архитектура — MVP + PySide6 (как в дипломе HallsSequences)
Структура в `src/` (рядом с уже существующим `src/Model/TextConverter.py`):
```
src/
  main.py                     Model() + View() + Presenter(m, v)
  Model/  Model.py            фасад: generate_best(params, n), evaluate(text)
          Generator.py        Generator(ABC) + StubGenerator (LLMGenerator позже)
          RhymeEvaluator.py   обёртка RPST + метрика rhyme_accuracy
          TextConverter.py    (был) препроцессинг
  View/   View.py             QWidget: параметры, лучший стих, метрики, таблица; тема свет/тьма
  Presenter/ Presenter.py     сигналы View -> Model; тяжёлое в QThread (Worker)
```

## Статус реализации (день 1)
- [x] Окружение: PySide6 6.11, scipy, matplotlib — в venv (`venv/bin/python -m pip`, т.к. venv перенесён и `venv/bin/pip` сломан).
- [x] Модели RPST (LFS) докачаны через GitHub media-URL (git-lfs не нужен); `create_rpst_instance` зовём с явным `models_dir` (обход бага joinpath('') на Python 3.12).
- [x] Model-слой: StubGenerator (50 строф/359 строк из `poems/`), RhymeEvaluator, фасад Model.
- [x] View + Presenter + main (QThread, тема свет/тьма).
- [x] End-to-end прогон: эталон Пушкина → score=0.95, ямб/хорей, ABAB, рифма 100%.
      best-of-N (n=8): связная строфа Блока наверх (100%/0.93), шум — вниз (0%).
- [x] Скриншоты UI (свет/тьма): `Rhymer/ui_light.png`, `Rhymer/ui_dark.png`.
- [x] Подсветка рифм по группам + метрика «% зарифмованных слогов» (`analyze_rhyme_coloring`),
      таблица кандидатов очищается при оценке одного стиха.
- [x] LLMGenerator (Claude API, по умолчанию `claude-opus-4-8`, override `RHYMER_MODEL`):
      тема → best-of-N одним structured-output вызовом → самокоррекция по фидбэку RhymeEvaluator.
      Чекбокс «Генерировать через ИИ»; активен при заданном `ANTHROPIC_API_KEY`.
- [ ] Презентация (12 слайдов) — по плану ниже.
- [ ] Опционально: вкладка визуализации Юкавы.

## Запуск с ИИ-генерацией
```bash
export ANTHROPIC_API_KEY=...   # в той же сессии, откуда запускаете
cd src && ../venv/bin/python main.py
```
Без ключа чекбокс «Генерировать через ИИ» неактивен — работает генератор-заглушка из корпуса.
Замечание: диск был заполнен на 100% — очистил кэш pip (~5.5 ГБ), чтобы поставить `anthropic`.

## Запуск
```bash
cd src && ../venv/bin/python main.py        # GUI (нужен дисплей)
```
Первый запуск грузит модели RPST ~15–30 с (идёт в QThread, UI не виснет).

## Что уже есть (переиспользуем, не пишем заново)
- `venv`: Python 3.12, **torch 2.10, russian_scansion 1.0.22** — работают (`../a.py` — рабочий пример API RPST).
- API RPST: `tool = russian_scansion.create_rpst_instance(); s = tool.align(lines)` →
  `s.score`, `s.meter`, `s.rhyme_scheme`, `s.get_stressed_lines(...)`.
- `src/Model/TextConverter.py` — препроцессинг текста (lower / убрать пунктуацию / split на строки и слова).
- `Rhymer/detector.py` — анализ Юкавы (нужны scipy+matplotlib).

## Бэкенд генерации — РЕШЕНО: «сначала заглушка»
Генератор за единым интерфейсом `Generator.generate(params, n) -> list[str]`; реализации меняются местами.
- **День 1 (делаем сейчас): `StubGenerator`** — кандидаты = случайные комбинации строк из `poems/`
  (там стихи русских классиков). Цель — показать рабочий конвейер UI → оценка RPST → best-of-N **без сети и ключа**.
- **Позже (подключаем потом): реальная модель** за тем же интерфейсом:
  - Claude API: `claude-haiku-4-5-20251001` для N кандидатов, `claude-sonnet-4-6` для финала (`pip install anthropic`, `ANTHROPIC_API_KEY`).
  - либо локально Saiga/Vikhr через `transformers` (GB весов, оффлайн).

---

## Таймлайн (≈8 часов)

### 0. Setup (30 мин)
```bash
cd /home/zackarym/__RHYMER
source venv/bin/activate
pip install PySide6 scipy matplotlib anthropic
python a.py            # проверить, что RPST работает
export ANTHROPIC_API_KEY=...   # если Claude API
```

### 1. Модуль оценки рифмы `Rhymer/rhyme_eval.py` (1.5 ч)
- Обёртка над RPST: `evaluate(text:str) -> dict{score, meter, rhyme_scheme, stressed_lines}`.
- Кэшировать `create_rpst_instance()` (грузится медленно — один раз на процесс).
- Доп. метрика `rhyme_accuracy`: из размеченных ударений берём «хвост от последней ударной гласной»
  каждой строки, сверяем пары по `rhyme_scheme` → доля корректно срифмованных пар.
  Это «доделанный распознаватель рифм» в надёжном виде.

### 2. (Опционально, можно срезать) Детектор Юкавы как функция (1 ч)
- Из `detector.py` вынести `analyze(text) -> matplotlib Figure` (убрать `plt.show()`, вернуть fig для встраивания в Qt).
- Используется только во вкладке-визуализации. Если время поджимает — оставить как есть, показывать готовый `poem_analysis.png`.

### 3. Генератор + контроллер `Rhymer/generator.py` (2 ч)
- Единый интерфейс `Generator` с методом `generate(params, n) -> list[str]`.
- **`StubGenerator` (день 1):** собирает N кандидатов-четверостиший из строк `poems/` (через `TextConverter`),
  с учётом числа строк из params. Сети/ключа не требует.
- Контроллер `best_of_n(params, n)`: скоринг каждого кандидата через `rhyme_eval.evaluate`, сортировка, выбор лучшего.
- **Самокоррекция** (для реальной модели, позже): 1 повторный запрос с фидбэком RPST (какие строки не рифмуют / ломают размер).
- `LLMGenerator` (Claude API) — отдельный класс за тем же интерфейсом, подключается без изменения UI.

### 4. UI `Rhymer/app.py` (PySide6) (2 ч)
- Слева: поля — тема, размер (combobox), число строк, N кандидатов, схема рифмовки.
- Кнопка «Сгенерировать» → запуск генерации в `QThread` (чтобы UI не висел).
- Справа: лучший стих с ударениями, `score`/`meter`/`scheme`/`rhyme_accuracy`; список кандидатов с их score.
- Вкладка «Анализ»: цветокарта Юкавы для введённого/выбранного стиха.

### 5. Полировка + прогон (30 мин)
- 3–5 тем прогнать, сохранить скриншоты UI и пару `poem_analysis.png` для слайдов.
- README: как запустить (`python Rhymer/app.py`).

### 6. Презентация (1 ч) — 10–12 слайдов
1. Титул: тема, ФИО, магистратура ИИ.
2. Актуальность (из заметок): социальная, гос. поддержка культуры, научная — «мало ИИ, пишущих стихи».
3. Цель и задачи (анализ + генерация).
4. Постановка задачи.
5. Архитектура MVP (схема выше).
6. Распознавание рифм: RPST (ударения/размер/схема/score) **+ авторский подход Юкавы** (новизна, визуализация).
7. Генерация с обратной связью: как rhyme-score корректирует генерацию (best-of-N + самокоррекция).
8. Демо: скриншоты UI.
9. Метрики: RPST `score`, `rhyme_accuracy`, точность размера на N примерах.
10. Ограничения: Юкава шумит на больших текстах; зависимость от API.
11. Дальнейшая работа → направление ВКР: датасеты, fine-tune, RL с rhyme-reward.
12. Итоги.

---

## Минимальный результат к концу дня (если время кончается — режем сверху вниз)
1. **Обязательно:** `rhyme_eval.py` + `generator.py` (best-of-N) + презентация.
2. **Желательно:** PySide6 UI.
3. **Опционально:** вкладка с визуализацией Юкавы, самокоррекция, локальный фоллбэк-генератор.

## Проверка (verification)
- `python a.py` — RPST отдаёт score/meter/stressed lines.
- `python -c "from Rhymer.rhyme_eval import evaluate; print(evaluate(open('Rhymer/...').read()))"` на известном стихе → разумный score.
- Сгенерировать стих на тему «зима»: лучший кандидат имеет score выше среднего по N → best-of-N работает.
- `python Rhymer/app.py` — UI запускается, генерирует, показывает метрики, не зависает.
