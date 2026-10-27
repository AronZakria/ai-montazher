#!/usr/bin/env python3
"""Подкаст «Визионеры #38»: короткие ролики из длинной записи (правила — «docs/монтаж.md», раздел
«Подкаст»). Общая сборка для роликов этой записи на функциях montazh.py; сам montazh.py не меняется.
Образец из рабочей папки автора: пробный формат «квадрат», Ароном ещё не утверждён. В plan.json обязателен "file" — исходник.

    .venv/bin/python "primery/kvadrat.py" <папка ролика> [faces|dry|preview|render|slova] [--plan plan_X.json]

faces   — лицо и макушка героя по каждому куску записи из плана, 5 раз в секунду → монтаж/лицо.json
dry     — куски и склейки без сборки
preview — то же + звук склейки 16 кГц → расшифровка с метками склеек |N| → монтаж/превью.wav; концы кусков, за
          которыми через смычку идёт звук (не срезан ли последний слог: «кар|ты») — расшифровка с ним и без него
render  — монтаж/итог.mp4 (1080×1920, 25 fps) + склейки.txt
slova   — расшифровка итога → итог_слова.json + правки из плана "slova_fix"

plan.json (секунды — время исходника; края — по звуку и кратно кадру 1/25 с):
  "clips": [{"cut_from", "cut_to" — жёсткие края куска записи; "cut": [[от, до, "что"]] — вырезать внутри;
             "hum": [[от, до, "что"]] — мычание; "crop_x" — левый край квадрата в исходнике (иначе по лицу)}]
      Порядок clips — порядок в ролике (фразы можно переставлять). Между clips — стык как между фразами.
  "ends": [секунды] — где в тексте ролика кончается предложение (после этих слов остаётся вдох, а не смычка)
  "zooms": [крупность каждого куска] — 1.0 / 1.15 / 1.3, соседние разные (каждая склейка — со сменой крупности)
  "pause_cut" (0.32) — паузы короче остаются; "pause_long" (0.6) и "min_piece" (1.2) — пауза внутри фразы короче
      pause_long режется, только если оба куска выходят не короче min_piece; "keep_word" / "keep_sent" — сколько
      тишины оставить на стыке внутри фразы и между фразами
  "pad_out" — хвост после последнего звука ролика, с (тишина записи; во вдох и за cut_to не заходит; по умолчанию 0.08);
  "breath" — вдох на краях кусков (breath_edges): начало куска — на начало голоса (−0,03 с), вдох после последнего
      слова куска заглушается; по умолчанию включено в режиме "polnyi", в остальных выключено
  "end_freeze" — стоп-кадр последнего кадра в конце, с (когда за последним словом сразу вдох и закрытого рта дальше нет)
  "gain_db" — усиление (иначе подбирается до −14 LUFS); "limit_db" — потолок ограничителя пиков (ставится сам,
      если после усиления true peak выше −1,7 dBTP); "slova_fix" — правки расшифровки итога
Кадр: квадрат 1080×1080 из исходника 1920×1080 пиксель в пиксель, в кадре 1080×1920 на y 330…1410; 25 fps, как
исходник (кадры берутся по номерам). Крупнее 1,0 — кроп внутри того же квадрата, макушка на той же высоте.
  "video_y", "video_h" — верх и высота видео в кадре (по умолчанию 330 и 1080 — квадрат). Высота меньше 1080 —
      у готового квадрата срезается низ, верхние строки те же пиксель в пиксель на любой крупности. Раскладка «б»
      (2026-10-12): 416 и 960 — видео на y 416…1376, заголовок над ним виден и в ленте 4:5 (y 285–1635).
      Верх — только чётный (yuv420p): в макете титровщика 415, поставлено 416.
Звук: кусок записи, отличающийся от ролика больше чем на 2 LU, выравнивается; дальше только усиление (звук подкаста
сведён и сжат), ограничитель — только если пики не помещаются.
"""
import json, math, re, subprocess, sys, tempfile, wave
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]  # корень репозитория
sys.path.insert(0, str(ROOT))
import montazh as m  # noqa: E402

m.FPS = 25
# Исходник — "file" в plan.json; звук 16 кГц и words.json — в <папка>/монтаж/ (montazh.py transcribe); задаются в main()
SRC_WAV = SRC_WORDS = None
SQ, SQ_Y = 1080, 330
HEAD_MARGIN = 14
FADE_LOUD_DB, FADE_OUT_LOUD = -30.0, 0.04   # последние 20 мс куска громче −30 dBFS — кончается внутри звука: затухание 40 мс
FACE_FPS = 5
TARGET_LUFS, TP_MAX = -14.0, -1.7


def clip_range(c):
    return c.get("cut_from", c.get("from")), c.get("cut_to", c.get("to"))


def faces(work, plan, src):
    """Лицо (tools/face) и макушка (первая строка сверху, где над лицом есть пиксели ярче шторы) — 5 раз в секунду."""
    rows = []
    for c in plan["clips"]:
        t0, t1 = clip_range(c)
        t0, t1 = math.floor(t0 - 0.4), math.ceil(t1 + 0.4)
        d = Path(tempfile.mkdtemp(prefix="lico_"))
        seek = ["-ss", f"{t0:.3f}", "-t", f"{t1 - t0:.3f}", "-i", str(src)]
        m.run(["ffmpeg", "-v", "error", "-y", *seek, "-vf", f"fps={FACE_FPS}", "-q:v", "3", str(d / "%05d.jpg")])
        raw = subprocess.run(["ffmpeg", "-v", "error", *seek, "-vf", f"fps={FACE_FPS},scale=960:540", "-pix_fmt", "gray",
                              "-f", "rawvideo", "-"], capture_output=True).stdout
        g = np.frombuffer(raw, np.uint8).reshape(-1, 540, 960)
        res = subprocess.run([str(m.FACE_BIN), *map(str, sorted(d.glob("*.jpg")))], capture_output=True, text=True).stdout
        for line in res.splitlines():
            p = line.split()
            k = int(Path(" ".join(p[:-4])).stem) - 1
            cx, cy, w, h = float(p[-4]) * 1920, float(p[-3]) * 1080, float(p[-2]) * 1920, float(p[-1]) * 1080
            if k >= len(g):
                continue
            top = int((cy - h / 2) / 2)
            col = g[k][:max(top, 1), max(0, int((cx - 0.6 * w) / 2)): int((cx + 0.6 * w) / 2)]
            r = np.flatnonzero((col > 45).sum(1) >= 6)
            crown = (r[0] if len(r) else top) * 2
            rows.append([round(t0 + k / FACE_FPS, 2), round(cx), round(cy), round(w), round(h), int(crown)])
        a = np.array([r for r in rows if t0 <= r[0] <= t1])
        print(f"{t0}–{t1}: кадров с лицом {len(a)} из {len(g)}: x {a[:, 1].min():.0f}–{a[:, 1].max():.0f} (медиана "
              f"{np.median(a[:, 1]):.0f}), макушка {a[:, 5].min():.0f}–{a[:, 5].max():.0f}, низ лица до "
              f"{(a[:, 2] + a[:, 4] / 2).max():.0f}")
    (work / "лицо.json").write_text(json.dumps(rows))


def clip_crop_x(work, c):
    """Левый край квадрата для куска записи: "crop_x" из плана или по медиане лица (лицо по центру квадрата)."""
    if "crop_x" in c:
        return int(c["crop_x"])
    a = np.array(json.loads((work / "лицо.json").read_text()))
    t0, t1 = clip_range(c)
    sel = a[(a[:, 0] >= t0) & (a[:, 0] <= t1)]
    return int(min(max(round((np.median(sel[:, 1]) - SQ / 2) / 2) * 2, 0), 1920 - SQ))


def crop_for(work, s, e, z, crop_x):
    """Кроп куска: (сторона, x, y). 1,0 — квадрат 1080 пиксель в пиксель; крупнее — кроп 1080/z внутри него вокруг лица,
    макушка на той же высоте кадра, что и на 1,0, и не ближе HEAD_MARGIN к верхнему краю за весь кусок."""
    if z == 1.0:
        return SQ, crop_x, 0
    a = np.array(json.loads((work / "лицо.json").read_text()))
    sel = a[(a[:, 0] >= s - 0.11) & (a[:, 0] <= e + 0.11)]
    cx, crown_med, crown_min = np.median(sel[:, 1]), np.median(sel[:, 5]), sel[:, 5].min()
    side = round(SQ / z / 2) * 2
    x = int(round(min(max(cx - side / 2, crop_x), crop_x + SQ - side) / 2) * 2)
    y = int(max(0, min(round(crown_med * (1 - side / SQ)), crown_min - HEAD_MARGIN, 1080 - side)) // 2 * 2)
    return side, x, y


def crop_full(work, s, e, z):
    """Полный кадр 9:16 (япинг, Арон 2026-10-19: «в таком же формате зафигачить эти ролики»): кроп 9:16 из исходника
    вокруг лица → (ширина, высота, x, y). 1,0 — вся высота 1080; крупнее — 1080/z, макушка на той же высоте."""
    a = np.array(json.loads((work / "лицо.json").read_text()))
    sel = a[(a[:, 0] >= s - 0.11) & (a[:, 0] <= e + 0.11)]
    cx, crown_med, crown_min = np.median(sel[:, 1]), np.median(sel[:, 5]), sel[:, 5].min()
    ch = round(1080 / z / 2) * 2
    cw = round(ch * 9 / 16 / 2) * 2
    x = int(round(min(max(cx - cw / 2, 0), 1920 - cw) / 2) * 2)
    y = 0 if z == 1.0 else int(max(0, min(round(crown_med * (1 - ch / 1080)), crown_min - HEAD_MARGIN, 1080 - ch)) // 2 * 2)
    return cw, ch, x, y


def plan_words(plan):
    """Слова записи для правил пауз: конец предложения — только там, где он в тексте ролика ("ends" в плане)."""
    ws = [dict(w=re.sub(r"[.?!…]+$", "", x["w"]), s=x["s"], e=x["e"]) for x in next(iter(m.load_words(SRC_WORDS).values()))]
    for t in plan.get("ends", []):
        near = [w for w in ws if abs(w["e"] - t) < 0.8]
        w = min(near, key=lambda w: abs(w["e"] - t))
        w["w"] = w["w"].rstrip(",") + "."
    return ws


def pieces(plan, wav, words):
    lv, x, voiced = m.level(wav), m.audio(wav), m.envelope(wav)
    clips = plan["clips"]

    def iv(ci, extra=0.0):
        c = clips[ci]
        cf, ct = c.get("cut_from"), c.get("cut_to")
        return m.pieces_iv(voiced, lv, x, c.get("from", cf), c.get("to", ct), cf, ct, c.get("hum", []),
                           words, ci == 0, ci == len(clips) - 1, c.get("cut", []), extra)

    pre = {ci: iv(ci) for ci in range(len(clips))}
    for ci in range(len(clips) - 1):
        if pre[ci + 1][2] > 1e-3:
            pre[ci] = iv(ci, pre[ci + 1][2])
    out, notes = [], []
    for ci, c in enumerate(clips):
        raw, kept, _ = pre[ci]
        notes += kept
        cf, ct = c.get("cut_from"), c.get("cut_to")
        hums = c.get("hum", []) + c.get("cut", [])
        for s0, e0, why in raw:  # края — ровно по кадрам 25 fps; за жёсткий край и в вырезанное не заходят
            s, e = round(s0 * m.FPS) / m.FPS, round(e0 * m.FPS) / m.FPS
            lo_lim = max([cf if cf is not None else -1] + [b for a, b, *_ in hums if b <= s0 + 1e-3])
            hi_lim = min([ct if ct is not None else math.inf] + [a for a, b, *_ in hums if a >= e0 - 1e-3])
            if s < lo_lim - 1e-3:
                s = math.ceil(lo_lim * m.FPS - 0.01) / m.FPS
            if e > hi_lim + 1e-3:
                e = math.floor(hi_lim * m.FPS + 0.01) / m.FPS
            if e - s >= 1 / m.FPS:
                out.append([ci, s, e, why])
    return out, notes


BR_LOUD = 16.0     # громче (дБ над порогом речи) — это слово: гласные +20…+33, «с/ш» +20…+28, вдох 0…+13
BR_QUIET = -10.0   # тише — тишина студии
BR_CENT = 1000     # вдох — шум со спектром выше 1 кГц (гласные и «м/н» — ниже 600 Гц)
BR_MIN = 0.08      # шум вдоха не короче, с (хвост согласной и взрыв «т/к» — короче)
BR_LEAD = 0.03     # начало куска — за столько до начала голоса
BR_TAIL = 0.06     # после последнего громкого звука слова — хвост согласной, не трогается
BR_VOICED_IN = "аеёиоуыэюяйлмнр"   # слово начинается на гласную или сонорную — вдох может стоять к нему вплотную;
                                   # на шумную (х, ф, с, к…) и в конце любого слова (оглушение: «платёж» — «ш») — только через провал


def frame_feats(x, lv, a, b):
    """Каждые 10 мс на [a, b]: громкость над порогом речи (дБ), звонкость, центр спектра (Гц)."""
    n = int(round((b - a) / m.HOP))
    idx = int(round(a * 16000)) + 160 * np.arange(n)[:, None] + np.arange(400)[None, :]
    fr = x[np.clip(idx, 0, len(x) - 1)].astype(float) * np.hanning(400)
    sp = np.abs(np.fft.rfft(fr, axis=1)) ** 2
    cent = (sp * np.fft.rfftfreq(400, 1 / 16000)).sum(1) / (sp.sum(1) + 1e-12)
    i0 = int(round(a / m.HOP))
    return lv[i0:i0 + n], m.harmonicity(x, a, b)[:n], cent


def breath_edges(ps, wav, words):
    """Вдох на краях кусков (Арон, 2026-10-20: «где-то дыхание слишком много, в начале там такое дыхание есть»).
    Вдох, который стоит вплотную к слову, breaths_to_silence не видит (ему нужна тишина с обеих сторон): кусок
    начинался со вдоха, а после последнего слова в хвост куска попадал вдох перед следующей фразой.
    Вдох — тихий (не громче BR_LOUD) шум без гармоник со спектром выше BR_CENT, не короче BR_MIN.
    Начало: кусок начинается за BR_LEAD до начала голоса (край — по кадру не позже этого, звук до него — тишина).
    Конец: длина куска та же (пауза на стыке), вдох после хвоста согласной заглушается.
    В начале слова на шумную (х, с, ф, к…) и в конце любого слова вдох — только через провал тишины, иначе это часть
    слова (тихое «ш» в конце «платёж» по спектру как вдох).
    Возвращает новые куски и {номер куска: (заглушить до, заглушить после)} в секундах исходника."""
    x, lv = m.audio(wav), m.level(wav)
    out, mute, log = [], {}, []
    for k, (ci, s, e, why) in enumerate(ps):
        first = min((w for w in words if w["e"] > s + 0.02), key=lambda w: w["s"], default=None)
        last = max((w for w in words if w["s"] < e - 0.02), key=lambda w: w["e"], default=None)
        fl = re.sub(r"[^а-яё]", "", first["w"].lower())[:1] if first else ""
        L, h, c = frame_feats(x, lv, s, e)
        br = (L > BR_QUIET) & (L <= BR_LOUD) & (c >= BR_CENT) & (h < 0.45)
        loud = np.flatnonzero(L >= BR_LOUD)
        ns, ne = s, None
        if len(loud):
            on = loud[0]   # начало голоса: первый громкий кадр; перед ним — тихий звук начала слова или вдох
            j = on
            while j > 0 and L[j - 1] > BR_QUIET and not br[j - 1]:
                j -= 1     # тихое начало слова («м», «н», нарастание гласной) — к голосу
            if fl not in BR_VOICED_IN:
                j2 = j
                while j2 > 0 and L[j2 - 1] > BR_QUIET:
                    j2 -= 1  # шумная в начале слова идёт вплотную к гласной — вся до провала тишины
                j = j2
            run = br[:j]
            if run.sum() * m.HOP >= BR_MIN:
                t = s + j * m.HOP - BR_LEAD
                ns = max(s, math.floor(t * m.FPS + 1e-6) / m.FPS)
                mute.setdefault(k, [None, None])[0] = t
                log.append(f"кусок {k + 1}: вдох {run.sum() * m.HOP:.2f} с в начале ({s:.2f}–{s + j * m.HOP:.2f}) — "
                           f"начало {s:.2f} → {ns:.2f}, звук с {t:.2f} («{first['w'] if first else ''}»)")
            off = loud[-1] + 1 + int(round(BR_TAIL / m.HOP))
            while off < len(L) and L[off] > BR_QUIET:
                off += 1  # хвост слова (оглушённая согласная, затухание) — до провала тишины
            tail = br[off:]
            if tail.sum() * m.HOP >= BR_MIN:
                a = np.flatnonzero(tail)[0] + off
                ne = s + a * m.HOP
                mute.setdefault(k, [None, None])[1] = ne
                log.append(f"кусок {k + 1}: вдох {tail.sum() * m.HOP:.2f} с после «{last['w'] if last else ''}» "
                           f"({ne:.2f}–{e:.2f}) — заглушён")
        out.append([ci, ns, e, why])
    return out, {k: tuple(v) for k, v in mute.items()}, log


def edge_check(spans, wav):
    """Концы кусков: не остался ли за краем последний слог слова. Финальный слог после смычки («кар|ты», «момен|та»)
    выглядит как отдельный короткий звук после провала, и край, поставленный по концу гласной, его срезает
    (титровщик, 2026-10-12: «майнд-кар…»). Для каждого конца куска, за которым через ≤ 0,12 с тишины идёт звук:
    расшифровка последних 1,5 с куска как есть и вместе с этим звуком — если последнее слово меняется, смотреть спектр."""
    x, v = m.audio(wav), m.envelope(wav)
    z, out = np.zeros(4800, np.float32), []
    for k, (s, e) in enumerate(spans):
        i = int(round(e / m.HOP))
        inside, after = np.flatnonzero(v[max(0, i - 40):i]), np.flatnonzero(v[i:i + 15])
        if not len(inside) or not len(after):
            continue
        last, g0 = i - 40 + inside[-1] + 1, i + after[0]
        if (g0 - last) * m.HOP > 0.12:
            continue
        j = g0
        while j < g0 + 60 and (v[j] or v[j + 1:j + 4].any()):
            j += 1
        a0 = max(s, e - 1.5)
        tr = lambda b: m.whisper(np.r_[z, x[int(a0 * 16000): int(b * 16000)], z])["text"].strip()
        ta, tb = tr(e), tr(j * m.HOP + 0.03)
        na, nb = m.norm_words(ta), m.norm_words(tb)
        same_stem = bool(na and nb) and len(nb) >= len(na) and nb[len(na) - 1] != na[-1] and nb[len(na) - 1][:3] == na[-1][:3]
        out.append(f"кусок {k + 1}: за краем {e:.2f} через {(g0 - last) * m.HOP:.2f} с тишины звук {g0 * m.HOP:.2f}–{j * m.HOP:.2f} "
                   f"({(j - g0) * m.HOP:.2f} с){'  ← ПОСЛЕДНЕЕ СЛОВО МЕНЯЕТСЯ' if same_stem else ''}\n      как есть: {ta}\n      с ним:    {tb}")
    return out


def measure(path):
    err = subprocess.run(["ffmpeg", "-nostats", "-hide_banner", "-i", str(path), "-vn", "-af",
                          "ebur128=peak=true:framelog=quiet", "-f", "null", "-"], capture_output=True, text=True).stderr
    s = err[err.rfind("Summary:"):]
    g = lambda p: float(re.search(p, s)[1])
    return g(r"I:\s+(-?[\d.]+) LUFS"), g(r"LRA:\s+(-?[\d.]+) LU"), g(r"Peak:\s+(-?[\d.]+) dBFS")


def slova_fix(work, plan, rows, sfx):
    """Расшифровка итога (montazh.slova) и правки из плана: "set" — текст и/или время слова рядом с этим местом,
    "insert" — слово, которое whisper потерял, "drop" — лишнее «слово»; тире отдельным «словом» выкидывается."""
    m.slova(work, sfx)
    f = work / f"итог_слова{sfx}.json"
    ws = json.loads(f.read_text())

    def out_t(t):  # секунда исходника → секунда итога
        t0 = 0.0
        for ci, s, e, *_ in rows:
            if s - 1e-6 <= t <= e + 1e-6:
                return round(t0 + t - s, 2)
            t0 += e - s
        raise SystemExit(f"{t} — вне кусков итога")

    fix, log = plan.get("slova_fix", {}), []
    n = len(ws)
    ws = [w for w in ws if m.norm_words(w["w"])]
    if len(ws) != n:
        log.append(f"выкинуто «слов» без букв (тире): {n - len(ws)}")
    for it in fix.get("set", []):
        t = out_t(it["near"])
        was = it["was"] if isinstance(it["was"], list) else [it["was"]]  # как whisper пишет это слово (варианты)
        same = [w for w in ws if any(m.norm_words(w["w"]) == m.norm_words(x) for x in was)]
        w = min(same, key=lambda w: min(abs(w["s"] - t), abs(w["e"] - t)), default=None)
        if not w or min(abs(w["s"] - t), abs(w["e"] - t)) >= 0.6:  # whisper от прогона к прогону пишет по-разному
            log.append(f"НЕ НАЙДЕНО «{was[0]}» около {t:.2f} с — правка не применена, проверить текст глазами")
            continue
        old = dict(w)
        if "w" in it:
            w["w"] = it["w"]
        if "s" in it:
            w["s"] = out_t(it["s"])
        if "e" in it:
            w["e"] = out_t(it["e"])
        log.append(f"«{old['w']}» {old['s']:.2f} → «{w['w']}» {w['s']:.2f} ({it.get('why', '')})")
    for it in fix.get("drop", []):   # лишнее «слово» (whisper разбил название на два)
        t = out_t(it["near"])
        same = [w for w in ws if m.norm_words(w["w"]) == m.norm_words(it["was"]) and min(abs(w["s"] - t), abs(w["e"] - t)) < 0.6]
        if same:
            w = min(same, key=lambda w: abs(w["s"] - t))
            ws.remove(w)
            log.append(f"убрано «{w['w']}» {w['s']:.2f} ({it.get('why', '')})")
    for it in fix.get("insert", []):
        a, b = out_t(it["s"]), out_t(it["e"])
        for w in ws:
            if a <= w["s"] < b:
                w["s"] = round(b + 0.01, 2)
        ws.append({"w": it["w"], "s": a, "e": b})
        log.append(f"вставлено «{it['w']}» {a:.2f}–{b:.2f} ({it.get('why', '')})")
    ws.sort(key=lambda w: w["s"])
    f.write_text(json.dumps(ws, ensure_ascii=False, indent=1))
    print("\nПравки итог_слова.json:", *log, sep="\n  ")
    print(" ".join(w["w"] for w in ws))


def main():
    folder = Path(sys.argv[1]).expanduser().resolve()
    work = folder / "монтаж"
    step = sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith("--") else "dry"
    plan_name = sys.argv[sys.argv.index("--plan") + 1] if "--plan" in sys.argv else "plan.json"
    sfx = Path(plan_name).stem[len("plan"):]
    plan = json.loads((work / plan_name).read_text())
    global SRC_WAV, SRC_WORDS
    src = Path(plan["file"]).expanduser()
    if not src.is_absolute():
        src = folder / src
    SRC_WAV, SRC_WORDS = m.wav_of(src, work), work / "words.json"
    wav = SRC_WAV
    if step == "faces":
        return faces(work, plan, src)
    m.IV_PAUSE = float(plan.get("pause_cut", 0.32))
    m.IV_PAUSE_LONG = float(plan.get("pause_long", 0.6))
    m.IV_MIN_PIECE = float(plan.get("min_piece", 1.2))
    m.IV_KEEP_WORD = tuple(plan.get("keep_word", (0.06, 0.09)))
    m.IV_KEEP_SENT = tuple(plan.get("keep_sent", (0.10, 0.14)))
    m.PAD_OUT = float(plan.get("pad_out", m.PAD_OUT))   # хвост после последнего звука ролика (тишина записи)
    hold = float(plan.get("end_freeze", 0.0))           # стоп-кадр последнего кадра в конце, звук — тишина
    vy, vh = int(plan.get("video_y", SQ_Y)), int(plan.get("video_h", SQ))   # верх и высота видео в кадре 1080×1920
    assert 0 < vh <= SQ and vh % 2 == 0 and vy + vh <= m.H, (vy, vh)
    # yuv420p: цвет хранится через строку — нечётный верх ffmpeg молча округляет вниз (415 → 414), а честно поставить
    # видео на нечётную строку можно только пересчитав цвет (он размоется на полстроки). Поэтому верх — только чётный.
    assert vy % 2 == 0, f"video_y = {vy}: в yuv420p верх видео должен быть чётным (414 или 416, не 415)"
    words = plan_words(plan)
    ps, notes = pieces(plan, wav, words)
    mute = {}
    if plan.get("breath", bool(plan.get("polnyi"))):
        ps, mute, blog = breath_edges(ps, wav, words)
        notes += blog
    zooms = plan.get("zooms") or [(1.0, 1.15, 1.3)[k % 3] for k in range(len(ps))]
    assert len(zooms) == len(ps), f"в плане крупностей {len(zooms)}, кусков {len(ps)}"
    # Соседние куски в одной крупности разрешены (Арон, 2026-10-20: смена плана на кусках в одно слово — «тэ-тэ-тэ»,
    # обрывисто): крупность меняется только на смене мысли, вырез паузы внутри фразы идёт без смены плана.
    if not plan.get("polnyi"):
        assert all(a != b for a, b in zip(zooms, zooms[1:])), "соседние куски в одной крупности"
    cx = [clip_crop_x(work, c) for c in plan["clips"]]
    t, log, rows = 0.0, [], []
    for k, (ci, s, e, why) in enumerate(ps):
        z = zooms[k]
        if plan.get("polnyi"):
            cw, ch, x, y = crop_full(work, s, e, z)
            side = (cw, ch)
        else:
            side, x, y = crop_for(work, s, e, z, cx[ci])
        rows.append((ci, s, e, z, side, x, y))
        log.append(f"{t:6.2f}  кусок {k + 1:2d}  {s:8.2f}–{e:8.2f} ({e - s:5.2f} с, кадры {round(s * m.FPS)}–{round(e * m.FPS)})  "
                   f"крупность {z}  кроп {side}×{side} @ {x},{y}  ← {'начало' if k == 0 else why}")
        t += e - s
    total = f"{t + hold:.2f} с, склеек: {len(ps) - 1}"
    v, t0 = m.envelope(wav), 0.0   # паузы, которые остались внутри кусков
    for ci, s, e, *_ in rows:
        i0, i1 = int(round(s / m.HOP)), int(round(e / m.HOP))
        for a, b in m.runs_of(~v[i0:i1]):
            if (b - a) * m.HOP >= 0.25 and a > 0 and i0 + b < i1:
                w = m.sentence_end(words, s + a * m.HOP)[1]
                notes.append(f"пауза {(b - a) * m.HOP:.2f} с на {t0 + a * m.HOP:.2f} с итога (исходник {s + a * m.HOP:.2f}) после «{w}»")
        t0 += e - s
    if hold:
        notes.append(f"конец: стоп-кадр последнего кадра {hold:.2f} с (с {t:.2f} с итога), звук — тишина")
    print("\n".join(log), f"\nИтого {total}", *notes, sep="\n")
    if step == "preview":
        x, sr, f = m.audio(wav), 16000, int(0.012 * 16000)
        segs = []
        for k, (ci, s, e, *_) in enumerate(rows):
            p = x[int(round(s * sr)): int(round(e * sr))].copy()
            p[:f] *= np.linspace(0, 1, f)
            p[-f:] *= np.linspace(1, 0, f)
            mi, mo = mute.get(k, (None, None))
            if mi is not None:
                p[:max(0, int(round((mi - s) * sr)))] = 0
            if mo is not None:
                p[int(round((mo - s) * sr)):] = 0
            segs.append(p)
        y = np.concatenate(segs)
        with wave.open(str(work / "превью.wav"), "wb") as w:
            w.setnchannels(1), w.setsampwidth(2), w.setframerate(sr)
            w.writeframes((np.clip(y, -1, 1) * 32767).astype(np.int16).tobytes())
        cuts = np.cumsum([len(p) / sr for p in segs])[:-1]
        r = m.whisper(y, words=True)
        ws = [(w["start"], w["word"].strip()) for sg in r["segments"] for w in sg["words"]]
        txt, ci = [], 0
        for t0, w in ws:
            while ci < len(cuts) and cuts[ci] <= t0 + 0.05:
                txt.append(f"|{ci + 1}|")
                ci += 1
            txt.append(w)
        print("\n" + " ".join(txt))
        ec = edge_check([(s, e) for ci, s, e, *_ in rows], wav)
        print("\nКонцы кусков, за которыми через смычку идёт звук (сверить последний слог со спектром):", *(ec or ["нет"]), sep="\n  ")
    if step == "slova":
        return slova_fix(work, plan, rows, sfx)
    if step != "render":
        return
    # громкость кусков записи: отличается от ролика больше чем на 2 LU — выравнивается
    lu, remarks = {}, []
    for ci in sorted({r[0] for r in rows}):
        ls = [(m.lufs(src, s, e), e - s) for c2, s, e, *_ in rows if c2 == ci]
        ls = [(l, d) for l, d in ls if l is not None]
        if ls:
            lu[ci] = (10 * math.log10(sum(d * 10 ** (l / 10) for l, d in ls) / sum(d for _, d in ls)), sum(d for _, d in ls))
    ref = 10 * math.log10(sum(d * 10 ** (l / 10) for l, d in lu.values()) / sum(d for _, d in lu.values()))
    cgain = {ci: (ref - l if abs(ref - l) > m.IV_LEVEL_LU else 0.0) for ci, (l, _) in lu.items()}
    for ci, (l, _) in lu.items():
        remarks.append(f"громкость куска записи {ci + 1}: {l:.1f} LUFS (ролик {ref:.1f})"
                       + (f" → усиление {cgain[ci]:+.1f} дБ" if cgain[ci] else " — в пределах 2 LU, не трогаю"))
    inputs, aparts, vparts = [], [], []
    x16 = m.audio(wav)
    for k, (ci, s, e, z, side, x, y) in enumerate(rows):
        tail = x16[int((e - 0.02) * 16000): int(e * 16000)].astype(float)
        loud = 20 * math.log10(math.sqrt(float((tail ** 2).mean())) + 1e-9) > FADE_LOUD_DB
        fo = FADE_OUT_LOUD if loud else 0.015
        if loud:
            remarks.append(f"кусок {k + 1} кончается внутри звука ({e:.2f}) — затухание {fo * 1000:.0f} мс вместо 15")
        base = max(0.0, math.floor(s - 2))            # целая секунда — на сетке кадров 25 fps
        off = base - 0.5 / m.FPS                      # вход открываем на полкадра раньше: первый кадр — ровно кадр base
        inputs += ["-ss", f"{off:.3f}", "-i", str(src)]
        f0, f1 = round((s - base) * m.FPS), round((e - base) * m.FPS)   # номера кадров от base: ровно кадры исходника
        if isinstance(side, tuple):   # полный кадр 9:16
            cropf = f"crop={side[0]}:{side[1]}:{x}:{y},scale={m.W}:{m.H}:flags=lanczos"
        else:
            cropf = f"crop={side}:{side}:{x}:{y}" + ("" if side == SQ else f",scale={SQ}:{SQ}:flags=lanczos")
        last = hold and k == len(rows) - 1   # конец ролика: держим последний кадр, звук — тишина
        cut_low = "" if vh == SQ or isinstance(side, tuple) else f",crop={SQ}:{vh}:0:0"   # видео ниже квадрата: срезается низ готового квадрата
        vparts.append(f"[{k}:v]trim=start_frame={f0}:end_frame={f1},setpts=PTS-STARTPTS,{cropf}{cut_low},setsar=1"
                      + (f",tpad=stop_mode=clone:stop_duration={hold:.3f}" if last else "") + f"[v{k}];")
        aparts.append(f"[{k}:a]atrim={s - off:.4f}:{e - off:.4f},asetpts=PTS-STARTPTS,aformat=sample_rates=48000:channel_layouts=stereo,"
                      f"volume={cgain.get(ci, 0.0):.2f}dB,afade=t=in:d=0.01,afade=t=out:st={max(0, e - s - fo):.3f}:d={fo}"
                      + "".join(f",afade=t={tp}:st={max(0.0, tt - s - (0.02 if tp == 'out' else 0)):.4f}:d=0.02"   # вдох — тишина
                                for tp, tt in zip(("in", "out"), mute.get(k, (None, None))) if tt is not None)
                      + (f",apad=pad_dur={hold:.3f}" if last else "") + f"[a{k}];")
    k = len(rows)
    ajoin = "".join(aparts) + "".join(f"[a{i}]" for i in range(k)) + f"concat=n={k}:v=0:a=1[a0]"
    tmp = Path(tempfile.mkdtemp(prefix="kv_")) / "join.wav"   # первый проход — только звук: замер громкости и пиков
    m.run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", ajoin, "-map", "[a0]", "-c:a", "pcm_s24le", str(tmp)])
    i0, lra0, tp0 = measure(tmp)
    gain = float(plan["gain_db"]) if "gain_db" in plan else round(TARGET_LUFS - i0, 1)
    audio = f"volume={gain:.2f}dB"
    remarks.append(f"склейка до усиления: {i0:.1f} LUFS, LRA {lra0:.1f}, true peak {tp0:.1f} dBTP → усиление {gain:+.1f} дБ")
    if "limit_db" in plan or tp0 + gain > TP_MAX:
        lim = float(plan.get("limit_db", -2.0))
        audio += (f",aresample=192000,alimiter=limit={10 ** (lim / 20):.4f}:attack=2:release=60:level=false:latency=true,"
                  f"aresample=48000")
        remarks.append(f"пики после усиления {tp0 + gain:.1f} dBTP — ограничитель с потолком {lim:.1f} (true peak, 4× частота)")
    fc = "".join(vparts) + "".join(aparts) + "".join(f"[v{i}][a{i}]" for i in range(k)) + f"concat=n={k}:v=1:a=1[vq][a0];" + \
        f"[a0]{audio}[a1];" + ("[vq]null[vv]" if plan.get("polnyi") else f"[vq]pad={m.W}:{m.H}:0:{vy}:black[vv]")
    m.run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", fc, "-map", "[vv]", "-map", "[a1]",
           "-r", str(m.FPS), "-c:v", "libx264", "-preset", "slow", "-crf", "12", "-pix_fmt", "yuv420p",
           "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709", "-color_range", "tv",
           "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", str(work / f"итог{sfx}.mp4")])
    i1, lra1, tp1 = measure(work / f"итог{sfx}.mp4")
    remarks.append(f"итог: {i1:.1f} LUFS, LRA {lra1:.1f}, true peak {tp1:.1f} dBTP")
    (work / f"склейки{sfx}.txt").write_text(
        "Время итога (с) · кусок · секунды исходника (кадры 25 fps) · крупность · кроп из 1920×1080 · причина склейки\n"
        f"Кадр 1080×1920, 25 fps. Видео 1080×{vh} — на y {vy}…{vy + vh}"
        + ("" if vh == SQ else f" (квадрат 1080×1080 из исходника без нижних {SQ - vh} px)")
        + "; крупность 1.0 — пиксель в пиксель, 1.15 и 1.3 — кроп 940×940 и 830×830 внутри того же квадрата (в столбце «кроп» — квадрат целиком).\n"
        f"Над видео — чёрное поле до y {vy} (заголовок), под видео — чёрное поле с y {vy + vh} (субтитры); по ширине текст — в 35…1045, ниже 1150 — до 960.\n\n"
        + "\n".join(log) + f"\n\nИтого: {total}\n" + "".join(f"Оставлено: {w}\n" for w in notes)
        + "".join(f"Примечание: {w}\n" for w in remarks))
    print(*remarks, sep="\n")


if __name__ == "__main__":
    main()
