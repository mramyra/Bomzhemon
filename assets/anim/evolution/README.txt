СВОЯ АНИМАЦИЯ ЭВОЛЮЦИИ (необязательно)
Положи сюда папку с PNG-кадрами, они проигрываются поверх фазы "мерцание" вместо/вместе с заготовкой:
  assets/anim/evolution/<id_до>_<id_после>/000.png, 001.png, ...   - для конкретной эволюции (например krysa_spidkrys)
  assets/anim/evolution/default/000.png, 001.png, ...             - для всех остальных
Кадры берутся по алфавиту, скорость - поле "fps" в data/animations.json (раздел evolution), размер любой (рисуются по центру).
Тайминги фаз (intro, flicker, burst, reveal), частота мерцания и размер спрайта - там же, в data/animations.json.
Звук: во время анимации игра шлёт события через app.events (evolution_start / _intro / _flicker / _burst / _reveal / _cancelled / _done),
на которые потом подпишется звуковой слой.
