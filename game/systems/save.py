"""Сохранения: 3 ручных слота + автосохранение (слот 0), JSON.
- запись атомарная (tmp -> replace) и с резервной копией .bak предыдущего сохранения;
- загрузка проверяет совместимость (существа/приёмы есть в текущих данных) и чистит устаревшие предметы;
- повреждённый файл не роняет игру: читается .bak, а если и он плох - понятная ошибка SaveError."""
import json
import os
import shutil
import time
from pathlib import Path

from game.systems.state import PlayerState

from game.core import paths

SAVE_DIR = paths.SAVE_DIR
SLOTS = (1, 2, 3)
AUTO = 0
SAVE_VERSION = 2   # 2: IV/EV/характер у существ (сохранения версии 1 читаются со значениями по умолчанию)


class SaveError(Exception):
    pass


def _dir(folder):
    return Path(folder) if folder else SAVE_DIR


def slot_path(slot, folder=None):
    return _dir(folder) / ("autosave.json" if slot == AUTO else f"slot{slot}.json")


def _bak(p):
    return p.with_suffix(".bak")


def make_meta(state, location=None, now=None):
    return {"saved_at": now if now is not None else time.time(), "play_seconds": int(state.play_seconds),
            "badges": len(state.badges), "dex": len(state.caught), "money": state.money, "location": location or "",
            "party": [{"species": c.species_id, "name": c.name, "level": c.level} for c in state.party]}


def save(state, slot=1, folder=None, location=None, now=None):
    payload = state.to_dict()
    payload["version"] = SAVE_VERSION
    payload["meta"] = make_meta(state, location, now)
    p = slot_path(slot, folder)
    tmp = p.with_suffix(".tmp")
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=1)
        if p.exists():
            shutil.copy2(p, _bak(p))
        os.replace(tmp, p)
    except OSError as e:
        raise SaveError(f"Не удалось записать сохранение: {e}")
    if slot != AUTO:
        state.slot = slot


def autosave(state, folder=None, location=None):
    """Автосохранение, которое никогда не бросает исключений. True - получилось."""
    try:
        save(state, AUTO, folder, location)
        return True
    except Exception:  # noqa
        return False


def _read(path):
    try:
        with open(path, encoding="utf-8") as f:
            raw = json.load(f)
    except (OSError, ValueError) as e:
        raise SaveError(f"файл повреждён ({type(e).__name__})")
    if not isinstance(raw, dict):
        raise SaveError("файл повреждён")
    return raw


def check_compat(raw, data):
    """Бросает SaveError, если сохранение не подходит к текущим данным игры."""
    if raw.get("version", 1) > SAVE_VERSION:
        raise SaveError("сохранено в более новой версии игры")
    try:
        for c in raw["party"] + raw["storage"]:
            if c["species"] not in data.species:
                raise SaveError(f"несовместимо с этой версией игры (нет существа «{c['species']}»)")
            for m in c["moves"]:
                if m["id"] not in data.moves:
                    raise SaveError(f"несовместимо с этой версией игры (нет приёма «{m['id']}»)")
            for m in c.get("pending_moves", []):
                if m not in data.moves:
                    raise SaveError(f"несовместимо с этой версией игры (нет приёма «{m}»)")
    except (KeyError, TypeError):
        raise SaveError("файл повреждён или неполный")


def _candidates(slot, folder):
    p = slot_path(slot, folder)
    return [q for q in (p, _bak(p)) if q.exists()]


def read_meta(slot, folder=None, data=None):
    """None - слот пуст; иначе словарь: ok, meta-поля, error, from_backup."""
    paths = _candidates(slot, folder)
    if not paths:
        return None
    err = ""
    for i, p in enumerate(paths):
        try:
            raw = _read(p)
            if data is not None:
                check_compat(raw, data)
            meta = dict(raw.get("meta") or make_meta(PlayerState()))
            meta.update(slot=slot, ok=True, from_backup=(p.suffix == ".bak"))
            return meta
        except SaveError as e:
            err = err or str(e)
    return {"slot": slot, "ok": False, "error": err}


def list_slots(folder=None, data=None, with_auto=True):
    ids = ([AUTO] if with_auto else []) + list(SLOTS)
    return [(s, read_meta(s, folder, data)) for s in ids]


def latest_slot(folder=None, data=None):
    best = [(m["saved_at"], s) for s, m in list_slots(folder, data) if m and m.get("ok")]
    return max(best)[1] if best else None


def load(data, slot=1, folder=None):
    """PlayerState или None (слот пуст). SaveError - если сохранение не читается/несовместимо."""
    paths = _candidates(slot, folder)
    if not paths:
        return None
    err = None
    for p in paths:
        try:
            raw = _read(p)
            check_compat(raw, data)
            st = PlayerState.from_dict(data, raw)
        except SaveError as e:
            err = err or e
            continue
        except (KeyError, TypeError, ValueError, IndexError) as e:
            err = err or SaveError(f"файл повреждён ({type(e).__name__})")
            continue
        st.bag = {k: n for k, n in st.bag.items() if k in data.items and isinstance(n, int)}
        st.seen &= set(data.species)
        st.caught &= set(data.species)
        st.defeated &= set(data.trainers)
        st.slot = slot if slot != AUTO else None
        st.loaded_from_backup = p.suffix == ".bak"
        return st
    raise err


def delete(slot, folder=None):
    p = slot_path(slot, folder)
    for q in (p, _bak(p), p.with_suffix(".tmp")):
        if q.exists():
            q.unlink()


def exists(slot=1, folder=None):
    return bool(_candidates(slot, folder))
