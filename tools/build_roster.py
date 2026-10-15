"""ОДНОРАЗОВЫЙ генератор data/species.json по таблице «Бомжекимон» (44 существа).
ВНИМАНИЕ: перезаписывает data/species.json. После первой генерации правь JSON напрямую.
Статы здесь - заготовка: сумма статов по стадии развития x профиль роли. Баланс: python -m tools.balance_report"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

ROLES = {  # hp, atk, def, spa, spd, spe
    "bal": (1, 1, 1, 1, 1, 1), "fast": (0.8, 1.1, 0.8, 0.8, 0.8, 1.7), "tank": (1.4, 0.9, 1.4, 0.7, 1.1, 0.5),
    "brute": (1.2, 1.5, 1.0, 0.6, 0.8, 0.9), "mage": (0.9, 0.6, 0.8, 1.5, 1.2, 1.0),
    "glass": (0.7, 1.4, 0.6, 1.1, 0.7, 1.5), "swarm": (0.7, 1.2, 0.9, 0.9, 0.7, 1.4),
}
# тир: (сумма статов, шанс поимки, опыт за победу, расписание уровней для приёмов)
TIERS = {
    "b": (285, 235, 55, [1, 1, 6, 12, 20, 30]),     # базовая форма, есть куда расти
    "m": (385, 120, 120, [1, 1, 1, 1, 24, 34]),     # середина цепочки
    "f1": (410, 70, 150, [1, 1, 1, 1, 24, 34]),     # финал после одной эволюции
    "f2": (480, 45, 190, [1, 1, 1, 1, 36, 44]),     # финал после двух эволюций
    "s": (360, 45, 110, [1, 1, 1, 10, 20, 30]),     # без эволюций
    "k": (470, 20, 220, [1, 1, 1, 1, 30, 40]),      # король (крафт)
    "L": (590, 3, 300, [1, 1, 1, 1, 40, 50]),       # легендарное
}
L, I, T = "level", "item", "trade"

# id: (имя, типы, роль, тир, поправка_суммы, [приёмы по порядку], [эволюции], описание)
R = {
 "khomechennok": ("Хомеченнок", ["rodent"], "bal", "b", 0, ["gnaw", "squeak", "quick_gnaw", "play_dead", "rat_scuffle"], [(L, 16, "khomyak")], "Щёки полны, карманы пусты. Классика."),
 "khomyak": ("Хомяк", ["rodent"], "tank", "m", 0, ["gnaw", "play_dead", "rat_scuffle", "squeak", "bite"], [(L, 33, "khomemertv")], "Запасливый. В холодильнике мира уже ничего не осталось."),
 "khomemertv": ("Хомемертв", ["ghost", "rodent"], "mage", "f2", 0, ["whisper", "grave_chill", "delirium", "nap", "rat_scuffle"], [], "Выглядит неважно. Ведёт себя тоже."),
 "shchenok": ("Щенок", ["dog"], "bal", "b", 0, ["bark", "snarl", "bite", "howl", "chase"], [(L, 13, "pes")], "Верит в людей. Зря."),
 "pes": ("Пес", ["dog"], "brute", "m", 0, ["bite", "bark", "snarl", "howl", "chase"], [(L, 36, "volchara")], "Знает, где твоя нычка."),
 "volchara": ("Волчара", ["dog"], "fast", "f2", 0, ["bite", "howl", "chase", "snarl", "scandal"], [], "Бывший Пёс. Теперь с принципами."),
 "kotenok": ("Котёнок", ["cat"], "fast", "b", 0, ["scratch", "hiss", "claws", "night_yowl", "pounce"], [(L, 14, "kot")], "Милый. Пока не подойдёшь."),
 "kot": ("Кот", ["cat"], "fast", "m", 0, ["claws", "hiss", "night_yowl", "scratch", "pounce"], [(L, 30, "beshekot")], "Гуляет сам по себе и по твоим вещам."),
 "beshekot": ("Бешекот", ["cat", "poison"], "bal", "f2", 0, ["claws", "hiss", "night_yowl", "scratch", "drool", "pounce"], [], "С пеной у рта доказывает своё."),
 "yaitso": ("Яйцо", ["bird"], "bal", "b", -10, ["peck", "droppings", "wing_flap", "dive_bomb"], [(L, 12, "ptenets")], "Что внутри - загадка. Опять."),
 "ptenets": ("Птенец", ["bird"], "bal", "m", 0, ["peck", "droppings", "dive_bomb", "wing_flap"], [(L, 26, "golub"), (T, "krysa", "goluvin")], "Клюв раскрыт, совесть закрыта."),
 "golub": ("Голубь", ["bird"], "brute", "f2", 0, ["dive_bomb", "droppings", "squawk", "wing_flap"], [], "Знает, где у вас бутерброд."),
 "goluvin": ("Голувин", ["bird", "rodent"], "bal", "f1", 0, ["dive_bomb", "droppings", "gnaw", "wing_flap"], [], "Плод обмена и взаимного непонимания."),
 "strannoe_yaitso": ("Странное яйцо", ["bird"], "bal", "b", -10, ["peck", "droppings", "wing_flap", "dive_bomb"], [(L, 13, "pleshinets")], "Тикает. Нет, показалось."),
 "pleshinets": ("Плешинец", ["bird"], "glass", "m", 0, ["peck", "wing_flap", "droppings", "dive_bomb"], [(L, 30, "popugaeshche")], "Перьев мало, амбиций много."),
 "popugaeshche": ("Попугаеще", ["bird"], "mage", "f2", 0, ["squawk", "dive_bomb", "wing_flap", "droppings", "delirium"], [], "Повторяет всё, что слышал в подворотне. Прям всё."),
 "lisenok": ("Лисенок", ["dog"], "fast", "b", 0, ["bark", "snarl", "bite", "howl", "chase"], [(L, 22, "lisitsa")], "Рыжий воришка с большими глазами."),
 "lisitsa": ("Лисица", ["dog"], "fast", "f1", 0, ["bite", "howl", "chase", "snarl"], [], "Знает, где курятник. И где участковый."),
 "enot": ("Енот", ["dog"], "bal", "b", 0, ["bite", "bark", "scratch", "snarl", "howl"], [(I, "bin_lid", "rytsenot")], "Полоскает всё подряд. Включая твоё белое."),
 "rytsenot": ("Рыценот", ["dog", "human"], "tank", "f1", 0, ["bite", "knight_charge", "howl", "snarl", "shield_wall"], [], "Крышка бака - щит. Остальное - дело чести."),
 "tarakan": ("Таракан", ["bug"], "tank", "b", 0, ["sting", "crawl", "gnaw", "buzz", "swarm"], [(I, "bait", "tararoy")], "Переживёт всё. Кроме тапка."),
 "tararoy": ("Тарарой", ["bug"], "mage", "f1", 0, ["swarm", "buzz", "sting", "crawl"], [], "Не один. Совсем не один."),
 "gusenitsa": ("Гусеница", ["bug"], "tank", "b", 0, ["sting", "crawl", "cocoon", "scale_dust"], [(L, 9, "kokonishche")], "Жуёт. Растёт. Мечтает."),
 "kokonishche": ("Коконище", ["bug"], "tank", "m", 0, ["cocoon", "sting", "scale_dust", "crawl", "buzz"], [(L, 16, "babakach"), (I, "palto", "mol")], "Висит в углу и копит силы. Как и все мы."),
 "babakach": ("Бабакач", ["bug", "human"], "brute", "f2", 0, ["stinger", "scandal", "buzz", "crawl", "shield_wall"], [], "Когда-то была бабочкой. Теперь качалка."),
 "mol": ("Моль", ["bug"], "mage", "f1", 0, ["scale_dust", "buzz", "sting", "crawl"], [], "Ест пальто. Любит пальто. Живёт в пальто."),
 "nedopchel": ("Недопчел", ["bug"], "mage", "b", 0, ["sting", "crawl", "buzz", "scale_dust", "swarm"], [(L, 16, "pchel"), (I, "molochko", "korolevchel")], "Пчела, но без уверенности."),
 "pchel": ("Пчел", ["bug"], "fast", "m", 0, ["sting", "buzz", "swarm", "crawl", "stinger"], [(L, 30, "boevoypchel")], "Работает за двоих. Платят за одного."),
 "boevoypchel": ("Боевойпчел", ["bug", "poison"], "brute", "f2", 0, ["stinger", "swarm", "buzz", "cologne"], [], "Жало с допуском. Допуск не выдан."),
 "korolevchel": ("Королевчел", ["bug"], "mage", "f1", 0, ["swarm", "buzz", "scale_dust", "crawl"], [], "Весь улей на её молочке. Буквально."),
 "pleshipes": ("Плешипес", ["dog"], "bal", "b", 0, ["bark", "snarl", "bite", "howl", "chase"], [(T, "pleshipes", "siamsobek"), (T, "cheremshkot", "kotopes")], "Лысый, но не комплексует. Мёрзнет - да."),
 "siamsobek": ("Сиамсобек", ["dog", "cat"], "fast", "f1", 0, ["bite", "claws", "howl", "night_yowl"], [], "Сиамская собака. Не спрашивай, как."),
 "cheremshkot": ("Черемшкот", ["cat"], "bal", "b", 0, ["scratch", "hiss", "claws", "snarl", "night_yowl"], [(T, "pleshipes", "kotopes")], "Пахнет черемшой. Подозрительно сильно."),
 "kotopes": ("Котопес", ["cat", "dog"], "brute", "f1", 0, ["claws", "bite", "pounce", "howl"], [], "Не определился. Громко."),
 "golubiny_korol": ("Голубиный король", ["bird", "human"], "brute", "L", 0, ["dive_bomb", "squawk", "scandal", "balcony", "shield_wall"], [], "Бомж в костюме голубя. Или голубь в костюме бомжа. Он сам уже не помнит."),
 "bingus": ("Бингус", ["cat"], "fast", "L", 0, ["pounce", "night_yowl", "claws", "hiss"], [], "Лысый. Легендарный. Бингус."),
 "belochka": ("Белочка", ["rodent", "ghost"], "mage", "L", 0, ["hallucination", "delirium", "quick_gnaw", "whisper"], [], "Массовая галлюцинация. Видят все, кому нужно и не нужно."),
 "dikiy": ("Дикий", ["human"], "bal", "s", 0, ["cuff", "balcony", "slipper", "scandal", "whisper"], [], "Одичавший бомж. Ветки развития пока не придуманы."),
 "krysa": ("Крыса", ["rodent"], "bal", "b", 0, ["gnaw", "squeak", "quick_gnaw", "play_dead", "rat_scuffle"],
           [(I, "syringe", "spidkrys"), (I, "tin_can", "rytsekrys"), (T, "ptenets", "krysolet"), (I, "maggots", "gniekrys")], "Хозяйка свалки. Берёт числом, а не умением."),
 "spidkrys": ("Спидкрыс", ["rodent"], "fast", "f1", 0, ["quick_gnaw", "adrenaline", "rat_scuffle", "bite"], [], "Всегда куда-то опаздывает. Всегда успевает."),
 "rytsekrys": ("Рыцекрыс", ["rodent", "human"], "tank", "f1", 0, ["gnaw", "knight_charge", "rat_scuffle", "squeak", "shield_wall"], [], "Консервная банка - латы. Свалка - королевство."),
 "krysiny_korol": ("Крысиный король", ["rodent", "poison"], "brute", "k", 0, ["rat_scuffle", "expired", "squeak", "play_dead", "scandal"], [], "Пять крыс, одна судьба. Получается только крафтом."),
 "krysolet": ("Крысолет", ["rodent", "bird"], "fast", "f1", 0, ["gnaw", "wing_flap", "dive_bomb", "quick_gnaw"], [], "Крыса, которая посмотрела на голубей и решила: могу."),
 "gniekrys": ("Гниекрыс", ["poison", "rodent"], "mage", "f1", 0, ["rot_bite", "shawarma", "gnaw", "cologne"], [], "Пахнет так, что враг сдаётся первым."),
}


def build():
    out = {}
    for sid, (name, types, role, tier, adj, moves, evos, desc) in R.items():
        bst, catch, exp, sched = TIERS[tier]
        w = ROLES[role]
        base = {k: max(10, round((bst + adj) * wi / sum(w))) for k, wi in zip(("hp", "atk", "def", "spa", "spd", "spe"), w)}
        evolutions = []
        for e in evos:
            if e[0] == L:
                evolutions.append({"method": L, "level": e[1], "into": e[2]})
            elif e[0] == I:
                evolutions.append({"method": I, "item": e[1], "into": e[2]})
            else:
                evolutions.append({"method": T, "partner": e[1], "into": e[2]})
        out[sid] = {"name": name, "types": types, "base": base, "catch_rate": catch, "base_exp": exp,
                    "learnset": [[lv, m] for lv, m in zip(sched, moves)], "evolutions": evolutions, "desc": desc}
        if tier == "L":
            out[sid]["legendary"] = True
    return out


if __name__ == "__main__":
    sp = build()
    assert len(sp) == 44, len(sp)
    with open(ROOT / "data" / "species.json", "w", encoding="utf-8") as f:
        json.dump(sp, f, ensure_ascii=False, indent=1)
    names = ["# id -> имя (для файлов спрайтов: assets/sprites/creatures/<id>.png)"]
    names += [f"{k:<18}{v['name']:<20}{'/'.join(v['types'])}{'  (легендарное)' if v.get('legendary') else ''}" for k, v in sp.items()]
    (ROOT / "assets" / "sprites" / "creatures" / "NAMES.txt").write_text("\n".join(names) + "\n", encoding="utf-8")
    print("species.json:", len(sp))
