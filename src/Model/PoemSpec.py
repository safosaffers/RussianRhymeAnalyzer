# Model/PoemSpec.py
# Карта стиха: всё, что решено до того, как написана первая строка.
# Семь шагов замысла (docs/stepsBeforeRhyming.txt) + четыре вопроса о поводе
# и говорящем + сцена высказывания. Дальше по конвейеру идёт карта, а не тема.
from dataclasses import dataclass, field

# Схема для structured output. Держится рядом с dataclass, чтобы поля не
# разъезжались: имена совпадают один в один.
SCHEMA = {
    "type": "object",
    "properties": {
        "thought": {"type": "string"},        # Мысль: один тезис
        "occasion": {"type": "string"},       # почему говорится именно сейчас
        "palette": {"type": "string"},        # тон, градус напряжения, регистр
        "objects": {"type": "array", "items": {"type": "string"}},
        "motion": {"type": "string"},         # режим развития и место поворота
        "speaker": {"type": "string"},        # кто говорит
        "addressee": {"type": "string"},      # кому
        "scene": {"type": "string"},          # где и когда он это говорит
        "thread": {"type": "string"},         # сквозной образ, лейтмотив
        "punchline": {"type": "string"},      # чем кончается, без морали
        "forbidden": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["thought", "occasion", "palette", "objects", "motion",
                 "speaker", "addressee", "scene", "thread", "punchline",
                 "forbidden"],
    "additionalProperties": False,
}


@dataclass
class PoemSpec:
    thought: str = ""
    occasion: str = ""
    palette: str = ""
    objects: list = field(default_factory=list)
    motion: str = ""
    speaker: str = ""
    addressee: str = ""
    scene: str = ""
    thread: str = ""
    punchline: str = ""
    forbidden: list = field(default_factory=list)

    @classmethod
    def from_dict(cls, d: dict) -> "PoemSpec":
        """Карта из ответа модели: лишние ключи игнорируем, недостающие пустые."""
        known = {f: d.get(f) for f in cls.__dataclass_fields__ if d.get(f) is not None}
        return cls(**known)

    def to_prompt(self) -> str:
        """Карта как часть задания генератору. Пустые поля не печатаем."""
        rows = [
            ("Мысль (один тезис)", self.thought),
            ("Повод: почему это говорится сейчас", self.occasion),
            ("Палитра (тон, градус напряжения)", self.palette),
            ("Объекты, которые должны попасть в стих", ", ".join(self.objects)),
            ("Движение и место поворота", self.motion),
            ("Говорящий", self.speaker),
            ("Адресат", self.addressee),
            ("Сцена высказывания", self.scene),
            ("Сквозной образ", self.thread),
            ("Чем кончается (без морали и вывода)", self.punchline),
            ("Слова, которых говорящий не скажет", ", ".join(self.forbidden)),
        ]
        return "\n".join(f"{k}: {v}" for k, v in rows if v)
