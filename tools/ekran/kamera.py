"""Вставка экрана 9:16: место действия всегда в центре безопасной зоны, камера плавно едет и приближает.

    python3 tools/ekran/kamera.py <папка съёмки> [--zona]

Вход: <папка>/кадры.json и frames/ от ekran.mjs. Выход: <папка>/вставка.mp4 (1080×1920, 30 fps),
с --zona ещё вставка_зона.mp4 — с наложенной безопасной зоной для проверки.
Правила — docs/запись_экрана.md, зона — docs/безопасная_зона.md.
"""
import json, math, subprocess, sys
from pathlib import Path
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from zona import W, H, CENTER, overlay

FPS = 30
MAX_W, MAX_H = 970, 1180  # место действия (с полями) влезает сюда — внутри зоны 35..1045 по ширине, 220..1500 по высоте
MAX_W_ICONS = 850         # если место действия опускается до иконок справа (ниже 1150) — уже, чтобы не залезть под них
PAD = 45                  # поля вокруг места действия, px скриншота с каждой стороны
MIN_BOX = 520             # меньше не приближаем: вокруг маленькой кнопки должен остаться понятный контекст
K_MIN, K_MAX = 0.62, 1.6  # пределы масштаба (1 px скриншота → px кадра); сильнее 1,6 — обрывки слов по краям
MOVE = 0.55               # длительность переезда камеры, с


def target(box, sw, sh):
    """Камера (центр в px скриншота, масштаб) для места действия; None — весь экран телефона."""
    if box is None:
        k = min(W / sw, (H - 220 - 420 + 300) / sh)  # весь экран: по ширине кадра
        return sw / 2, sh / 2, k
    bw = max(box["w"] + 2 * PAD, MIN_BOX)
    bh = max(box["h"] + 2 * PAD, MIN_BOX * 0.6)
    k = max(K_MIN, min(K_MAX, MAX_W / bw, MAX_H / bh))
    if CENTER[1] + bh * k / 2 > 1150:  # низ места действия доходит до иконок справа
        k = max(K_MIN, min(k, MAX_W_ICONS / bw))
    return box["x"] + box["w"] / 2, box["y"] + box["h"] / 2, k


def union(boxes):
    bs = [b for b in boxes if b]
    if not bs:
        return None
    x0 = min(b["x"] for b in bs); y0 = min(b["y"] for b in bs)
    x1 = max(b["x"] + b["w"] for b in bs); y1 = max(b["y"] + b["h"] for b in bs)
    return {"x": x0, "y": y0, "w": x1 - x0, "h": y1 - y0}


def ease(p):
    return (1 - math.cos(math.pi * min(max(p, 0), 1))) / 2


def main(folder: Path, with_zone: bool):
    d = json.loads((folder / "кадры.json").read_text())
    frames = d["frames"]
    first = Image.open(folder / frames[0]["file"]).convert("RGB")
    sw, sh = first.size
    bg = first.getpixel((5, sh // 2))  # цвет фона страницы — им заполняем поля за краем скриншота
    # одна цель камеры на группу (например, весь ввод текста) — камера не дёргается за каждой буквой
    groups = {}
    for f in frames:
        groups.setdefault(f["group"], []).append(f["focus"])
    tgt = {g: target(union(bs), sw, sh) for g, bs in groups.items()}

    outs = [folder / "вставка.mp4"] + ([folder / "вставка_зона.mp4"] if with_zone else [])
    procs = [subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                               "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-crf", "17", "-pix_fmt", "yuv420p",
                               "-movflags", "+faststart", str(o)], stdin=subprocess.PIPE) for o in outs]
    cam = list(tgt[frames[0]["group"]]); start = list(cam); goal = list(cam); t_move = -1
    t = 0.0; cur_group = frames[0]["group"]
    for f in frames:
        img = Image.open(folder / f["file"]).convert("RGB")
        if f["group"] != cur_group:
            cur_group = f["group"]
            if list(tgt[cur_group]) != goal:
                start, goal, t_move = list(cam), list(tgt[cur_group]), t
        for _ in range(max(1, round(f["hold"] * FPS))):
            p = ease((t - t_move) / MOVE) if t_move >= 0 else 1
            cx = start[0] + (goal[0] - start[0]) * p
            cy = start[1] + (goal[1] - start[1]) * p
            k = math.exp(math.log(start[2]) + (math.log(goal[2]) - math.log(start[2])) * p)  # зум — в логарифме, равномерно
            cam = [cx, cy, k]
            ox, oy = CENTER
            fr = img.transform((W, H), Image.AFFINE, (1 / k, 0, cx - ox / k, 0, 1 / k, cy - oy / k),
                               resample=Image.BICUBIC, fillcolor=bg)
            procs[0].stdin.write(fr.tobytes())
            if with_zone:
                procs[1].stdin.write(overlay(fr).tobytes())
            t += 1 / FPS
    for p in procs:
        p.stdin.close(); p.wait()
    print(f"{t:.1f} с → " + ", ".join(map(str, outs)))


if __name__ == "__main__":
    main(Path(sys.argv[1]), "--zona" in sys.argv)
