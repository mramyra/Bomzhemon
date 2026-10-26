#!/usr/bin/env python3
"""
Берёт PNG из "not crop" (объекты с прозрачным фоном),
обрезает по содержимому, растягивает до 192×192 и сохраняет в "croped".
"""

from pathlib import Path
from PIL import Image

SRC_DIR = Path("not crop")
DST_DIR = Path("croped")
TARGET_SIZE = (192, 192)

def get_content_bbox(img: Image.Image):
    """Возвращает bounding box непрозрачных пикселей (или None)."""
    if img.mode != "RGBA":
        img = img.convert("RGBA")
    # Альфа-канал
    alpha = img.split()[-1]
    # bbox = (left, upper, right, lower)
    return alpha.getbbox()

def main():
    src = SRC_DIR.resolve()
    dst = DST_DIR.resolve()

    if not src.is_dir():
        print(f"Ошибка: папка не найдена → {src}")
        return 1

    dst.mkdir(parents=True, exist_ok=True)

    png_files = sorted(list(src.glob("*.png")) + list(src.glob("*.PNG")))
    if not png_files:
        print(f"PNG-файлы не найдены в: {src}")
        return 0

    print(f"Найдено {len(png_files)} PNG")
    print(f"Обрезка по объекту + растягивание до 192×192 → '{dst}'\n")

    success = 0
    for path in png_files:
        try:
            with Image.open(path) as img:
                original_size = img.size

                # Приводим к RGBA, чтобы корректно работать с прозрачностью
                if img.mode != "RGBA":
                    img = img.convert("RGBA")

                bbox = get_content_bbox(img)
                if bbox is None:
                    print(f"  ✗ {path.name}: полностью прозрачное изображение")
                    continue

                # Обрезаем до объекта
                cropped = img.crop(bbox)

                # Растягиваем до 192×192 без сохранения пропорций
                resized = cropped.resize(TARGET_SIZE, Image.Resampling.LANCZOS)

                out_path = dst / path.name
                resized.save(out_path, format="PNG", optimize=True)

                print(f"  ✓ {path.name}  ({original_size[0]}×{original_size[1]} → crop {bbox[2]-bbox[0]}×{bbox[3]-bbox[1]} → 192×192)")
                success += 1
        except Exception as e:
            print(f"  ✗ {path.name}: {e}")

    print(f"\nГотово. Обработано {success}/{len(png_files)}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())