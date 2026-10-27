"""Сборка ролика по монтажному листу: вставки на весь экран и надписи поверх итог.mp4, звук — из итог.mp4.

    python3 tools/sborka.py <папка ролика> [--zona]

Вход: <папка>/монтаж/итог.mp4 и <папка>/монтаж/сборка.json:
{
  "vstavki": [{"file": "вставки/письмо_1.mp4", "from": 2.6, "to": 5.6}, ...],   // пути от монтаж/
  "nadpisi": [{"text": "314 300 ₽ из 1 000 000", "sub": "осталось 18 дней", "from": 45.2, "to": 50.9, "band": "title"}, ...]
}
band: "title" — полоса заголовка (220–700 по высоте), "sub" — полоса субтитров (1150–1450). Всё внутри безопасной зоны.
"crf": 12 — необязательно, качество кодирования финала (по умолчанию 18). Для итога, собранного с crf 12 (подкаст, раскладка
«квадрат»): на 18 мелкая деталь лица сглаживается — глазом почти не видно, по замеру дисперсия лапласиана 76–90 % от итога,
на 12 — 88–98 % (Визионеры, 2026-10-12).
"obrez": true — необязательно: в финал_зона.mp4 поверх зоны Reels рисуются линии обреза кадра — сетка профиля 3:4 (y 240 и 1680,
жёлтые) и лента 4:5 (y 285 и 1635, голубые): заголовок и субтитры должны быть видны и там (обложка, показ в ленте).
Частота кадров и сетка времени финала — как у итог.mp4 (25 или 30): слой титров и надписи кладутся на его кадры,
вставки приводятся к частоте итога.
Границы вставок и надписей считаются в КАДРАХ итога, а не в секундах (2026-10-13, «Извозчики или лошади»): from/to из
сборка.json переводятся в первый и последний кадр (см. kadry() ниже), вставка включается по номеру кадра — between(n,…).
Время склейки в склейки.txt округлено до 0,01 с и у трети склеек на 3 мс позже своего кадра (50.07 при кадре 1502 =
50,0667 с): условие between(t,50.07,…) такой кадр пропускало — перед вставкой на один кадр оставалось лицо в новой
крупности, а вставка, кончавшаяся на такой склейке, залезала на первый кадр следующего плана.
Проверять стыки — по номеру кадра (select='eq(n,N)'), не через -ss.
Выход: <папка>/монтаж/финал.mp4 (+ финал_зона.mp4 с наложенной зоной для проверки).
Вставка обрезается/растягивается до своего отрезка: если файл короче — держится последний кадр.
"""
import json, math, subprocess, sys, tempfile
from fractions import Fraction
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).parent / "ekran"))
from zona import W, H, SAFE, TOP, BOTTOM, SIDE, ICONS, ICONS_FROM, CENTER

FONT = "/System/Library/Fonts/HelveticaNeue.ttc"
BANDS = {"title": (220, 700), "sub": (1150, 1450)}
MAX_TEXT_W = 900
SNAP = 0.4  # граница вставки/надписи ближе 0,4 с к склейке — ставится ровно на склейку
GRID_34, FEED_45 = (240, 1680), (285, 1635)  # что видно по высоте в сетке профиля 3:4 и в ленте 4:5 (безопасная_зона.md)


def font(size, bold=True):
    return ImageFont.truetype(FONT, size, index=1 if bold else 0)  # в HelveticaNeue.ttc индекс 1 — Bold


def plate(text, sub, band, out: Path):
    """PNG 1080×1920 с плашкой: чёрная скруглённая подложка, белый жирный текст, по центру полосы."""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    size = 76
    while size > 36 and d.textlength(text, font=font(size)) > MAX_TEXT_W - 80:
        size -= 2
    f1, f2 = font(size), font(round(size * 0.55), bold=False)
    w1 = d.textlength(text, font=f1)
    w2 = d.textlength(sub, font=f2) if sub else 0
    h1 = size * 1.15
    h2 = size * 0.55 * 1.3 if sub else 0
    bw, bh = max(w1, w2) + 80, h1 + h2 + 50
    y0, y1 = BANDS[band]
    cy = (y0 + y1) / 2
    x = (W - bw) / 2
    y = cy - bh / 2
    d.rounded_rectangle((x, y, x + bw, y + bh), radius=28, fill=(0, 0, 0, 215))
    d.text((W / 2, y + 25 + h1 / 2), text, font=f1, fill="white", anchor="mm")
    if sub:
        d.text((W / 2, y + 25 + h1 + h2 / 2), sub, font=f2, fill=(255, 255, 255, 220), anchor="mm")
    assert x >= SAFE[0] and x + bw <= SAFE[2] and y >= SAFE[1] and y + bh <= SAFE[3], f"надпись вне зоны: {text}"
    img.save(out)


def overlay_rgba(img, obrez=False):
    """Прозрачная картинка: красным — то, что закрывает Instagram, крестик — центр внимания.
    obrez — ещё и линии обреза кадра в сетке профиля 3:4 и в ленте 4:5 (подпись — над верхней линией)."""
    d = ImageDraw.Draw(img)
    red = (255, 40, 40, 90)
    for r in [(0, 0, W, TOP), (0, H - BOTTOM, W, H), (0, TOP, SIDE, H - BOTTOM), (W - SIDE, TOP, W, ICONS_FROM),
              (W - ICONS, ICONS_FROM, W, H - BOTTOM)]:
        d.rectangle(r, fill=red)
    cx, cy = CENTER
    d.line((cx - 30, cy, cx + 30, cy), fill=(255, 0, 0, 255), width=4)
    d.line((cx, cy - 30, cx, cy + 30), fill=(255, 0, 0, 255), width=4)
    if obrez:
        f = font(24, bold=False)
        for (top, bot), col, name in ((GRID_34, (255, 220, 0, 255), "сетка 3:4"), (FEED_45, (0, 220, 255, 255), "лента 4:5")):
            d.line((0, top - 1, W, top - 1), fill=col, width=2)   # линия — на последних строках, которых уже не видно
            d.line((0, bot + 1, W, bot + 1), fill=col, width=2)
            d.text((W - 44, top - 6), name, font=f, fill=col, anchor="rd")
            d.text((W - 44, bot + 6), name, font=f, fill=col, anchor="ra")
    return img


def main():
    folder = Path(sys.argv[1]).expanduser()
    work = folder / "монтаж"
    plan = json.loads((work / "сборка.json").read_text())
    # настоящие склейки итог.mp4 (склейки.txt от montazh.py) — к ним притягиваем границы вставок и надписей,
    # иначе на стыке мелькает лицо в старой крупности (зритель, 2026-09-28)
    cuts = []
    sk = work / "склейки.txt"
    if sk.exists():
        for line in sk.read_text().splitlines():
            p = line.split()
            if p and p[0].replace(".", "").isdigit():
                cuts.append(float(p[0]))
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                                str(work / "итог.mp4")], capture_output=True, text=True).stdout)
    cuts.append(dur)
    # сетка кадров итога: частота и число кадров видео (dur выше — длина файла, звук бывает на 1–3 кадра длиннее)
    pr = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                         "stream=r_frame_rate,nb_frames", "-of", "default=nw=1:nk=0", str(work / "итог.mp4")],
                        capture_output=True, text=True).stdout
    info = dict(line.split("=", 1) for line in pr.split())
    fps = Fraction(info["r_frame_rate"])
    total = int(info["nb_frames"]) if info.get("nb_frames", "").isdigit() else round(dur * fps)

    def snap(t):
        c = min(cuts, key=lambda c: abs(c - t)) if cuts else t
        return c if abs(c - t) <= SNAP else t

    def kadry(a, b):
        """Отрезок [a, b] в секундах (уже притянутый к склейкам) → первый и последний кадр итога, оба включительно.
        Граница на склейке — это кадр склейки round(t·fps): с него начинается следующий план, поэтому вставка
        «от склейки» начинается с него, а вставка «до склейки» кончается кадром раньше; конец ролика — последний кадр.
        Граница не на склейке — как было: все кадры, чьё время лежит внутри [a, b]."""
        k0 = round(a * fps) if a in cuts else math.ceil(a * fps - 1e-6)
        if b == dur:
            k1 = total - 1
        elif b in cuts:
            k1 = round(b * fps) - 1
        else:
            k1 = math.floor(b * fps + 1e-6)
        return max(k0, 0), min(k1, total - 1)

    items = plan.get("vstavki", []) + plan.get("nadpisi", [])
    for it in items:
        it["from"], it["to"] = snap(it["from"]), snap(it["to"])
    vs = sorted(plan.get("vstavki", []), key=lambda v: v["from"])
    for a, b in zip(vs, vs[1:]):  # соседние вставки смыкаются без щели
        if 0 < b["from"] - a["to"] < 0.3:
            a["to"] = b["from"]
    for it in items:
        it["k0"], it["k1"] = kadry(it["from"], it["to"])
    for a, b in zip(vs, vs[1:]):  # сомкнутые вставки не делят один кадр: кадр стыка — за следующей вставкой
        if a["to"] == b["from"] and a["k1"] >= b["k0"]:
            a["k1"] = b["k0"] - 1
    tmp = Path(tempfile.mkdtemp(prefix="sborka_"))
    inputs = ["-i", str(work / "итог.mp4")]
    chain, last = [], "[0:v]"
    k = 1
    for v in plan.get("vstavki", []):
        f, k0, k1 = work / v["file"], v["k0"], v["k1"]
        if not f.exists():
            print("НЕТ ВСТАВКИ — пропускаю:", f); continue
        inputs += ["-i", str(f)]
        print(f"вставка {v['file']}: кадры {k0}–{k1} ({k1 - k0 + 1} шт., {float(k0 / fps):.3f}–{float((k1 + 1) / fps):.3f} с)")
        # нулевой кадр вставки встаёт на кадр k0 итога, включается она по номеру кадра; короче отрезка — держим последний кадр
        chain.append(f"[{k}:v]setpts=PTS-STARTPTS+{k0}/({fps})/TB,tpad=stop_mode=clone:stop_duration={float((k1 - k0 + 1) / fps)},"
                     f"fps={fps},scale={W}:{H},setsar=1[i{k}];"
                     f"{last}[i{k}]overlay=enable='between(n,{k0},{k1})':eof_action=pass[v{k}];")
        last = f"[v{k}]"; k += 1
    for i, t in enumerate(plan.get("nadpisi", [])):
        png = tmp / f"n{i}.png"
        plate(t["text"], t.get("sub"), t.get("band", "title"), png)
        inputs += ["-loop", "1", "-i", str(png)]
        print(f"надпись «{t['text']}»: кадры {t['k0']}–{t['k1']}")
        chain.append(f"{last}[{k}:v]overlay=enable='between(n,{t['k0']},{t['k1']})':shortest=1[v{k}];")
        last = f"[v{k}]"; k += 1
    titry = work / "титры.mov"  # слой субтитров и заголовков от tools/titry.py — поверх всего
    if titry.exists():
        inputs += ["-i", str(titry)]
        chain.append(f"{last}[{k}:v]overlay=eof_action=pass[v{k}];")
        last = f"[v{k}]"; k += 1
    fc = "".join(chain) + f"{last}format=yuv420p[vout]"
    out = work / "финал.mp4"
    crf = str(plan.get("crf", 18))  # итог с crf 12 (подкаст) на 18 теряет мелкую деталь лица — в сборка.json "crf": 12
    subprocess.run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", fc, "-map", "[vout]", "-map", "0:a",
                    "-c:v", "libx264", "-crf", crf, "-preset", "medium", "-c:a", "copy", "-movflags", "+faststart",
                    str(out)], check=True)
    if "--zona" in sys.argv:  # копия с безопасной зоной поверх — для проверки глазами
        z = tmp / "zona.png"
        base = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        overlay_rgba(base, plan.get("obrez", False)).save(z)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(out), "-i", str(z), "-filter_complex",
                        "[0:v][1:v]overlay,format=yuv420p", "-c:a", "copy", str(work / "финал_зона.mp4")], check=True)
    print("→", out)


if __name__ == "__main__":
    main()
