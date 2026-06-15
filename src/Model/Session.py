# Model/Session.py
# Сессия редактора (задел под удобный редактор стихов): состояние UI <-> JSON.
# Чистый JSON без Qt — формат версионируется для совместимости.
import json

SESSION_VERSION = 1


def save_session(path: str, state: dict) -> None:
    data = dict(state)
    data["version"] = SESSION_VERSION
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_session(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
