# Работа с источниками: обзор литературы и библиография

Тема ВКР (рабочая): **генерация и автоматическая оценка рифмованной русской
поэзии с использованием LLM**. Ниже — методология поиска, аналитический обзор
по направлениям (SOTA) и категоризированный библиографический список.

> Записи с пометкой `[проверить]` найдены через поисковую выдачу, но точные
> выходные данные (год/издание/arXiv-id) не подтверждены чтением первоисточника —
> перед включением в итоговый список ВКР сверить по arXiv/DOI.

## Методология поиска
- **Базы и площадки:** eLibrary.ru (рег. обязательна), arXiv, ACL Anthology,
  Scopus, Web of Science, Hugging Face, GitHub.
- **Ключевые запросы:** *poetry generation*, *rhyme/meter detection*, *Russian
  scansion*, *controlled/constrained text generation*, *RLHF poetry*, *Russian
  LLM*, *poetry evaluation*, *русская поэзия корпус*.
- **Критерии отбора:** релевантность задаче (генерация ИЛИ оценка стиха),
  наличие воспроизводимого метода/кода/датасета, приоритет 2016–2026.
- Текущий объём — ~40 ключевых источников (международные + русскоязычные).
  Для целевых 70–100 расширяется отечественными работами по стиховедению и NLP
  с eLibrary и follow-up статьями по каждому методу.

## Аналитический обзор (SOTA, кратко)
- **Генерация поэзии** прошла путь RNN+конечные автоматы для рифмы/метра
  (Hafez, Deep-speare) → byte-/token-free и управляемые модели (ByGPT5, PoeLM) →
  LLM общего назначения с управлением через промпт и декодирование. Узкое место —
  одновременное соблюдение смысла, размера и рифмы.
- **Оценка стиха** для русского языка фактически закрывается инструментом RPST
  (Koziev): автоматическая расстановка ударений, классификация метра, детекция
  точных/неточных рифм и «техничности». Это опорный внешний верификатор проекта.
- **Управляемая генерация** (PPLM, FUDGE, constrained/grid-beam, COLD) даёт
  механизмы навязывания рифмы/метра без переобучения LLM — основа для будущего
  улучшения генератора.
- **RL с наградой за рифму** (Generate-and-Revise) и **best-of-N с
  регуляризацией** — прямая опора для направления ВКР: rhyme-score как reward.
- **Метрики оценки** поэзии слабо коррелируют между собой и с экспертами →
  нужен комбинированный протокол (автометрики RPST + human eval).

---

## 1. Нейросетевая/LLM-генерация поэзии
- Ghazvininejad M., Shi X., Choi Y., Knight K. (2016). *Generating Topical Poetry*. EMNLP 2016. https://aclanthology.org/D16-1126/ — Hafez: RNN + FSA для рифмы и метра.
- Ghazvininejad M., Shi X., Priyadarshi J., Knight K. (2017). *Hafez: an Interactive Poetry Generation System*. ACL 2017 (Demo). https://aclanthology.org/P17-4008/ — интерактивный контроль стиля.
- Lau J.H., Cohn T., Baldwin T., Brooke J., Hammond A. (2018). *Deep-speare: A Joint Neural Model of Poetic Language, Meter and Rhyme*. ACL 2018 / arXiv:1807.03491. https://arxiv.org/pdf/1807.03491 — совместная модель языка/метра/рифмы; код: https://github.com/jhlau/deepspeare
- Belouadi J., Eger S. (2023). *ByGPT5: End-to-End Style-conditioned Poetry Generation with Token-free Language Models*. ACL 2023 Findings / arXiv:2212.10474. https://arxiv.org/abs/2212.10474 — byte-level контроль рифмы/метра/аллитерации.
- Lee S.W. et al. (2022). *GPoeT-2: A GPT-2 Based Poem Generator*. arXiv:2205.08847. https://arxiv.org/abs/2205.08847 — forward+reverse генерация лимериков.
- Wang J., Zhang X., Zhou Y., Suh C., Rudin C. (2021). *There Once Was a Really Bad Poet, It Was Automated but You Didn't Know It*. TACL 2021 / arXiv:2103.03775. https://arxiv.org/abs/2103.03775 — LimGen: ограниченный поиск + storyline.
- Ormazabal A., Artetxe M., Soroa A., Labaka G., Agirre E. (2022). *PoeLM: A Meter- and Rhyme-Controllable Language Model for Unsupervised Poetry Generation*. EMNLP 2022 Findings / arXiv:2205.12206. https://arxiv.org/abs/2205.12206 — управляющие коды метра/рифмы без поэтического корпуса.
- Belouadi J., Eger S. (2024). *Let the Poem Hit the Rhythm: Beat-Aligned Poetry Generation*. arXiv:2406.10174. https://arxiv.org/html/2406.10174 — байтовый трансформер под ритмический паттерн.

## 2. Русскоязычные LLM
- Zmitrovich D. et al. (2023). *A Family of Pretrained Transformer Language Models for Russian*. arXiv:2309.10931 / ru-gpts. https://github.com/ai-forever/ru-gpts — семейство ruGPT-3.
- AI Forever (Sber). *ruGPT-3.5-13B*. Hugging Face. https://huggingface.co/ai-forever/ruGPT-3.5-13B — основа GigaChat.
- Shliazhko O. et al. (2022). *mGPT: Few-Shot Learners Go Multilingual*. arXiv:2204.07580. https://arxiv.org/abs/2204.07580 — мультиязычная GPT-3 (вкл. русский); код: https://github.com/ai-forever/mgpt
- Yandex (2022). *YaLM-100B*. GitHub. https://github.com/yandex/YaLM-100B — открытая 100B-модель, преим. русский корпус.
- Nikolich A. et al. (2024). *Vikhr: Open-Source Instruction-Tuned LLMs for Russian*. arXiv:2405.13929. https://arxiv.org/abs/2405.13929 — адаптация токенизатора + continued pretraining.
- Gusev I. *saiga_llama3_8b*. Hugging Face. https://huggingface.co/IlyaGusev/saiga_llama3_8b — русский instruct-чатбот (Llama-3 8B, SFT+KTO).
- Mukhamedshina D. et al. (2025). *GigaChat Family: Efficient Russian Language Modeling Through MoE*. arXiv:2506.09440. https://arxiv.org/abs/2506.09440 — MoE-семейство Sber.
- Fenogenova A. et al. (2024). *MERA: A Comprehensive LLM Evaluation in Russian*. arXiv:2401.04531. https://arxiv.org/abs/2401.04531 — бенчмарк из 21 задачи.

## 3. Автоматический анализ стиха: метр, ударение, рифма
- Koziev I. (2025). *Automated Evaluation of Meter and Rhyme in Russian Generative and Human-Authored Poetry*. arXiv:2502.20931. https://arxiv.org/abs/2502.20931 — **ключевая** по RPST: «техничность» 0–1, детекция рифм/дефектов.
- Koziev I. *RussianPoetryScansionTool*. GitHub. https://github.com/Koziev/RussianPoetryScansionTool — библиотека проекта (ударения, метр, рифма; MIT).
- Koziev I. *ArsPoetica (~8.5k poems)*. Hugging Face. https://huggingface.co/datasets/inkoziev/ArsPoetica — корпус с ударениями для валидации RPST.
- Koziev I. *Rifma*. GitHub. https://github.com/Koziev/Rifma — 5002 фрагмента с разметкой ударений и схемы рифмовки.
- Plecháč P. (2018). *A Collocation-Driven Method of Discovering Rhymes*. Taming the Corpus (Springer); RhymeTagger. https://github.com/versotym/rhymetagger — language-independent детектор рифм (вкл. русский).
- Plecháč P. et al. (2026). *Training Data Size Sensitivity in Unsupervised Rhyme Recognition*. arXiv:2604.08156. https://arxiv.org/abs/2604.08156v1 `[проверить]` — RhymeTagger vs LLM на 7 языках; LLM без фонетики слабее.
- Koziev I. *rupostagger — POS Tagger for Russian*. GitHub. https://github.com/Koziev/rupostagger — разрешение омографов при разметке ударений.
- Koziev I. *rutokenizer*. GitHub. https://github.com/Koziev/rutokenizer — сегментация/токенизация в пайплайне RPST.

## 4. Контролируемая/ограниченная генерация
- Dathathri S. et al. (2020). *Plug and Play Language Models (PPLM)*. ICLR 2020 / arXiv:1912.02164. https://arxiv.org/abs/1912.02164 — управление атрибутами без переобучения; код: https://github.com/uber-research/PPLM
- Yang K., Klein D. (2021). *FUDGE: Controlled Text Generation With Future Discriminators*. NAACL 2021 / arXiv:2104.05218. https://arxiv.org/abs/2104.05218 — пословная коррекция вероятностей; тест на завершении куплетов (рифма).
- Hokamp C., Liu Q. (2017). *Lexically Constrained Decoding Using Grid Beam Search*. arXiv:1704.07138. https://arxiv.org/abs/1704.07138 — включение заданных слов в вывод.
- Qin L. et al. (2022). *COLD Decoding: Energy-based Constrained Text Generation*. arXiv:2202.11705. https://arxiv.org/pdf/2202.11705 — гибкие лексические/стилевые ограничения.
- Lu X. et al. (2021). *NeuroLogic Decoding*. arXiv:2010.12884. https://arxiv.org/pdf/2010.12884v1 — декодирование с логическими предикатами-ограничениями.
- Manurung R., Ranta A. et al. *"Poetic" Statistical Machine Translation: Rhyme and Meter*. EMNLP 2010. https://aclanthology.org/D10-1016.pdf — ранние ограничения ритма/рифмы.

## 5. RLHF и RL с вознаграждением для генерации
- Huang S. et al. (2024). *The N+ Implementation Details of RLHF with PPO (TL;DR)*. arXiv:2403.17031. https://arxiv.org/pdf/2403.17031 — воспроизводимость RLHF+PPO (содержит ссылку на Stiennon et al. 2020).
- Casas N. et al. (2021). *Generate and Revise: Reinforcement Learning in Neural Poetry*. arXiv:2102.04114. https://arxiv.org/abs/2102.04114 — генерация + коррекция через PPO с reward за схему рифмы.
- Casas N. et al. (2023). *Creative Data Generation: A Review Focusing on Text and Poetry*. arXiv:2305.08493. https://arxiv.org/pdf/2305.08493 — обзор, включая RL-доработку.
- Lee H. et al. (2023). *RLAIF vs. RLHF: Scaling RL from Human Feedback with AI Feedback*. arXiv:2309.00267. https://arxiv.org/html/2309.00267v3 `[проверить]` — AI-обратная связь вместо человеческой разметки.
- *Regularized Best-of-N Sampling with MBR Objective for LM Alignment*. arXiv:2404.01054. https://arxiv.org/abs/2404.01054 `[проверить]` — снижение reward hacking при best-of-N.

## 6. Оценка генерируемой поэзии (метрики, human eval)
- Koziev I. (2025). *Automated Evaluation of Meter and Rhyme...*. arXiv:2502.20931. https://arxiv.org/abs/2502.20931 — сравнение генеративных и авторских текстов по метру/рифме.
- Lau J.H. et al. (2018). *Deep-speare* (раздел expert evaluation). https://arxiv.org/pdf/1807.03491 — слабая корреляция автометрик с экспертной оценкой.
- Belouadi J., Eger S. (2024). *Evaluating Diversity in Automatic Poetry Generation*. arXiv:2406.15267. https://arxiv.org/html/2406.15267v1 — метрики разнообразия.
- *POEMetric: The Last Stanza of Humanity*. arXiv:2604.03695. https://arxiv.org/html/2604.03695v1 `[проверить]` — фреймворк из 10 метрик (instruction-following + творчество).
- *Introducing Aspects of Creativity in Automatic Poetry Generation*. arXiv:2002.02511. https://arxiv.org/pdf/2002.02511 `[проверить]` — критерии Fluency/Meaning/Coherence/Relevance/Aesthetics.
- Manurung R. et al. *Autonomous Haiku Generation*. arXiv:1906.08733. https://arxiv.org/pdf/1906.08733 `[проверить]` — соответствие форме (5-7-5) как proxy-метрика.

## 7. Датасеты/корпуса (детально — см. [03_data.md](03_data.md))
- ArsPoetica (HF), Rifma (GitHub), stihi_ru (HF), Поэтический подкорпус НКРЯ,
  Gutenberg Poetry Corpus, PULPO (мультиязычный). Полное описание, лицензии и
  протокол — в `03_data.md`.

---

## Регистрация на eLibrary и оформление по ГОСТ
- **eLibrary.ru** — регистрация обязательна по Заданию 1 (профиль автора, доступ
  к РИНЦ, поиск отечественных публикаций): https://elibrary.ru
- **Стандарт оформления ссылок:** ГОСТ Р 7.0.100–2018 (библиографическая
  запись); для оформления текста отчёта/ВКР — ГОСТ 7.32–2017.
- **Инструменты (упрощают оформление):**
  - Zotero (бесплатный, CSL-стили) — https://www.zotero.org/
  - Стиль «Russian GOST R 7.0.100-2018» (CSL) для Zotero/Mendeley — https://bibliostyle.ru/stil-gost-7-0-100-2018-dlya-mendeley-i-zotero-style-russian-gost-r-7-0-100-2018-csl/
  - Каталог CSL-стилей по ГОСТ (вкл. 7.32-2017) — https://bibliostyle.ru/stiles/ , https://firescience.ru/project/zoterogost/7322017.html
  - Mendeley — https://www.mendeley.com/

**Как проще всего оформлять ссылки** (ответ на PS из задания): вести базу в
**Zotero**, подключить CSL-стиль ГОСТ Р 7.0.100-2018, добавлять источники
кнопкой-коннектором из браузера (DOI/arXiv подтягиваются автоматически) и
вставлять ссылки/список литературы плагином Zotero в Word/LibreOffice — список
пересобирается автоматически в нужном стиле.
