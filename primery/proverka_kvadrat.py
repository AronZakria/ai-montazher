"""Проверка финал.mp4 раскладки «квадрат» против итог.mp4 и титры.mov — все кадры, не выборка (сборщик, 2026-10-12).

    python3 primery/proverka_kvadrat.py <папка ролика> [папка для листов кадров]

Рамка видео — из plan.json монтажа ("video_y", "video_h"): раскладка «б» — 416…1376; без этих строк — первый квадрат 330…1410.
Что проверяет:
- частота, число кадров, длина, сетка времени (pts) — как у итога; кадр финала i = кадр итога i (не i−1 и не i+1);
- слой титров: альфа только на чёрных полях (заголовок — выше видео и, в раскладке «б», ниже линии ленты 4:5 y 285;
  субтитры — между видео и низом зоны 1500), на видео — ничего, в безопасной зоне (x 35…1045, под субтитры x ≤ 960);
  под надписями в итоге чёрное; заголовок один на все кадры; заголовок и субтитры видны в ленте 4:5 и в сетке 3:4;
- смены субтитра в слое = границы субтитры.txt; в финале субтитр на каждом кадре тот же, что в слое на этом кадре
  (на кадре смены — проба «свой кадр слоя против соседнего»);
- видео в рамке финала = итог (разница — шум кодека), резкость (дисперсия лапласиана) по всем кадрам, чёрных кадров нет;
- резкость лица (рамка лица — tools/face) на среднем кадре каждого куска между склейками, финал к итогу;
- текст на кадре (OCR середины каждой фразы и кадров до/после каждой склейки) = субтитры.txt;
- звук: md5 пакетов, громкость и true peak.
Листы кадров — из финал_зона.mp4: первый, последний, пары «до склейки / после склейки».
"""
import json, re, subprocess, sys, tempfile
from fractions import Fraction
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1920
SAFE = (35, 220, 1045, 1500)
ICON_X = 960
FEED, GRID = (285, 1635), (240, 1680)   # что видно по высоте в ленте 4:5 и в сетке профиля 3:4
VID, TITLE, SUB = (330, 1410), (220, 330), (1410, 1500)   # первый квадрат; main() берёт рамку видео из plan.json
ROOT = Path(__file__).resolve().parents[1]  # корень репозитория
bad = []


def note(ok, text):
    print(("  ok  " if ok else "  ОШИБКА  ") + text)
    if not ok:
        bad.append(text)


def probe(f, entries, stream="v:0", count=False):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", stream, *(["-count_frames"] if count else []), "-show_entries", entries,
                        "-of", "json", str(f)], capture_output=True, text=True).stdout
    return json.loads(r)


def pts(f):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "frame=pts", "-of", "csv=p=0",
                        str(f)], capture_output=True, text=True).stdout.split()
    return [int(x.strip(",")) for x in r]


def pipe(f, pix):
    return subprocess.Popen(["ffmpeg", "-v", "error", "-i", str(f), "-map", "0:v:0", "-fps_mode", "passthrough", "-pix_fmt", pix,
                             "-f", "rawvideo", "-"], stdout=subprocess.PIPE, bufsize=W * H * 4)


def read(p, ch):
    b = p.stdout.read(W * H * ch)
    return None if len(b) < W * H * ch else np.frombuffer(b, np.uint8).reshape(H, W, ch)


def luma(a):
    return (a[..., 0].astype(np.float32) * 0.2126 + a[..., 1].astype(np.float32) * 0.7152 + a[..., 2].astype(np.float32) * 0.0722)


def lap_var(g):
    l = -4 * g[1:-1, 1:-1] + g[:-2, 1:-1] + g[2:, 1:-1] + g[1:-1, :-2] + g[1:-1, 2:]
    return float(l.var())


LOOK = str.maketrans("abcehkmoptxy", "авсенкмортху")  # Vision читает короткие русские слова латиницей: «но…» → «HO...», «вот» → «BOT»


def norm(t):
    t = t.lower().replace("ё", "е").replace("–", "-").replace("—", "-").translate(LOOK)  # одинаковые на вид буквы — к одному виду, с обеих сторон
    return re.sub(r"[^\w\-]+", " ", t).strip()


def audio(f):
    md5 = subprocess.run(["ffmpeg", "-v", "error", "-i", str(f), "-map", "0:a", "-c", "copy", "-f", "md5", "-"],
                         capture_output=True, text=True).stdout.strip()
    pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", str(f), "-map", "0:a", "-f", "md5", "-"],
                         capture_output=True, text=True).stdout.strip()
    e = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(f), "-map", "0:a", "-af", "ebur128=peak=true", "-f", "null", "-"],
                       capture_output=True, text=True).stderr
    s = e[e.rindex("Summary:"):]
    g = lambda k: float(re.search(k + r":\s+(-?[\d.]+)", s).group(1))
    return md5, pcm, g("I"), g("LRA"), g("Peak")


def main():
    folder = Path(sys.argv[1]).expanduser().resolve()
    work = folder / "монтаж"
    listy = Path(sys.argv[2]) if len(sys.argv) > 2 else None
    itog, final, titry, zona = work / "итог.mp4", work / "финал.mp4", work / "титры.mov", work / "финал_зона.mp4"
    print(f"=== {folder.name}")
    global VID, TITLE, SUB
    plan = json.loads((work / "plan.json").read_text()) if (work / "plan.json").exists() else {}
    lenta = "video_y" in plan                     # раскладка «б»: заголовок обязан быть виден в ленте 4:5
    vy, vh = plan.get("video_y", VID[0]), plan.get("video_h", VID[1] - VID[0])
    VID, TITLE, SUB = (vy, vy + vh), (FEED[0] if lenta else SAFE[1], vy), (vy + vh, SAFE[3])
    print(f"  рамка видео y {VID[0]}…{VID[1]} ({'plan.json' if lenta else 'первый квадрат'}); поле заголовка y {TITLE[0]}…{TITLE[1]}, поле субтитров y {SUB[0]}…{SUB[1]}")

    # 1. частота, кадры, длина, сетка времени
    info = {}
    for f in (itog, final, titry, zona):
        s = probe(f, "stream=r_frame_rate,avg_frame_rate,nb_read_frames,duration,time_base,pix_fmt,color_space,color_range:format=duration", count=True)
        st = s["streams"][0]
        info[f.name] = (st["r_frame_rate"], st["avg_frame_rate"], int(st["nb_read_frames"]), float(st["duration"]), float(s["format"]["duration"]))
        print(f"  {f.name}: {st['r_frame_rate']} кадр/с (средняя {st['avg_frame_rate']}), кадров {st['nb_read_frames']}, "
              f"видео {float(st['duration']):.3f} с, файл {float(s['format']['duration']):.3f} с, {st['pix_fmt']} {st.get('color_space', '')} {st.get('color_range', '')}")
    fps = Fraction(info["итог.mp4"][0])
    N = info["итог.mp4"][2]
    note(fps == 25, f"частота итога {fps} = 25")
    for f in ("финал.mp4", "титры.mov", "финал_зона.mp4"):
        note(info[f][:4] == info["итог.mp4"][:4], f"{f}: частота, число кадров ({info[f][2]}) и длина видео ({info[f][3]:.3f} с) — как у итога")
    note(abs(info["финал.mp4"][4] - info["итог.mp4"][4]) < 1e-6, f"длина файла финала {info['финал.mp4'][4]:.3f} с = итогу {info['итог.mp4'][4]:.3f} с")
    tb = Fraction(probe(itog, "stream=time_base")["streams"][0]["time_base"]); tbf = Fraction(probe(final, "stream=time_base")["streams"][0]["time_base"])
    pi, pf, pt = pts(itog), pts(final), pts(titry)
    tbt = Fraction(probe(titry, "stream=time_base")["streams"][0]["time_base"])
    step = lambda p, t: {Fraction(b - a) * t for a, b in zip(p, p[1:])}
    note(step(pi, tb) == {1 / fps} and step(pf, tbf) == {1 / fps} and step(pt, tbt) == {1 / fps} and pi[0] == pf[0] == pt[0] == 0,
         f"время кадров: у итога, слоя и финала шаг ровно 1/{fps} с с нуля — ни дублей, ни пропусков")
    note([Fraction(x) * tb for x in pi] == [Fraction(x) * tbf for x in pf], "время каждого кадра финала = времени кадра итога")

    # субтитры.txt и склейки.txt
    subs = []
    for line in (work / "субтитры.txt").read_text().splitlines():
        m = re.match(r"\s*(\d+\.\d+)–\s*(\d+\.\d+)\s+(.*\S)\s*$", line)
        if m:
            subs.append((float(m.group(1)), float(m.group(2)), m.group(3)))
    cuts = []
    for line in (work / "склейки.txt").read_text().splitlines():
        m = re.match(r"\s*(\d+\.\d+)\s+кусок\s+\d+.*крупность\s+([\d.]+)", line)
        if m and float(m.group(1)) > 0:
            cuts.append((float(m.group(1)), float(m.group(2))))
    fr = lambda t: int(round(t * fps))
    bounds = [0] + [fr(t) for t, _ in cuts] + [N]
    face_k = sorted({(a + b) // 2 for a, b in zip(bounds, bounds[1:])})   # средний кадр каждого куска — для резкости лица
    face_buf = {}
    tmp = Path(tempfile.mkdtemp(prefix="proverka_"))
    want = {}                                    # кадр → текст (None — пусто)
    for s, e, t in subs:
        for k in range(fr(s), fr(e)):
            want[k] = t

    # 2. все кадры: слой, итог, финал
    pT, pI, pF = pipe(titry, "rgba"), pipe(itog, "rgb24"), pipe(final, "rgb24")
    prev_F = prev_Il = prev_Ta = prev_Tl = None
    title0 = None
    changes, sub_state = [], []                  # кадры смены субтитра в слое; (пусто/нет, ширина, высота) по кадрам
    amin = [W, H, 0, 0]
    d_vid, d_title, d_sub, d_rest, lapI, lapF, vid_mean = [], [], [], [], [], [], []
    align_ok, align_tie, align_err, cross = 0, 0, [], []

    def align(k, pfs):  # кадр финала k против кадров итога k−1, k, k+1
        nonlocal align_ok, align_tie
        dd = [float(np.abs(pfs - Ismall[j]).mean()) if 0 <= j < len(Ismall) and Ismall[j] is not None else 1e9 for j in (k - 1, k, k + 1)]
        best = min(dd[0], dd[2])
        if abs(best - dd[1]) < 0.02:      # соседние кадры итога почти одинаковы — не различить
            align_tie += 1
        elif dd[1] < best:
            align_ok += 1
        else:
            align_err.append(k)
    viol = {"на видео": [], "вне полей заголовка и субтитров": [], "заголовок изменился": []}   # кадры, где слой титров не на месте
    black = [0.0, 0.0]                           # самое светлое в итоге под заголовком и под субтитрами (должно быть чёрное)
    edge = [0.0, 255.0, 255.0, 0.0]              # строки у краёв рамки: над видео (макс.), первая и последняя строка видео (мин. средней), под видео (макс.)
    jump = []                                    # скачок картинки итога между соседними кадрами
    pend = None                                  # (кадр, F_small) — ждёт итог i+1
    Ismall = []
    n = 0
    y0, y1 = VID
    while True:
        T, I, F = read(pT, 4), read(pI, 3), read(pF, 3)
        if T is None or I is None or F is None:
            note(T is None and I is None and F is None, f"все три потока кончились вместе на кадре {n}")
            break
        a = T[..., 3]
        rows = np.nonzero(a.any(axis=1))[0]; cols = np.nonzero(a.any(axis=0))[0]
        if len(rows):
            amin = [min(amin[0], cols[0]), min(amin[1], rows[0]), max(amin[2], cols[-1]), max(amin[3], rows[-1])]
        if a[y0:y1].any():
            viol["на видео"].append(n)
        out = a.copy(); out[TITLE[0]:TITLE[1]] = 0; out[SUB[0]:SUB[1]] = 0
        if out.any():
            viol["вне полей заголовка и субтитров"].append(n)
        ta = a[TITLE[0]:TITLE[1]]
        if title0 is None:
            title0 = T[TITLE[0]:TITLE[1]].copy()
            r_, c_ = np.nonzero(ta.any(axis=1))[0], np.nonzero(ta.any(axis=0))[0]
            print(f"  заголовок в слое: x {c_[0]}…{c_[-1]}, y {TITLE[0] + r_[0]}…{TITLE[0] + r_[-1]}")
        elif not np.array_equal(title0, T[TITLE[0]:TITLE[1]]):
            viol["заголовок изменился"].append(n)
        sa = a[SUB[0]:SUB[1]]
        if prev_Ta is None or not np.array_equal(sa, prev_Ta):
            if n > 0 or sa.any():
                changes.append(n)
        if sa.any():
            r_, c_ = np.nonzero(sa.any(axis=1))[0], np.nonzero(sa.any(axis=0))[0]
            sub_state.append((True, c_[0], c_[-1], SUB[0] + r_[0], SUB[0] + r_[-1]))
        else:
            sub_state.append((False, 0, 0, 0, 0))
        # финал против «итог + слой», посчитанного здесь же (независимо от overlay в ffmpeg)
        lf, li = luma(F), luma(I)
        al = a.astype(np.float32) / 255
        tl = luma(T)
        ref = li * (1 - al) + tl * al
        d = np.abs(lf - ref)
        d_vid.append(float(d[y0:y1].mean())); d_title.append(float(d[TITLE[0]:TITLE[1]].mean())); d_sub.append(float(d[SUB[0]:SUB[1]].mean()))
        d_rest.append(float(max(d[:TITLE[0]].max(), d[SUB[1]:].max())))
        vid_mean.append(float(lf[y0:y1].mean()))
        tr = np.nonzero(ta.any(axis=1))[0]
        if len(tr):
            black[0] = max(black[0], float(li[TITLE[0] + tr[0]:TITLE[0] + tr[-1] + 1].max()))
        if sa.any():
            sr = np.nonzero(sa.any(axis=1))[0]
            black[1] = max(black[1], float(li[SUB[0] + sr[0]:SUB[0] + sr[-1] + 1].max()))
        edge = [max(edge[0], float(li[y0 - 2:y0].max())), min(edge[1], float(li[y0].mean())),
                min(edge[2], float(li[y1 - 1].mean())), max(edge[3], float(li[y1:y1 + 2].max()))]
        if n in face_k:
            Image.fromarray(I).save(tmp / f"f{n:05d}.png")
            face_buf[n] = (li.copy(), lf.copy())
        lapI.append(lap_var(li[y0:y1])); lapF.append(lap_var(lf[y0:y1]))
        # смена субтитра: кадр финала ближе к своему кадру слоя, чем к прошлому
        if prev_Ta is not None and not np.array_equal(sa, prev_Ta):
            sl = slice(SUB[0], SUB[1])
            own = float(np.abs(lf[sl] - (li[sl] * (1 - al[sl]) + tl[sl] * al[sl])).mean())
            pa = prev_Ta.astype(np.float32) / 255
            oth = float(np.abs(lf[sl] - (li[sl] * (1 - pa) + prev_Tl * pa)).mean())
            own_p = float(np.abs(prev_F - (prev_Il * (1 - pa) + prev_Tl * pa)).mean())
            oth_p = float(np.abs(prev_F - (prev_Il * (1 - al[sl]) + tl[sl] * al[sl])).mean())
            cross.append((n, own, oth, own_p, oth_p))
        # кадр в кадр: финал i против итога i−1, i, i+1 (в рамке видео, каждый 4-й пиксель)
        fs, is_ = lf[y0:y1:4, ::4], li[y0:y1:4, ::4]
        Ismall.append(is_)
        if len(Ismall) > 1:
            jump.append(float(np.abs(is_ - Ismall[-2]).mean()))
        if pend is not None:
            align(*pend)
            if len(Ismall) > 3:
                Ismall[-4] = None
        pend = (n, fs)
        prev_Ta, prev_Tl = sa.copy(), tl[SUB[0]:SUB[1]].copy()
        prev_F, prev_Il = lf[SUB[0]:SUB[1]].copy(), li[SUB[0]:SUB[1]].copy()
        n += 1
    if pend is not None:
        align(*pend)
    for p in (pT, pI, pF):
        p.stdout.close(); p.wait()
    note(n == N, f"прочитано кадров {n} = {N}")

    # 3. слой титров
    note(not any(viol.values()), f"слой титров во всех {N} кадрах: на видео y {VID[0]}…{VID[1]} пусто, вне полей заголовка и субтитров пусто, заголовок один и тот же"
         + "".join(f"; {k.upper()}: {len(v)} кадров, первый {v[0]}" for k, v in viol.items() if v))
    note(amin[0] >= SAFE[0] and amin[2] <= SAFE[2] and amin[1] >= SAFE[1] and amin[3] < SAFE[3],
         f"слой титров за весь ролик: x {amin[0]}…{amin[2]}, y {amin[1]}…{amin[3]} — в безопасной зоне (35…1045 × 220…1500), на видео {VID[0]}…{VID[1]} пусто")
    tr = np.nonzero(title0[..., 3].any(axis=1))[0] + TITLE[0]
    note(tr[0] >= (FEED[0] if lenta else SAFE[1]) and tr[-1] < VID[0],
         f"заголовок y {tr[0]}…{tr[-1]}: " + (f"ниже линии ленты 285 на {tr[0] - FEED[0]} px, " if lenta else "") + f"выше видео на {VID[0] - 1 - tr[-1]} px"
         + (f"; в ленте 4:5 (y {FEED[0]}…{FEED[1]}) и в сетке 3:4 (y {GRID[0]}…{GRID[1]}) виден целиком" if tr[0] >= FEED[0]
            else f"; в сетке 3:4 (с y {GRID[0]}) " + ("виден" if tr[0] >= GRID[0] else f"срезано {GRID[0] - tr[0]} px") + f", в ленте 4:5 (с y {FEED[0]}) срезано {FEED[0] - tr[0]} px сверху"))
    note(max(black) < 16, f"под надписями в итоге чёрное: самое светлое под заголовком {black[0]:.0f}, под субтитрами {black[1]:.0f} из 255")
    note(edge[0] < 16 and edge[3] < 16 and edge[1] > 4 and edge[2] > 4,
         f"края рамки видео: над видео (y {VID[0] - 2}…{VID[0] - 1}) до {edge[0]:.0f}, первая строка видео {VID[0]} — от {edge[1]:.0f}, "
         f"последняя {VID[1] - 1} — от {edge[2]:.0f}, под видео (y {VID[1]}…{VID[1] + 1}) до {edge[3]:.0f} из 255")
    on = [s for s in sub_state if s[0]]
    xr, hh, ww = max(s[2] for s in on), max(s[4] - s[3] + 1 for s in on), max(s[2] - s[1] + 1 for s in on)
    sy0, sy1 = min(s[3] for s in on), max(s[4] for s in on)
    note(xr <= ICON_X and ww <= 840 and sy0 >= VID[1] and sy1 < SAFE[3] and sy1 < FEED[1],
         f"субтитры: правый край ≤ {xr} (иконки с 960), самая широкая строка {ww} px (≤ 840), высота до {hh} px (одна строка), "
         f"y {sy0}…{sy1} — под видео (с {VID[1]}), в зоне Reels (до 1500) и в ленте 4:5 (до {FEED[1]})")
    empty = [k for k, s in enumerate(sub_state) if not s[0]]
    # смена = начало каждой фразы + конец фразы, за которой пусто (до следующей фразы или до конца ролика)
    exp_changes = sorted({fr(s) for s, e, t in subs} | {fr(e) for (s, e, t), nx in zip(subs, subs[1:] + [None]) if fr(e) != (fr(nx[0]) if nx else N)})
    note(changes == exp_changes, f"смены субтитра в слое ({len(changes)}) — ровно на кадрах границ субтитры.txt ({len(exp_changes)})"
         + ("" if changes == exp_changes else f": лишние {sorted(set(changes) - set(exp_changes))}, нет {sorted(set(exp_changes) - set(changes))}"))
    exp_empty = [k for k in range(N) if k not in want]
    note(empty == exp_empty, f"кадров без субтитра {len(empty)}" + (f" ({empty[0] / fps:.2f}–{(empty[-1] + 1) / fps:.2f} с)" if empty else "")
         + f" — как в субтитры.txt ({len(exp_empty)})")

    # 4. финал = итог + слой, кадр в кадр
    note(max(d_title) < 1.5 and max(d_sub) < 1.5, f"финал против «итог + слой» на том же кадре: заголовок — разница до {max(d_title):.2f}, "
         f"полоса субтитров — до {max(d_sub):.2f} из 255 (все {N} кадров)")
    worst = min(cross, key=lambda c: min(c[2] / max(c[1], 1e-6), c[4] / max(c[3], 1e-6)))
    note(all(c[1] * 3 < c[2] and c[3] * 3 < c[4] for c in cross),
         f"на всех {len(cross)} сменах субтитра кадр финала совпадает со своим кадром слоя, а не с соседним "
         f"(худшая смена — кадр {worst[0]}: свой {worst[1]:.2f} / чужой {worst[2]:.2f}; кадр до неё: {worst[3]:.2f} / {worst[4]:.2f})")
    note(not align_err and align_ok > 0.9 * N, f"кадр финала i ближе всего к кадру итога i (а не к i−1 или i+1): {align_ok} кадров из {N}"
         f" (ещё {align_tie} — соседние кадры итога одинаковы, не различить)" + (f"; НЕ СВОЙ КАДР: {align_err[:20]}" if align_err else ""))
    note(max(d_vid) < 1.5, f"видео в рамке: разница с итогом в среднем {np.mean(d_vid):.2f}, худший кадр {max(d_vid):.2f} из 255 (шум кодека)")
    note(max(d_rest) < 12, f"чёрные поля выше заголовка и ниже субтитров: отклонение от итога до {max(d_rest):.0f} из 255")
    ratio = np.array(lapF) / np.array(lapI) * 100
    note(ratio.min() > 85, f"резкость рамки видео (дисперсия лапласиана), финал к итогу: в среднем {ratio.mean():.1f} %, худший кадр {ratio.min():.1f} % "
         f"(кадр {int(ratio.argmin())})")
    note(min(vid_mean) > 20, f"чёрных кадров нет: средняя яркость рамки {min(vid_mean):.0f}…{max(vid_mean):.0f}")
    # резкость лица: рамка лица по кадру итога (tools/face), средний кадр каждого куска
    face = ROOT / "tools" / "face"
    if face.exists():
        r = subprocess.run([str(face), *[str(tmp / f"f{k:05d}.png") for k in sorted(face_buf)]], capture_output=True, text=True).stdout
        fr_ = []
        for line in r.splitlines():
            path, cx, cy, w, h = line.rsplit(maxsplit=4)
            k = int(Path(path).stem[1:]); cx, cy, w, h = float(cx), float(cy), float(w), float(h)
            x0, x1, fy0, fy1 = int((cx - w / 2) * W), int((cx + w / 2) * W), int((cy - h / 2) * H), int((cy + h / 2) * H)
            li, lf = face_buf[k]
            fr_.append((k, lap_var(lf[fy0:fy1, x0:x1]) / lap_var(li[fy0:fy1, x0:x1]) * 100, float(np.abs(lf[fy0:fy1, x0:x1] - li[fy0:fy1, x0:x1]).mean()), fy0, fy1))
        if fr_:
            lo = min(fr_, key=lambda x: x[1])
            note(len(fr_) == len(face_buf) and np.mean([x[1] for x in fr_]) > 90 and lo[1] > 70,
                 f"резкость лица (дисперсия лапласиана в рамке лица), финал к итогу, {len(fr_)} кадров из {len(face_buf)} (середина каждого куска): "
                 + ", ".join(f"{x[1]:.0f}" for x in fr_) + f" % — в среднем {np.mean([x[1] for x in fr_]):.1f} %, худший {lo[1]:.1f} % (кадр {lo[0]}); "
                 f"разница яркости в лице до {max(x[2] for x in fr_):.2f} из 255; лицо y {min(x[3] for x in fr_)}…{max(x[4] for x in fr_)}")
        else:
            note(False, "резкость лица: tools/face не нашёл лица ни на одном кадре")
    else:
        print("  НЕ ПРОВЕРЕНО: резкость лица — нет tools/face (собрать: swiftc tools/face.swift -o tools/face)")
    face_buf.clear()

    # 5. склейки
    med = float(np.median(jump))
    for t, z in cuts:
        c = fr(t)
        j = jump[c - 1]
        near = [x for x in changes if x != c and abs(x - c) <= 3]
        note(j > 5 * med and (c in changes or not near), f"склейка {t:5.2f} с (кадр {c}, крупность {z}): картинка итога меняется на этом кадре "
             f"(скачок {j:.1f} при обычном {med:.2f}); субтитр " + ("меняется на этом же кадре" if c in changes else "стоит через склейку")
             + (f"; СМЕНА РЯДОМ: кадры {near}" if near else ""))
    extra = [k + 1 for k, j in enumerate(jump) if j > 5 * med and k + 1 not in {fr(t) for t, _ in cuts}]
    note(not extra, "других скачков картинки, кроме склеек, нет" + (f": кадры {extra}" if extra else ""))

    # 6. текст на кадре финала (OCR) против субтитры.txt
    picks = {}
    for s, e, t in subs:
        picks[(fr(s) + fr(e) - 1) // 2] = "середина фразы"
    for t, _ in cuts:
        picks[fr(t) - 1] = f"кадр до склейки {t:.2f}"
        picks[fr(t)] = f"кадр после склейки {t:.2f}"
    picks[0] = "первый кадр"; picks[N - 1] = "последний кадр"
    ks = sorted(picks)
    sel = "+".join(f"eq(n\\,{k})" for k in ks)
    subprocess.run(["ffmpeg", "-v", "error", "-i", str(final), "-vf", f"select='{sel}',crop={W}:{SUB[1] - SUB[0]}:0:{SUB[0]},pad=iw:ih+80:0:40:black,scale=iw*2:ih*2:flags=lanczos",
                    "-fps_mode", "passthrough", str(tmp / "s%04d.png")], check=True)
    subprocess.run(["ffmpeg", "-v", "error", "-i", str(final), "-vf", f"select='eq(n\\,0)+eq(n\\,{N - 1})',crop={W}:{TITLE[1] - TITLE[0]}:0:{TITLE[0]},pad=iw:ih+80:0:40:black,scale=iw*2:ih*2:flags=lanczos",
                    "-fps_mode", "passthrough", str(tmp / "t%04d.png")], check=True)
    files = [str(tmp / f"s{i + 1:04d}.png") for i in range(len(ks))] + [str(tmp / "t0001.png"), str(tmp / "t0002.png")]
    ocr = json.loads(subprocess.run(["swift", str(ROOT / "tools" / "ocr.swift"), *files], capture_output=True, text=True).stdout)
    miss = []
    for k, f in zip(ks, files):
        got, exp = norm(ocr.get(f, "")), norm(want.get(k) or "")
        if got != exp:
            miss.append((k, picks[k], want.get(k), ocr.get(f, "")))
    note(not miss, f"текст субтитра на кадре финала (OCR, {len(ks)} кадров: середина каждой из {len(subs)} фраз, кадры до и после каждой из {len(cuts)} склеек, "
         f"первый и последний) = субтитры.txt" + ("" if not miss else f" — расхождений {len(miss)}"))
    for k, why, exp, got in miss:
        print(f"      кадр {k} ({k / fps:.2f} с, {why}): в файле «{exp}», на кадре «{got}»")
    zag = " ".join(json.loads((work / "титры.json").read_text())["zagolovok"]["stroki"])
    for f, name in ((files[-2], "первом"), (files[-1], "последнем")):
        got = " ".join(ocr.get(f, "").split())
        note(norm(got) == norm(zag), f"заголовок на {name} кадре финала (OCR): «{got}»")

    # 7. звук
    ai, af = audio(itog), audio(final)
    note(ai[0] == af[0], f"звук: md5 пакетов финала = итогу ({af[0]})")
    note(ai[1] == af[1], f"звук: md5 декодированного звука финала = итогу")
    note(ai[2:] == af[2:], f"громкость: итог {ai[2]} LUFS, LRA {ai[3]}, true peak {ai[4]} dBTP · финал {af[2]} LUFS, LRA {af[3]}, true peak {af[4]} dBTP")
    na = probe(final, "stream=codec_name", "a")["streams"]
    note(len(na) == 1, f"звуковых дорожек в финале: {len(na)} ({na[0]['codec_name']}) — музыки и эффектов нет")

    # 8. листы кадров из финал_зона.mp4
    if listy:
        listy.mkdir(parents=True, exist_ok=True)
        tiles = [(0, "первый кадр")]
        for t, z in cuts:
            tiles += [(fr(t) - 1, f"до склейки {t:.2f}"), (fr(t), f"после {t:.2f} · ×{z}")]
        tiles.append((N - 1, "последний кадр"))
        sel = "+".join(f"eq(n\\,{k})" for k, _ in tiles)
        subprocess.run(["ffmpeg", "-v", "error", "-i", str(zona), "-vf", f"select='{sel}',scale=432:768:flags=lanczos", "-fps_mode", "passthrough",
                        str(tmp / "z%04d.png")], check=True)
        font = ImageFont.truetype("/System/Library/Fonts/HelveticaNeue.ttc", 22)
        per = 8
        for s in range(0, len(tiles), per):
            part = tiles[s:s + per]
            sheet = Image.new("RGB", (432 * 4, 800 * ((len(part) + 3) // 4)), (40, 40, 40))
            for j, (k, label) in enumerate(part):
                im = Image.open(tmp / f"z{s + j + 1:04d}.png")
                x, y = (j % 4) * 432, (j // 4) * 800
                sheet.paste(im, (x, y + 32))
                ImageDraw.Draw(sheet).text((x + 6, y + 4), f"{k / fps:.2f} с · к. {k} · {label}", font=font, fill=(255, 230, 0))
            out = listy / f"{folder.name[:2]}_лист_{s // per + 1}.png"
            sheet.save(out)
            print("  лист кадров:", out)
    print("  ИТОГ:", "всё сошлось" if not bad else f"ОШИБОК {len(bad)}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
