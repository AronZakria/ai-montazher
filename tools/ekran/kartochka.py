"""Вставка-карточка: картинка (скриншот письма, документа) уменьшена целиком и стоит в центре безопасной зоны
на мягком фоне. Для вещей, которые надо показать целиком, а не «ездить» по ним.

    python3 tools/ekran/kartochka.py <картинка> <выход.mp4> <секунды> [--blur x,y,w,h …] [--mark x,y,w,h@t …] [--zona]

--blur  — размыть прямоугольник (px исходной картинки): почта, телефон, имена, компании.
--mark  — с момента t (с) подсветить прямоугольник жёлтым маркером — «вот это главное».
Карточка чуть приближается за время вставки (1,00 → 1,04), чтобы картинка не стояла мёртво.
"""
import math, subprocess, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, str(Path(__file__).parent))
from zona import W, H, CENTER, SAFE, ICONS, ICONS_FROM, overlay

FPS = 30
CARD_W = 950          # ширина карточки в кадре: с наездом ×1,04 — 988, внутри зоны 35..1045
CARD_H = 1180         # высота не больше: с наездом ×1,04 — 1227, внутри зоны 220..1500 (1280)
RADIUS, SHADOW = 28, 40


def args():
    a = sys.argv[1:]
    src, out, dur = a[0], a[1], float(a[2])
    blur, marks = [], []
    i = 3
    while i < len(a):
        if a[i] == "--blur":
            i += 1
            while i < len(a) and not a[i].startswith("--"):
                blur.append(tuple(map(int, a[i].split(",")))); i += 1
        elif a[i] == "--mark":
            i += 1
            while i < len(a) and not a[i].startswith("--"):
                box, t = a[i].split("@"); marks.append((tuple(map(int, box.split(","))), float(t))); i += 1
        else:
            i += 1
    return src, out, dur, blur, marks, "--zona" in a


def main():
    src, out, dur, blur, marks, zone = args()
    img = Image.open(src).convert("RGB")
    for x, y, w, h in blur:  # личное — сильное размытие, текст не восстановить
        reg = img.crop((x - 4, y - 4, x + w + 4, y + h + 4))
        img.paste(reg.filter(ImageFilter.GaussianBlur(9)), (x - 4, y - 4))
    k = min(CARD_W / img.width, CARD_H / img.height)  # высокая картинка (длинный промпт) — по высоте зоны
    cx = CENTER[0]
    if CENTER[1] + img.height * k * 1.04 / 2 > ICONS_FROM:  # низ карточки доходит до иконок справа (лайк, комменты)
        right = W - ICONS                                    # правый край — не дальше 960
        cx = (SAFE[0] + right) / 2                           # центр между левым краем зоны и иконками
        k = min(k, (right - SAFE[0]) / 1.04 / img.width)
    cw, ch = round(img.width * k), round(img.height * k)
    # фон: то же письмо, крупно, сильно размыто и притемнено — в тон, без пустых полей
    cover = H / img.height
    bg = img.resize((round(img.width * cover), H))
    bg = bg.crop(((bg.width - W) // 2, 0, (bg.width - W) // 2 + W, H)).filter(ImageFilter.GaussianBlur(40))
    bg = bg.point(lambda v: int(v * 0.55 + 20))
    mask = Image.new("L", (cw, ch), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, cw, ch), RADIUS, fill=255)
    procs = [subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                               "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-crf", "17", "-pix_fmt", "yuv420p",
                               "-movflags", "+faststart", o], stdin=subprocess.PIPE)
             for o in [out] + ([out.replace(".mp4", "_зона.mp4")] if zone else [])]
    n = round(dur * FPS)
    for f in range(n):
        t = f / FPS
        card = img.copy()
        d = ImageDraw.Draw(card, "RGBA")
        for (x, y, w, h), tm in marks:
            if t >= tm:
                a = min(1, (t - tm) / 0.3)  # маркер проявляется за 0,3 с
                d.rectangle((x - 6, y - 4, x + w + 6, y + h + 4), fill=(255, 214, 0, int(95 * a)))
        z = 1 + 0.04 * (1 - math.cos(math.pi * t / dur)) / 2
        s = k * z
        c = card.resize((round(img.width * s), round(img.height * s)), Image.LANCZOS)
        m = mask.resize(c.size)
        frame = bg.copy()
        x0, y0 = round(cx - c.width / 2), CENTER[1] - c.height // 2
        sh = Image.new("L", (W, H), 0)
        ImageDraw.Draw(sh).rounded_rectangle((x0, y0 + 12, x0 + c.width, y0 + c.height + 12), RADIUS, fill=140)
        frame.paste((0, 0, 0), (0, 0), sh.filter(ImageFilter.GaussianBlur(SHADOW // 2)))
        frame.paste(c, (x0, y0), m)
        procs[0].stdin.write(frame.tobytes())
        if zone:
            procs[1].stdin.write(overlay(frame).tobytes())
    for p in procs:
        p.stdin.close(); p.wait()
    print(f"{dur:.1f} с, карточка {cw}×{ch} → {out}")


if __name__ == "__main__":
    main()
