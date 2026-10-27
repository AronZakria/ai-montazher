"""Безопасная зона Reels (1080×1920) по схеме Арона — docs/безопасная_зона.png.
python3 tools/ekran/zona.py <кадр.jpg|png> <выход.jpg>  — наложить зону на кадр для проверки."""
import sys
from PIL import Image, ImageDraw

W, H = 1080, 1920
TOP, BOTTOM, SIDE, ICONS = 220, 500, 35, 120   # сверху, снизу, по бокам, колонка иконок справа внизу
# низ поднят 1500 → 1420 (Арон, 2026-10-19, субтитры на 1435–1483: «надо поднять вверх безопасные зоны, из которых ты вышел»)
ICONS_FROM = 1150                              # с этой высоты справа иконки (лайк, коммент, репост)
SAFE = (SIDE, TOP, W - SIDE, H - BOTTOM)       # 35..1045 × 220..1420
CENTER = (540, 860)                            # центр внимания: сюда ставим место действия


def overlay(img):
    img = img.convert("RGB").resize((W, H))
    o = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(o)
    red = (255, 40, 40, 90)
    d.rectangle((0, 0, W, TOP), fill=red)
    d.rectangle((0, H - BOTTOM, W, H), fill=red)
    d.rectangle((0, TOP, SIDE, H - BOTTOM), fill=red)
    d.rectangle((W - SIDE, TOP, W, ICONS_FROM), fill=red)
    d.rectangle((W - ICONS, ICONS_FROM, W, H - BOTTOM), fill=red)
    cx, cy = CENTER
    d.line((cx - 30, cy, cx + 30, cy), fill=(255, 0, 0, 255), width=4)
    d.line((cx, cy - 30, cx, cy + 30), fill=(255, 0, 0, 255), width=4)
    return Image.alpha_composite(img.convert("RGBA"), o).convert("RGB")


if __name__ == "__main__":
    overlay(Image.open(sys.argv[1])).save(sys.argv[2], quality=90)
