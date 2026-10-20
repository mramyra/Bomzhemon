"""Характеристики по правилам покемонов (упрощённо, без пола/шайни):
  HP     = (2*База + IV + EV//4) * Ур / 100 + Ур + 10
  прочее = ((2*База + IV + EV//4) * Ур / 100 + 5) * Характер     (Характер: x1.1 / x0.9 / x1.0)
IV 0..31 - врождённый потенциал, у каждого существа свой. EV 0..252 на характеристику, 510 всего - растут от побед.
Характер даёт +10% к одной характеристике и -10% к другой (или нейтральный). Без округления, как в оригинале - целочисленная арифметика."""
import random as _random

STAT_KEYS = ("hp", "atk", "def", "spa", "spd", "spe")
STAT_RU = {"hp": "HP", "atk": "Атака", "def": "Защита", "spa": "Спец. атака", "spd": "Спец. защита", "spe": "Скорость"}
IV_MAX, IV_DEFAULT = 31, 15
EV_STAT_MAX, EV_TOTAL_MAX = 252, 510

# (id, русское имя, +10% к, -10% к)
_NATURES = [
    ("hardy", "Крепкий", None, None), ("lonely", "Одинокий", "atk", "def"), ("adamant", "Борзый", "atk", "spa"),
    ("naughty", "Хулиган", "atk", "spd"), ("brave", "Отчаянный", "atk", "spe"),
    ("bold", "Матёрый", "def", "atk"), ("docile", "Покладистый", None, None), ("impish", "Хитрый", "def", "spa"),
    ("lax", "Расслабленный", "def", "spd"), ("relaxed", "Неспешный", "def", "spe"),
    ("modest", "Скромный", "spa", "atk"), ("mild", "Мягкий", "spa", "def"), ("bashful", "Застенчивый", None, None),
    ("rash", "Дерзкий", "spa", "spd"), ("quiet", "Тихий", "spa", "spe"),
    ("calm", "Спокойный", "spd", "atk"), ("gentle", "Ласковый", "spd", "def"), ("careful", "Бдительный", "spd", "spa"),
    ("quirky", "Чудной", None, None), ("sassy", "Наглый", "spd", "spe"),
    ("timid", "Робкий", "spe", "atk"), ("hasty", "Торопыга", "spe", "def"), ("jolly", "Весёлый", "spe", "spa"),
    ("naive", "Наивный", "spe", "spd"), ("serious", "Серьёзный", None, None),
]
NATURES = {nid: (name, up, down) for nid, name, up, down in _NATURES}
NEUTRAL = "hardy"


def calc_hp(base, level, iv=IV_DEFAULT, ev=0):
    return (2 * base + iv + ev // 4) * level // 100 + level + 10


def calc_other(base, level, iv=IV_DEFAULT, ev=0, mult_percent=100):
    return ((2 * base + iv + ev // 4) * level // 100 + 5) * mult_percent // 100


def nature_mult(nature_id, stat):
    _, up, down = NATURES[nature_id]
    return 110 if stat == up else 90 if stat == down else 100


def nature_label(nature_id):
    name, up, down = NATURES[nature_id]
    if not up:
        return f"{name} (без бонусов)"
    return f"{name} (+{STAT_RU[up]}, -{STAT_RU[down]})"


def roll_ivs(rng=None, perfect=0):
    """Случайные IV; perfect - сколько характеристик гарантированно 31 (для легендарных)."""
    rng = rng or _random
    iv = {k: rng.randint(0, IV_MAX) for k in STAT_KEYS}
    for k in rng.sample(STAT_KEYS, min(perfect, len(STAT_KEYS))):
        iv[k] = IV_MAX
    return iv


def roll_nature(rng=None):
    return (rng or _random).choice(list(NATURES))


def default_ev_yield(species):
    """Сколько EV даёт победа над видом: очки в сильнейшую характеристику, больше у более сильных видов."""
    b = species["base"]
    top = max(STAT_KEYS, key=lambda k: (b[k], -STAT_KEYS.index(k)))
    bst = sum(b.values())
    return {top: 1 if bst <= 300 else 2 if bst <= 430 else 3}


def ev_yield(species):
    return species.get("ev_yield") or default_ev_yield(species)


def iv_grade(total):
    """Словесная оценка суммы IV (0..186)."""
    for limit, text in ((60, "Так себе"), (100, "Средний"), (130, "Крепкий"), (160, "Отличный"), (180, "Выдающийся")):
        if total <= limit:
            return text
    return "Почти идеальный" if total < 186 else "Идеальный"
