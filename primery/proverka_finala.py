"""Проверка финала «Извозчики или лошади» (формат «япинг») по ВСЕМ кадрам — сборщик, 2026-10-13.

    python3 primery/proverka_finala.py <папка ролика> [путь к финал.mp4]        (~1,5 минуты)
    Образец под один ролик: для нового — скопировать и поправить K0, K1 (кадры вставки) и CARD_TEXT.

Как считается. Для каждого кадра n ожидаемая яркость строится своими руками, без sborka.py:
    основа B = кадр вставки n − K0 на кадрах K0..K1, иначе кадр итога n;
    слой титров: альфа a = A/255, яркость цвета Ty = 16 + 219·(0,2126R + 0,7152G + 0,0722B)/255 (bt709, tv);
    ожидание E = B·(1 − a) + Ty·a — в каждом пикселе, в том числе в полупрозрачной тени под строкой.
Финал сравнивается с E: PSNR по кадру и отдельно под слоем (a > 0), число пикселей с отличием > 40.
Расчёт E сверен с кадром, который ffmpeg отдаёт кодеку: отличие до 1,7 уровня из 255 (округление).
Сдвиг слоя на один кадр даёт на кадрах смены строки PSNR под слоем 4–15 дБ и тысячи пикселей > 40 (в норме 36–48 дБ и 0–50).
Пиксели > 40 допустимы только у самих букв (кодек на тонких штрихах: под слоем или в 3 px от него) и в тексте карточки
на склейке и плавных сменах подсветки; в стороне от букв их быть не должно.
Ещё: число строк в кадре (заголовок — 2, субтитр — 1, пустых кадров нет), границы фраз слоя против субтитры.txt,
смена строки на склейках, рамки букв против зоны, звук против итога.
"""
import hashlib, json, subprocess, sys
from pathlib import Path
import numpy as np

here = Path(sys.argv[1]).expanduser() if len(sys.argv) > 1 else Path.cwd()
work = here / "монтаж"
final = sys.argv[2] if len(sys.argv) > 2 else str(work / "финал.mp4")
W, H = 1080, 1920
K0, K1 = 1502, 1876            # кадры вставки — их печатает sborka.py («вставка …: кадры 1502–1876»)
CARD_TEXT = (358, 1363)        # строки кадра с текстом карточки (лист оператора)
SAFE = (35, 220, 1045, 1499)   # зона Reels; ниже 1150 справа — колонка иконок, текст до x 960
vst = work / json.loads((work / "сборка.json").read_text())["vstavki"][0]["file"]


def pipe(path, vf, bpp=1):
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", str(path), "-vf", vf, "-f", "rawvideo", "-"],
                         stdout=subprocess.PIPE, bufsize=W * H * bpp * 4)
    def read():
        b = p.stdout.read(W * H * bpp)
        if len(b) < W * H * bpp:
            return None
        a = np.frombuffer(b, np.uint8)
        return a.reshape(H, W, bpp) if bpp > 1 else a.reshape(H, W)
    return read


def psnr(mse):
    return 99.0 if mse == 0 else float(10 * np.log10(255 ** 2 / mse))


def bbox(mask):
    ys, xs = np.where(mask.any(1))[0], np.where(mask.any(0))[0]
    return None if len(ys) == 0 else (int(xs[0]), int(ys[0]), int(xs[-1]), int(ys[-1]))


def lines(mask):
    rows = np.where(mask.any(1))[0]
    return 0 if len(rows) == 0 else int(1 + np.count_nonzero(np.diff(rows) > 8))


def near(mask, r=3):
    out = np.zeros_like(mask)
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            out |= np.roll(np.roll(mask, dy, 0), dx, 1)
    return out


rv = pipe(vst, "extractplanes=y")
V = []
while (f := rv()) is not None:
    V.append(f.copy())
rF, rI, rT = pipe(final, "extractplanes=y"), pipe(work / "итог.mp4", "extractplanes=y"), pipe(work / "титры.mov", "format=rgba", 4)
R, prevI, n = [], None, 0
while True:
    F, I, T = rF(), rI(), rT()
    if F is None or I is None or T is None:
        tail = [x is None for x in (F, I, T)]
        break
    A = T[..., 3]
    ins = K0 <= n <= K1
    B = V[n - K0] if ins else I
    E = B.astype(np.float32)
    r = {"n": n, "ins": ins, "fmean": float(F.mean()), "abox": bbox(A > 0)}
    letters = np.zeros((H, W), bool)
    if r["abox"]:
        x0, y0, x1, y1 = r["abox"]
        s = (slice(y0, y1 + 1), slice(x0, x1 + 1))
        t = T[s].astype(np.float32)
        a = t[..., 3] / 255.0
        ty = 16.0 + 219.0 * (0.2126 * t[..., 0] + 0.7152 * t[..., 1] + 0.0722 * t[..., 2]) / 255.0
        E[s] = E[s] * (1 - a) + ty * a
        letters[s] = (A[s] == 255) & (ty >= 200)
    d = np.abs(F.astype(np.float32) - E)
    lay = A > 0
    big = d > 40
    r["psnr"] = psnr(float(np.mean(d * d)))
    r["psnr_layer"] = psnr(float(np.mean(d[lay] ** 2))) if r["abox"] else None
    r["big"] = int(big.sum())
    far = big & ~lay
    if far.any():                     # редкий случай — тогда считаем, далеко ли от букв
        far &= ~near(lay)
        if ins:
            far[CARD_TEXT[0]:CARD_TEXT[1] + 1] = False
    r["big_far"] = int(far.sum())
    r["lbox"], r["lines"] = bbox(letters), lines(letters)
    nl = int(letters.sum())
    r["letter_ok"] = float(np.count_nonzero(F[letters] >= 190) / nl) if nl else None
    r["sig"] = hashlib.md5(T.tobytes()).hexdigest() if r["abox"] else ""
    r["dI"] = float(np.mean(np.abs(I.astype(np.int16) - prevI))) if prevI is not None else 0.0
    R.append(r)
    prevI = I.astype(np.int16)
    n += 1
N = n
ok_all = []


def check(name, cond, text):
    ok_all.append(bool(cond))
    print(f"{'ДА ' if cond else 'НЕТ'} {name}: {text}")


face, card = [r for r in R if not r["ins"]], [r for r in R if r["ins"]]
check("кадры", N == len(R) and all(tail) and len(V) == K1 - K0 + 1, f"{N} кадров, финал, итог и слой кончились вместе; кадров вставки {len(V)}")
check("чёрных кадров нет", min(r["fmean"] for r in R) > 30, f"средняя яркость кадра {min(r['fmean'] for r in R):.1f}–{max(r['fmean'] for r in R):.1f}")
for name, rows in (("лицо", face), ("вставка", card)):
    w = min(rows, key=lambda r: r["psnr"]); wl = min(rows, key=lambda r: r["psnr_layer"])
    check(f"{name}: финал = ожидание", w["psnr"] >= 40 and wl["psnr_layer"] >= 33,
          f"PSNR по кадру не ниже {w['psnr']:.2f} дБ (кадр {w['n']}), под слоем титров не ниже {wl['psnr_layer']:.2f} дБ (кадр {wl['n']})")
    b = max(rows, key=lambda r: r["big"])
    check(f"{name}: чужого в стороне от букв нет", sum(r["big_far"] for r in rows) == 0,
          f"пиксели > 40 есть в {sum(1 for r in rows if r['big'])} кадрах, не больше {b['big']} в кадре (кадр {b['n']}); в стороне от букв — {sum(r['big_far'] for r in rows)}")
    wo = min(rows, key=lambda r: r["letter_ok"])
    check(f"{name}: буквы слоя белые в финале", wo["letter_ok"] >= 0.99, f"не меньше {wo['letter_ok'] * 100:.2f} % пикселей букв (кадр {wo['n']})")
two = [r["n"] for r in R if r["lines"] == 2]
check("строк в кадре", two == list(range(two[0], two[-1] + 1)) and all(r["lines"] == 1 for r in R[two[-1] + 1:]),
      f"две строки (заголовок) — кадры {two[0]}–{two[-1]}, дальше ровно одна до кадра {N - 1}; пустых {sum(1 for r in R if r['lines'] == 0)}")
segs = []
for r in R:
    if not segs or r["sig"] != segs[-1]["sig"]:
        segs.append({"a": r["n"], "b": r["n"], "sig": r["sig"], "lbox": r["lbox"], "abox": r["abox"]})
    else:
        segs[-1]["b"] = r["n"]
sub = []
for line in (work / "субтитры.txt").read_text().splitlines():
    p = line.replace("–", " ").split(None, 2)
    if len(p) == 3:
        sub.append((round(float(p[0]) * 30), round(float(p[1]) * 30) - 1, p[2].strip()))
check("фразы", len(segs) - 1 == len(sub) and all((s["a"], s["b"]) == u[:2] for s, u in zip(segs[1:], sub)),
      f"заголовок {segs[0]['a']}–{segs[0]['b']}; {len(segs) - 1} фраз слоя стоят на кадрах субтитры.txt ({len(sub)} строк)")
starts = {s["a"] for s in segs}
cuts, prev, bad, cnt = [], None, [], 0
for line in (work / "склейки.txt").read_text().splitlines():
    p = line.split()
    if p and p[0].replace(".", "").isdigit():
        k = round(float(p[0]) * 30)
        if prev is not None and p[-1] != prev and not K0 <= k <= K1:   # склейки под вставкой в кадре не видны
            cnt += 1
            if k not in starts or R[k]["dI"] < max(10, 3 * max(R[k - 1]["dI"], R[k + 1]["dI"])):
                bad.append(k)
        prev = p[-1]
check("склейки со сменой крупности", not bad, f"{cnt} склеек: строка меняется в кадре склейки, скачок плана в итоге — в том же кадре; не так: {bad}")
lb = [s["lbox"] for s in segs]
check("зона", all(b[0] >= SAFE[0] and b[2] <= 960 and b[1] >= SAFE[1] and b[3] <= SAFE[3] for b in lb),
      f"буквы x {min(b[0] for b in lb)}–{max(b[2] for b in lb)}, y {min(b[1] for b in lb)}–{max(b[3] for b in lb)}")
bg = int(np.median(V[0][:200]))
cb = bbox(V[0].astype(np.int16) > bg + 3)
cs = [s for s in segs if K0 <= s["a"] <= K1]
top, bot, right = min(s["abox"][1] for s in cs), max(s["abox"][3] for s in cs), max(s["abox"][2] for s in cs)
check("строка под карточкой", top - cb[3] - 1 >= 12 and bot <= SAFE[3] and right <= 960,
      f"{len(cs)} фраз; карточка y {cb[1]}–{cb[3]}, строка y {top}–{bot}: до карточки {top - cb[3] - 1} px, до низа зоны {SAFE[3] - bot} px, правый край {right}")


def amd5(p):
    return hashlib.md5(subprocess.run(["ffmpeg", "-v", "error", "-i", str(p), "-map", "0:a", "-f", "s16le", "-"], capture_output=True).stdout).hexdigest()


a, b = amd5(work / "итог.mp4"), amd5(final)
check("звук", a == b, f"md5 декодированного звука итога {a[:12]}…, финала {b[:12]}…")
print("\nИТОГ:", "всё сходится" if all(ok_all) else f"не сходится пунктов: {ok_all.count(False)}")
sys.exit(0 if all(ok_all) else 1)
