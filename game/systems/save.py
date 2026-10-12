"""Сохранения в JSON. Любой момент, несколько слотов. Запись атомарная (tmp + replace)."""
import json
import os
from pathlib import Path

from game.systems.state import PlayerState

SAVE_DIR = Path(__file__).resolve().parents[2] / "saves"


def slot_path(slot, folder=SAVE_DIR):
    return Path(folder) / f"slot{slot}.json"


def save(state, slot=1, folder=SAVE_DIR):
    Path(folder).mkdir(parents=True, exist_ok=True)
    p = slot_path(slot, folder)
    tmp = p.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state.to_dict(), f, ensure_ascii=False, indent=1)
    os.replace(tmp, p)


def load(data, slot=1, folder=SAVE_DIR):
    p = slot_path(slot, folder)
    if not p.exists():
        return None
    with open(p, encoding="utf-8") as f:
        return PlayerState.from_dict(data, json.load(f))


def exists(slot=1, folder=SAVE_DIR):
    return slot_path(slot, folder).exists()
