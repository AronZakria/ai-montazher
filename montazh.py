#!/usr/bin/env python3
"""Монтаж говорящей головы: жёсткие склейки без пауз, вертикаль 9:16 по лицу.

    .venv/bin/python montazh.py <папка с дублями> [transcribe|mychanie|render|slova] [--static] [--plan plan_X.json]

transcribe — расшифровка всех дублей (.mov/.MOV/.mp4 в папке) со словами по времени → <папка>/монтаж/words.json
             и черновик plan.json. Дубли вне папки ролика (~/Downloads) — расшифровать через временную папку со ссылками
             на них и положить words.json в монтаж/ ролика: в репозиторий исходники не попадают
mychanie   — поиск мычания в кусках плана: перерасшифровка каждого куска отдельно (→ слова_кусков.json),
             звонкий ровный звук, шум на стыке со словом, растянутые слова; каждое место — расшифровка его одного
             и расшифровка окна без него (→ мычание.json). Подтверждённое вписать в клип: "hum": [[от, до, "что это"]]
render     — сборка по plan.json → <папка>/монтаж/итог.mp4 + склейки.txt
slova      — расшифровка готового итога со временем слов → итог_слова.json (для титровщика и сборщика)
По умолчанию кадр следит за глазами (как Motion tracking в CapCut) → итог.mp4
--static   — неподвижный кадр на каждый кусок → итог_статичный.mp4
--plan plan_X.json — другой план в той же папке → итог_X.mp4, склейки_X.txt, итог_слова_X.json (варианты порядка)
Безопасная зона Reels — docs/безопасная_зона.md.

plan.json: {"clips": [{"file": "…mov", "from": 2.7, "to": 12.0, "note": "…"}]}
from/to — примерные границы нужной речи (по words.json); точный край скрипт ищет сам по звуку.
cut_from/cut_to — жёсткий край (секунды исходника) там, где соседнее слово идёт без паузы
  и поиск края по звуку (SEARCH) захватил бы его: дальше этой точки кусок не заходит.
file — путь от папки ролика, можно абсолютный или с ~ (одна длинная запись вне репозитория).
wav  — (в плане или клипе) готовый звук исходника 16 кГц моно, чтобы не делать свой.
hum  — (в клипе) мычание, вырезается всегда, как тишина: [[от, до, "с-с… м-м"]], секунды исходника.
  Запасы у соседних слов в него не заходят. Ставится только после проверки (mychanie, спектр, перерасшифровка).
cut  — (в клипе) вырезать фразу внутри куска (связка, вводное, пояснение — по списку Арона): [[от, до, "что"]].
  Режется как мычание; края — по звуку и кратно кадру (от — начало первого вырезанного слова, до — конец последнего;
  слова слиты — край в провале звука между ними). На стыке остаётся тишина, что была вокруг, не больше 0,30 с,
  если в вырезанном или перед ним кончается предложение, иначе 0,20 с.
keep — (в клипе, говорящая голова) тихий звук речи под порогом — считать речью: [[от, до, "что"]], секунды исходника.
  Петличка в тихой комнате (2026-10-13, IMG_9754.mov): фон −69 дБ, порог «фон + 20 дБ» не видит взрыв «т»/«к» после
  смычки («лет», «интеллект»), слабые «ф» и «с» на краю слова («математиков», «сейчас», «в постоянное», «Вторая») —
  край куска их срезал. Ставится только по спектру (звук есть, это часть слова, а не вдох и не щелчок губ).
speed — (в плане) ускорение всего ролика после склеек и до громкости: видео setpts + 30 fps, звук atempo (тембр
  тот же). Интервью — 1,1 (Арон, 2026-09-30); по умолчанию 1,0. склейки.txt — в секундах итога после ускорения.
track — (в плане) false: неподвижный кадр как режим этого ролика (как --static, но итог — итог.mp4).
flat_gain — (в плане, говорящая голова) число, LUFS: вместо однопроходного loudnorm — ровное усиление всего ролика на
  одно и то же число дБ, такое, чтобы громкость собранного звука стала этой (обычно -14), и ограничитель пиков на
  FLAT_CEIL. Первый проход меряет собранный звук, второй усиливает. Итог выходит тише цели на то, что съел срез
  пиков (петличка: 0,8 LU); сколько мест и на сколько дБ выше потолка — в склейки.txt («Звук: …»).
flat_gain_db — (в плане, вместе с flat_gain) усиление, дБ, закреплено числом вместо расчёта: после правки, которая
  добавляет или убирает тишину (хвост), звук ролика остаётся тем же до сэмпла. Брать из склейки.txt прошлой сборки.
  True peak итога проверять всё равно: AAC от усиления к усилению выбрасывает пик по-разному.
porog — (в плане) порог речи, дБ над фоном комнаты (p10 огибающей каждого файла); по умолчанию POROG = 20.
  Встроенный микрофон телефона (2026-10-17, IMG_9862–9881.MOV): фон −48…−55 дБ, гласные всего на +15…+30 дБ выше,
  тихие слова («люди начали», «существует», «мы опубликовали») — на +5…+19: порог +20 находил «паузы» внутри слов
  и резал их. Подбирать по огибающей и расшифровке окон (паузы > 0,30 с — только настоящие), края — по спектру.
ekran — (в клипе) true: в кадре не лицо, а экран (снят камерой телефона): картинка — кадр целиком (вписан в 1080×1920,
  без кропа), крупность 1,0 и в чередовании крупности не участвует, слежения и поиска лица нет. Звук — как у всех
  кусков: те же паузы, ускорение, громкость. В склейки.txt — «экран (кадр целиком)».
tail_to — (в клипе, говорящая голова) секунда исходника: последний кусок клипа кончается не раньше неё — хвост тишины
  после последнего слова, пока человек ещё смотрит в камеру (2026-10-17, конец «соцсети»: 16,53 → 16,80). Остальные
  куски и время склеек не меняются; фейд звука 15 мс переезжает в конец хвоста. Хвост — тишина ≤ 0,30 с (PAUSE_MIN).

Интервью (Арон, 2026-09-30) — "format": "interview": горизонтальное видео в вертикальном кадре, без кропа по лицу.
  "only": {"file": "v_kadre.json", "who": "M"} — в кадре только этот человек: где в исходнике чужой кадр
  (Zoom переключает с опозданием), на краю куска держится стоп-кадр ближайшего своего, звук идёт как есть.
  Паузы — «не пулемёт» (IV_PAUSE, IV_KEEP_*): пауза короче 0,5 с остаётся, длиннее — вырезается, но после
  конца предложения остаётся вдох 0,30 с, внутри фразы — 0,20 с. Вдох (шум без гармоник в тишине) — это тишина.
  Конец предложения — по словам: слова_кусков.json (mychanie) или "words" в плане.
Правила монтажа — docs/монтаж.md.
"""
import json, math, os, subprocess, sys, tempfile, wave
from fractions import Fraction
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
FACE_BIN = ROOT / "tools" / "face"
EYES_BIN = ROOT / "tools" / "eyes"

# Параметры склейки (секунды)
HOP = 0.01          # шаг огибающей звука
POROG = 20          # порог речи, дБ над фоном комнаты; "porog" в плане — свой для записи (телефон без петлички — 12)
PAUSE_MIN = 0.30    # пауза внутри дубля длиннее — вырезается
PAD_IN = 0.04       # запас перед первым звуком фразы
PAD_OUT = 0.08      # запас после последнего звука (хвост согласных)
SEARCH = 0.35       # насколько искать край речи за пределами from/to
ZOOMS = [1.0, 1.15] # чередование крупности на склейках — прячет прыжок кадра
ZOOM_MIN_PIECE = 2.0  # кусок короче — остаётся в крупности предыдущего (без прыжка на короткий план)
FACE_AT = 0.45      # лицо на этой высоте кадра (доля сверху) при наезде
EYES_AT = 0.36      # глаза на этой высоте кадра (доля сверху) — ≈690 px; было 0,38 — подняли, чтобы субтитры внизу не закрывали рот (Арон, 2026-09-28)
TRACK_DEADZONE = 0.02  # мёртвая зона слежения, доля ширины исходника (~6 % кадра): мелкие движения головы кадр не двигают
TRACK_SMOOTH = 0.25 # сглаживание траектории глаз (сигма, с); больше — плавнее, но ленивее
W, H, FPS = 1080, 1920, 30

# Интервью: горизонтальное видео в вертикальном кадре (Арон, 2026-09-30)
IV_CUT_BOTTOM = 26  # снизу исходника Zoom срезается подпись с именем («Maxim Spiridonov»)
IV_W, IV_H = 1080, 564  # видео во всю ширину кадра: 640×334 → 1080×564
IV_Y = 578          # верх видео: центр видео (860) — центр внимания безопасной зоны; сверху рубрика и заголовок, снизу субтитры
IV_HAIR = 0.45      # макушка выше рамки лица из tools/face на эту долю её высоты (волосы, лоб)
IV_HEAD_MARGIN = 0.03  # запас над макушкой на крупности 1,15, доля высоты видео (≈17 px)

# Интервью: паузы «не пулемёт» (Арон, 2026-09-30: «не так, чтобы прям та-та-та-тах, как будто по одному слову»).
# Было: паузы > 0,30 с резались везде, на стыке оставалось 0,12 с — 12–16 склеек на 26–60 с.
# Замер по речи гостя (7 роликов): паузы внутри фразы — медиана 0,25 с (p75 0,44), после запятой 0,20,
# между предложениями — медиана 0,53 (p25 0,34).
IV_PAUSE = 0.50               # пауза короче — остаётся как есть (живое дыхание речи); длиннее — вырезается
IV_KEEP_SENT = (0.12, 0.18)   # вырезанная пауза после . ? ! — остаётся 0,30 с: хвост после слова + вдох перед следующим
IV_KEEP_WORD = (0.08, 0.12)   # вырезанная пауза или мычание внутри фразы — остаётся 0,20 с
IV_PAUSE_LONG = 1.0           # пауза внутри фразы 0,5–1,0 с режется, только если оба куска выйдут не короче
IV_MIN_PIECE = 1.5            # 1,5 с (иначе кусок в одно слово: «Нередко», «медицины»); длиннее 1,0 с — режется всегда
# Звук интервью (2026-09-30): одна дорожка Zoom, куски из разных минут записи
IV_LEVEL_LU = 2.0   # кусок записи тише/громче всего ролика больше чем на 2 LU — выравнивается усилением (№5: повтор
                    # «Это их просто испортит» на 4 LU тише соседних). Внутри куска записи живая динамика не трогается.
IV_TP = -2.0        # потолок loudnorm: AAC добавляет 0,2–0,3 дБ, с -1,5 итог выходил -1,3…-1,4 dBTP (норма ≤ -1,5)
# Скорость — "speed" в плане (Арон, 2026-09-30: интервью «режь по списку и ускоряй» — 1,1: темп гостя
# 2,3–2,6 слова/с → 2,5–2,9). Говорящая голова Арона — 1,0.
FLAT_CEIL = -2.0    # "flat_gain": потолок ограничителя пиков, дБFS — после AAC итог ≤ -1,5 dBTP (как IV_TP у интервью)
BREATH_H = 0.45     # вдох: шум без гармоник — автокорреляция голоса < 0,45 в ≥ 80 % кадров,
BREATH_MIN = 0.12   # не короче 0,12 с и с тишиной ≥ 0,08 с с обеих сторон — для пауз это тишина (не «речь»)
BREATH_MAX_DB = 25  # и не громче порога речи + 25 дБ (гласные — +40…+48): громкий шум без гармоник — сиплое слово
# Мычание (Арон, 2026-09-30: «вырежи мычание») — кандидаты для mychanie; режется только то, что вписано в "hum"
HUM_VOICED = 0.25   # звонкий ровный звук (гармоники, спектр почти не меняется) не короче — «м-м», «э-э», «и-и-и»
HUM_NOISE = 0.30    # ровный шум без гармоник вплотную к слову не короче — «с-с-с»
HUM_FLUX = 5.5      # «ровный»: средний сдвиг лог-мел-спектра за 50 мс меньше, дБ (в словах — 8–30)
HUM_HARM = 0.55     # «звонкий»: автокорреляция голоса (70–400 Гц) выше


def run(cmd):
    subprocess.run(cmd, check=True)


def wav_of(src: Path, work: Path) -> Path:
    w = work / (src.stem.replace(" ", "_") + ".wav")
    if not w.exists():
        run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-ac", "1", "-ar", "16000", str(w)])
    return w


_AUDIO = {}


def audio(w: Path):
    """Звук wav 16 кГц моно, float32 (кэш: одна длинная запись читается один раз)."""
    if w not in _AUDIO:
        _AUDIO[w] = np.frombuffer(wave.open(str(w)).readframes(10**10), np.int16).astype(np.float32) / 32768
    return _AUDIO[w]


_LEVEL = {}


def level(w: Path, porog=POROG):
    """Громкость каждые 10 мс относительно порога речи (фон комнаты + porog дБ, по умолчанию 20), дБ."""
    if (w, porog) not in _LEVEL:
        a = audio(w)
        n = int(16000 * HOP)
        r = np.sqrt((a[: len(a) // n * n].astype(float).reshape(-1, n) ** 2).mean(1)) + 1e-9
        db = 20 * np.log10(r)
        _LEVEL[w, porog] = db - (np.percentile(db, 10) + porog)  # порог речи: на porog дБ выше фона комнаты
    return _LEVEL[w, porog]


def envelope(w: Path, porog=POROG):
    v = level(w, porog) > 0
    v[: int(0.2 / HOP)] = False  # щелчок старта записи OBS
    return v


def harmonicity(a, t0, t1):
    """Звонкость каждые 10 мс на [t0, t1]: максимум нормированной автокорреляции (окно 40 мс) на 70–400 Гц.
    Голос («м-м», гласные) ≈ 0,7–0,95; вдох, «с», «ш» < 0,45."""
    sr, win, hop = 16000, 640, 160
    n = int(round((t1 - t0) / HOP))
    x = np.pad(a, (win, win))[int(t0 * sr) + win // 2: int(t0 * sr) + win // 2 + n * hop + win]
    if n <= 0:
        return np.zeros(0)
    idx = np.arange(win)[None, :] + hop * np.arange(n)[:, None]
    fr = x[np.clip(idx, 0, len(x) - 1)].astype(float)
    fr -= fr.mean(1, keepdims=True)
    ac = np.fft.irfft(np.abs(np.fft.rfft(fr * np.hanning(win), 2 * win, axis=1)) ** 2, axis=1)[:, :win]
    ac /= ac[:, :1] + 1e-12
    return ac[:, sr // 400: sr // 70].max(1)


def spec_flux(a, t0, t1, lag=5):
    """Насколько меняется спектр каждые 10 мс на [t0, t1]: средний сдвиг лог-мел-спектра (40 полос) за lag×10 мс, дБ.
    Слова — 8–30 дБ; тянущийся звук («м-м», «э-э», «с-с-с») < HUM_FLUX."""
    sr, win, hop, nb = 16000, 400, 160, 40
    n = int(round((t1 - t0) / HOP))
    if n <= 0:
        return np.zeros(0)
    mel = lambda f: 2595 * np.log10(1 + f / 700)
    pts = 700 * (10 ** (np.linspace(mel(80), mel(6000), nb + 2) / 2595) - 1)
    bins = np.floor(513 * pts / sr).astype(int)
    fb = np.zeros((nb, 257))
    for i in range(nb):
        l, c, r = bins[i], bins[i + 1], bins[i + 2]
        fb[i, l:c] = (np.arange(l, c) - l) / max(1, c - l)
        fb[i, c:r] = (r - np.arange(c, r)) / max(1, r - c)
    x = np.pad(a, (win, win))[int(t0 * sr) + win: int(t0 * sr) + win + (n + lag) * hop + win]
    idx = np.arange(win)[None, :] + hop * np.arange(n + lag)[:, None]
    fr = x[np.clip(idx, 0, len(x) - 1)].astype(float) * np.hanning(win)
    m = 10 * np.log10(fb @ (np.abs(np.fft.rfft(fr, 512, axis=1)) ** 2).T + 1e-10).T
    return np.abs(m[lag:] - m[:-lag]).mean(1)[:n]


def runs_of(m):
    """Отрезки подряд идущих True: [(начало, конец)] в индексах."""
    ch = np.flatnonzero(np.diff(np.r_[0, np.asarray(m, int), 0]))
    return list(zip(ch[::2], ch[1::2]))


def breaths_to_silence(v, h, lvl):
    """Вдох (тихий шум без гармоник, с тишиной с обеих сторон) — не речь: для пауз он тишина. Меняет v, возвращает
    отрезки. Дырки до 30 мс внутри вдоха не делят его на части (вдох шумит неровно). Громче BREATH_MAX_DB — это слово:
    сиплое слово в конце фразы («красавчик» с хрипотцой) тоже без гармоник, но на 20–25 дБ громче вдоха."""
    gap = int(0.08 / HOP)
    rr = []
    for s, e in runs_of(v):
        if rr and s - rr[-1][1] <= 3:
            rr[-1][1] = e
        else:
            rr.append([s, e])
    out = []
    for s, e in rr:
        if (e - s) * HOP >= BREATH_MIN and np.mean(h[s:e] < BREATH_H) >= 0.8 and lvl[s:e].max() <= BREATH_MAX_DB \
                and not v[max(0, s - gap):s].any() and not v[e:e + gap].any():
            v[s:e] = False
            out.append((s, e))
    return out


def load_words(path):
    """Слова со временем: {файл: [слова]} (transcribe, mychanie) или список фраз с "words" (расшифровка всей записи)."""
    d = json.loads(Path(path).read_text())
    if isinstance(d, list):
        return {"*": [w for s in d for w in (s.get("words") or [s])]}
    return d


def ends_sentence(w):
    return w.rstrip("»\"')")[-1:] in ".?!…"


def sentence_end(words, t):
    """Кончается ли предложение на речи, которая оборвалась в t: (да/нет, слово). Слово — из начатых до t то, чей
    конец ближе всего к t (whisper тянет начало слова после паузы назад в паузу: «задумал. Вот» — «Вот» с 2040,89)."""
    prev = [w for w in words if w["s"] < t + 0.05]
    if not prev:
        return False, ""
    w = min(prev, key=lambda w: abs(w["e"] - t))["w"]
    return ends_sentence(w), w


def pieces(voiced, t0, t1, hard_in=None, hard_out=None):
    """Куски речи внутри [t0, t1]: точные края + вырезанные паузы.
    hard_in/hard_out — жёсткий край: звук и запасы за ним не берутся (соседнее слово без паузы)."""
    n = len(voiced)
    lo = t0 - SEARCH if hard_in is None else hard_in
    hi = t1 + SEARCH if hard_out is None else hard_out
    i0 = max(0, math.ceil(lo / HOP - 1e-6))
    i1 = min(n, int(hi / HOP + 1e-6))
    idx = np.flatnonzero(voiced[i0:i1]) + i0
    # речь, начавшаяся до from - SEARCH, в дубль не входит: край ищем от первого звука после t0 - SEARCH
    if len(idx) == 0:
        return []
    # группы звука, разделённые паузами > PAUSE_MIN
    gaps = np.flatnonzero(np.diff(idx) * HOP > PAUSE_MIN)
    starts = np.r_[idx[0], idx[gaps + 1]]
    ends = np.r_[idx[gaps], idx[-1]] + 1
    out = []
    for s, e in zip(starts, ends):
        if (e - s) * HOP < 0.15:  # щелчок/вдох — не речь
            continue
        out.append([max(0.0 if hard_in is None else hard_in, s * HOP - PAD_IN),
                    min(math.inf if hard_out is None else hard_out, e * HOP + PAD_OUT)])
    # соседние куски не должны перекрываться из-за запасов
    for a, b in zip(out, out[1:]):
        if a[1] > b[0]:
            a[1] = b[0] = (a[1] + b[0]) / 2
    return out


def with_keep(voiced, keeps):
    """Огибающая, в которой отрезки "keep" клипа — речь (тихий звук под порогом: взрыв «т» после смычки, слабое «ф»)."""
    if not keeps:
        return voiced
    v = voiced.copy()
    for a, b, *_ in keeps:
        v[max(0, int(a / HOP + 1e-6)): math.ceil(b / HOP - 1e-6)] = True
    return v


def pieces_hum(voiced, t0, t1, hard_in, hard_out, hums):
    """Говорящая голова: куски как pieces(), но мычание из "hum" вырезается всегда — края мычания работают как жёсткий край."""
    hs = sorted((a, b) for a, b, *_ in hums if b > t0 - SEARCH and a < t1 + SEARCH)
    if not hs:
        return pieces(voiced, t0, t1, hard_in, hard_out)
    out, lo, hin = [], t0, hard_in
    for a, b in hs:
        out += pieces(voiced, lo, a, hin, a)
        lo, hin = b, b
    return out + pieces(voiced, lo, t1, hin, hard_out)


def pieces_iv(voiced, lvl, x, t0, t1, hard_in, hard_out, hums, words, first, last, cuts=(), tail_extra=0.0):
    """Интервью: куски речи внутри [t0, t1] «не пулемётом» (Арон, 2026-09-30).
    Пауза < IV_PAUSE остаётся как есть; длиннее, мычание ("hum") и вырезанные фразы ("cut") — вырезаются, на стыке
    остаётся IV_KEEP_SENT после конца предложения или IV_KEEP_WORD внутри фразы. Пауза внутри фразы короче
    IV_PAUSE_LONG режется, только если куски по обе стороны ≥ IV_MIN_PIECE. Вдох в тишине — тишина.
    Запасы — только тишина: не заходят в мычание, в вырезанное, во вдох (обрывок вдоха на стыке звучит как «х») и за
    жёсткий край; если с одной стороны тишины мало, остаток берётся с другой. Тишины нет (слова слиты) — стык впритык.
    tail_extra — сколько добавить тишины после последнего слова (у следующего куска записи первое слово впритык).
    Возвращает ([[начало, конец, причина склейки]], оставленные паузы, сколько тишины не хватило перед первым словом)."""
    lo = t0 - SEARCH if hard_in is None else hard_in
    hi = t1 + SEARCH if hard_out is None else hard_out
    i0 = max(0, math.ceil(lo / HOP - 1e-6))
    i1 = min(len(voiced), int(hi / HOP + 1e-6))
    v = voiced[i0:i1].copy()
    hs = sorted([(a, b, (n[0] if n else "мычание"), "hum") for a, b, *n in hums if b > lo and a < hi] +
                [(a, b, (n[0] if n else "фраза"), "cut") for a, b, *n in cuts if b > lo and a < hi])
    for a, b, *_ in hs:
        v[max(0, int(a / HOP) - i0): max(0, math.ceil(b / HOP) - i0)] = False
    br = breaths_to_silence(v, harmonicity(x, i0 * HOP, i1 * HOP), lvl[i0:i1])
    noise = [(a, b) for a, b, *_ in hs] + [((i0 + s) * HOP, (i0 + e) * HOP) for s, e in br]
    groups = []  # группы звука: паузы короче IV_PAUSE внутри группы не режутся
    for s, e in runs_of(v):
        g0, g1 = (i0 + (groups[-1][1] if groups else 0)) * HOP, (i0 + s) * HOP
        if groups and g1 - g0 < IV_PAUSE and not any(a < g1 and b > g0 for a, b, *_ in hs):
            groups[-1][1] = e
        else:
            groups.append([s, e])
    groups = [[(i0 + s) * HOP, (i0 + e) * HOP] for s, e in groups if (e - s) * HOP >= 0.15]  # щелчок — не речь
    # стыки групп: мычание, вырезанная фраза, конец предложения и пауза ≥ IV_PAUSE_LONG режутся всегда; пауза внутри
    # фразы короче — только если оба куска выходят ≥ IV_MIN_PIECE, иначе кусок в одно слово («Нередко», «медицины»)
    bnd = []
    for k in range(1, len(groups)):
        pe, s = groups[k - 1][1], groups[k][0]
        hum = [(n, kind, a, b) for a, b, n, kind in hs if a < s and b > pe]
        end, w = sentence_end(words, pe)
        if not end:  # в вырезанном кончалось предложение («к 100[, поскольку … по больнице.] Но») — стык как после точки
            end = any(ends_sentence(x["w"]) for _, kind, a, b in hum if kind == "cut"
                      for x in words if a <= (x["s"] + x["e"]) / 2 <= b)
        bnd.append({"hum": hum, "end": end, "w": w, "gap": s - pe, "cut": bool(hum) or end or s - pe >= IV_PAUSE_LONG})

    def piece_len(k):  # длина куска с группой k при текущих склейках (+ запасы)
        a, b = k, k
        while a > 0 and not bnd[a - 1]["cut"]:
            a -= 1
        while b < len(bnd) and not bnd[b]["cut"]:
            b += 1
        return groups[b][1] - groups[a][0] + 0.25

    kept = []
    for j in sorted(range(len(bnd)), key=lambda j: -bnd[j]["gap"]):
        if not bnd[j]["cut"]:
            bnd[j]["cut"] = True
            short = min(piece_len(j), piece_len(j + 1))
            if short < IV_MIN_PIECE:
                bnd[j]["cut"] = False
                kept.append(f"пауза {bnd[j]['gap']:.2f} с после «{bnd[j]['w']}» ({groups[j][1]:.2f}) не вырезана: "
                            f"кусок вышел бы {short:.2f} с")
    merged, info = [list(groups[0])] if groups else [], []
    for k in range(1, len(groups)):
        if bnd[k - 1]["cut"]:
            merged.append(list(groups[k]))
            info.append(bnd[k - 1])
        else:
            merged[-1][1] = groups[k][1]
    groups = merged
    lim_lo, lim_hi = (0.0 if hard_in is None else hard_in), (math.inf if hard_out is None else hard_out)
    room_after = lambda e, nxt: min([a for a, b in noise if a >= e - 1e-9] + [nxt, lim_hi]) - e
    room_before = lambda s, prv: s - max([b for a, b in noise if b <= s + 1e-9] + [prv, lim_lo])
    out, head_short = [], 0.0
    for k, (s, e) in enumerate(groups):
        if k == 0:
            pin = min(PAD_IN if first else IV_KEEP_SENT[1], room_before(s, lim_lo))
            head_short = 0.0 if first else IV_KEEP_SENT[1] - pin
            why = "другой кусок записи"
        else:
            pe = groups[k - 1][1]
            hum, end, w = info[k - 1]["hum"], info[k - 1]["end"], info[k - 1]["w"]
            pout, pin = IV_KEEP_SENT if end else IV_KEEP_WORD
            ra, rb = min(room_after(pe, s), s - pe), min(room_before(s, pe), s - pe)
            want = pout + pin
            pin = min(pin, rb)
            pout = min(ra, want - pin)
            pin = min(rb, want - pout)
            out[-1][1] = pe + pout
            what = {"hum": "мычание", "cut": "вырезано"}
            why = (" + ".join(f"{what[kind]} «{n}»" for n, kind, *_ in hum) if hum else f"пауза {s - pe:.2f} с") + \
                  f" после «{w}» — оставлено {'вдох ' if end else ''}{pout + pin:.2f} с"
        tail = PAD_OUT if last else IV_KEEP_SENT[0] + tail_extra
        out.append([s - pin, e + min(tail, room_after(e, math.inf)), why])
    for a, b in zip(out, out[1:]):
        if a[1] > b[0]:
            a[1] = b[0] = (a[1] + b[0]) / 2
    return out, kept, head_short


def face_track(src: Path, work: Path):
    """Положение лица по всему дублю, 2 раза в секунду: (время, x, y) в долях кадра, сглажено."""
    if not FACE_BIN.exists():
        run(["swiftc", "-O", str(ROOT / "tools" / "face.swift"), "-o", str(FACE_BIN)])
    fr = work / "faces" / src.stem.replace(" ", "_")
    fr.mkdir(parents=True, exist_ok=True)
    if not any(fr.iterdir()):
        run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-vf", "fps=2,scale=960:-1", str(fr / "%04d.jpg")])
    res = subprocess.run([str(FACE_BIN), *map(str, sorted(fr.glob("*.jpg")))], capture_output=True, text=True).stdout
    pts = []
    for l in res.splitlines():
        p = l.split()  # путь может содержать пробелы — числа берём с конца
        pts.append(((int(Path(" ".join(p[:-4])).stem) - 1) / 2, float(p[-4]), float(p[-3])))
    if not pts:
        return np.array([0.0]), np.array([0.5]), np.array([0.45])
    t, x, y = map(np.array, zip(*pts))
    k = np.exp(-0.5 * (np.arange(-4, 5) / 2) ** 2)  # гаусс ~1 с: убираем дрожь детектора
    xs = np.convolve(np.pad(x, 4, mode="edge"), k / k.sum(), "valid")
    return t, xs, y


def crop_expr(sw, sh, track, s, e, zoom):
    """Кроп 9:16: на весь кусок одна неподвижная позиция — по лицу в начале куска (первая секунда).
    Камера внутри куска никогда не двигается; меняется только на склейке.
    out_range=tv: телефон пишет полный диапазон яркости (yuvj420p), итог — обычный (как из OBS), чтобы титры,
    сборка и Instagram не гадали; для исходника в обычном диапазоне ничего не меняет (2026-10-13)."""
    t, fx, fy = track
    sc = H * zoom / sh                  # масштаб исходника, после которого кроп = готовый кадр
    SW, SH = round(sw * sc / 2) * 2, round(sh * sc / 2) * 2
    y = min(max(float(np.median(fy)) * SH - FACE_AT * H, 0), SH - H)
    ts = np.arange(s, min(e, s + 1.0) + 0.05, 0.1)
    cx = float(np.median(np.interp(ts, t, fx))) * SW
    x = min(max(cx - W / 2, 0), SW - W)
    return f"scale={SW}:{SH}:flags=lanczos:out_range=tv,crop={W}:{H}:{x:.0f}:{y:.0f}"


def eyes_track(src: Path, work: Path):
    """Середина между глазами в каждом кадре (≈30 раз в секунду), сглажено без запаздывания."""
    if not EYES_BIN.exists():
        run(["swiftc", "-O", str(ROOT / "tools" / "eyes.swift"), "-o", str(EYES_BIN)])
    f = work / "eyes" / (src.stem.replace(" ", "_") + ".txt")
    f.parent.mkdir(exist_ok=True)
    if not f.exists():
        fps = float(Fraction(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=r_frame_rate",
                                   "-of", "csv=p=0", str(src)], capture_output=True, text=True).stdout.strip()))
        with open(f, "w") as fh:
            subprocess.run([str(EYES_BIN), str(src), str(max(1, round(fps / FPS)))], stdout=fh, stderr=subprocess.DEVNULL,
                           check=True)
    t, x, y = np.loadtxt(f, ndmin=2).T
    g = np.arange(0, t[-1] + 1 / FPS, 1 / FPS)          # равномерная сетка кадров; пропуски — интерполяция
    xs, ys = np.interp(g, t, x), np.interp(g, t, y)

    def deadzone(v, dz):  # кадр стоит, пока глаза в пределах dz от точки; вышли — едет за ними от края зоны
        out, held = np.empty_like(v), v[0]
        for i, a in enumerate(v):
            if abs(a - held) > dz:
                held = a - np.sign(a - held) * dz
            out[i] = held
        return out

    xs, ys = deadzone(xs, TRACK_DEADZONE), deadzone(ys, TRACK_DEADZONE)
    r = int(3 * TRACK_SMOOTH * FPS)
    k = np.exp(-0.5 * (np.arange(-r, r + 1) / (TRACK_SMOOTH * FPS)) ** 2)
    k /= k.sum()
    sm = lambda v: np.convolve(np.pad(v, r, mode="edge"), k, "valid")  # гаусс в обе стороны — без отставания
    return g, sm(xs), sm(ys)


def track_crop(sw, sh, eyes, s, e, zoom, cmd: Path, name):
    """Кроп 9:16, который следит за глазами: позиция на каждый кадр через sendcmd."""
    g, ex, ey = eyes
    sc = H * zoom / sh
    SW, SH = round(sw * sc / 2) * 2, round(sh * sc / 2) * 2   # сначала масштаб — шаг сдвига 1 пиксель готового кадра
    ts = np.arange(0, e - s, 1 / FPS)
    xs = np.clip(np.interp(ts + s, g, ex) * SW - W / 2, 0, SW - W).round()
    ys = np.clip(np.interp(ts + s, g, ey) * SH - EYES_AT * H, 0, SH - H).round()
    cmd.write_text("".join(f"{t:.4f} {name} x {x:.0f}, {name} y {y:.0f};\n" for t, x, y in zip(ts, xs, ys)))
    return f"scale={SW}:{SH}:flags=lanczos:out_range=tv,sendcmd=f={cmd},{name}={W}:{H}:{xs[0]:.0f}:{ys[0]:.0f}"


def transcribe(folder: Path, work: Path):
    import mlx_whisper
    words, plan = {}, {"clips": []}
    # .mov/.MOV/.mp4 — телефон пишет расширение заглавными (IMG_9862.MOV)
    for src in sorted(p for p in folder.iterdir() if p.suffix.lower() in (".mov", ".mp4")):
        r = mlx_whisper.transcribe(str(wav_of(src, work)), path_or_hf_repo="mlx-community/whisper-large-v3-turbo",
                                   language="ru", word_timestamps=True)
        ws = [{"w": x["word"].strip(), "s": round(x["start"], 2), "e": round(x["end"], 2)}
              for seg in r["segments"] for x in seg["words"]]
        words[src.name] = ws
        if ws:
            plan["clips"].append({"file": src.name, "from": ws[0]["s"], "to": ws[-1]["e"],
                                  "note": " ".join(x["w"] for x in ws)})
        print(src.name, " ".join(x["w"] for x in ws))
    (work / "words.json").write_text(json.dumps(words, ensure_ascii=False, indent=1))
    p = work / "plan.json"
    if not p.exists():
        p.write_text(json.dumps(plan, ensure_ascii=False, indent=1))
        print("Черновик плана:", p, "— выбрать дубли и границы, потом render")


def resolve(folder: Path, p) -> Path:
    """Путь из плана: от папки ролика, абсолютный или с ~ (folder / абсолютный путь = абсолютный путь)."""
    return folder / Path(p).expanduser()


def lufs(src: Path, s, e):
    """Громкость отрезка исходника [s, e], LUFS (ebur128). Отрезок короче 0,4 с — None."""
    import re
    if e - s < 0.4:
        return None
    err = subprocess.run(["ffmpeg", "-nostats", "-hide_banner", "-ss", f"{s:.3f}", "-t", f"{e - s:.3f}", "-i", str(src),
                          "-vn", "-af", "ebur128=framelog=quiet", "-f", "null", "-"], capture_output=True, text=True).stderr
    m = re.search(r"I:\s+(-?[\d.]+) LUFS", err[err.rfind("Summary:"):])
    return float(m.group(1)) if m and float(m.group(1)) > -70 else None


def loud_stats(path: Path):
    """Громкость файла целиком (ebur128): (I, LUFS; LRA, LU; true peak, дБFS)."""
    import re
    err = subprocess.run(["ffmpeg", "-nostats", "-hide_banner", "-i", str(path), "-vn", "-af",
                          "ebur128=peak=true:framelog=quiet", "-f", "null", "-"], capture_output=True, text=True).stderr
    summ = err[err.rfind("Summary:"):]
    return tuple(float(re.search(pat, summ).group(1)) for pat in
                 (r"I:\s+(-?[\d.]+) LUFS", r"LRA:\s+(-?[\d.]+) LU", r"Peak:\s+(-?[\d.]+) dBFS"))


def probe(src: Path, entries, stream=True):
    cmd = ["ffprobe", "-v", "error"] + (["-select_streams", "v:0"] if stream else []) + \
          ["-show_entries", entries, "-of", "csv=p=0:s=x", str(src)]
    return subprocess.run(cmd, capture_output=True, text=True).stdout.strip()


def frame_size(src: Path):
    """Ширина и высота кадра, как его видят фильтры ffmpeg. Телефон, снятый вертикально, хранит кадр лёжа
    (1920×1080) и флаг поворота на 90° — ffmpeg при чтении поворачивает сам, фильтры получают 1080×1920
    (2026-10-13, IMG_9754.mov: без этого масштаб считался от лежачего кадра и картинка растягивалась втрое)."""
    sw, sh = map(int, probe(src, "stream=width,height").split("x")[:2])
    rot = probe(src, "stream_side_data=rotation").strip("x")
    if rot and round(abs(float(rot))) % 180 == 90:
        sw, sh = sh, sw
    return sw, sh


def face_box(src: Path, t0, t1, cut_bottom=0):
    """Лицо на отрезке [t0, t1] (доли кадра без cut_bottom px снизу), кадры каждые ~0,5 с:
    рамка (x, y, w, h) — медиана за первую секунду (туда ставится кроп), и самая высокая макушка за весь
    отрезок — выше неё верхний край кропа не опускается."""
    if not FACE_BIN.exists():
        run(["swiftc", "-O", str(ROOT / "tools" / "face.swift"), "-o", str(FACE_BIN)])
    d = Path(tempfile.mkdtemp(prefix="face_"))
    ts = np.r_[np.linspace(t0, min(t1, t0 + 1.0), 5), np.arange(t0 + 1.5, t1, 0.5)[:120]]
    for i, t in enumerate(ts):
        run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.3f}", "-i", str(src), "-frames:v", "1",
             "-vf", f"crop=iw:ih-{cut_bottom}:0:0", str(d / f"{i:03d}.png")])
    res = subprocess.run([str(FACE_BIN), *map(str, sorted(d.glob("*.png")))], capture_output=True, text=True).stdout
    rows = np.array([[int(Path(" ".join(l.split()[:-4])).stem), *map(float, l.split()[-4:])]
                     for l in res.splitlines() if l.strip()])
    if not len(rows):
        return None
    first = rows[rows[:, 0] < 5] if (rows[:, 0] < 5).any() else rows
    head = float(np.min(rows[:, 2] - rows[:, 4] / 2 - IV_HAIR * rows[:, 4]))
    return (*np.median(first[:, 1:], axis=0), head)


def interview_frame(z, face):
    """Интервью: срезать подпись Zoom снизу, видео во всю ширину 1080×564, на y = IV_Y, сверху и снизу чёрное.
    Крупность z > 1 — кроп вокруг лица того же размера на том же месте; макушка не режется верхним краем
    за весь кусок (человек наклоняется вперёд — берём самую высокую макушку)."""
    SW, SH = round(IV_W * z / 2) * 2, round(IV_H * z / 2) * 2
    f = f"crop=iw:ih-{IV_CUT_BOTTOM}:0:0,scale={SW}:{SH}:flags=lanczos"
    if (SW, SH) != (IV_W, IV_H):
        fx, fy, fw, fh, head = face if face is not None else (0.5, 0.45, 0.2, 0.35, 0.0)
        x = min(max(fx * SW - IV_W / 2, 0), SW - IV_W)
        top = head * SH - IV_HEAD_MARGIN * IV_H  # верхний край кропа — не ниже макушки с запасом
        y = min(max(min(fy * SH - IV_H / 2, top), 0), SH - IV_H)
        f += f",crop={IV_W}:{IV_H}:{x:.0f}:{y:.0f}"
    return f + f",pad={W}:{H}:0:{IV_Y}:black"


def foreign_frames(plan, folder: Path):
    """Интервалы исходника, где в кадре не тот, кто нужен (plan["only"]): [(s, e)]."""
    o = plan.get("only")
    if not o:
        return []
    return [(x["s"], x["e"]) for x in json.loads(resolve(folder, o["file"]).read_text()) if x["who"] != o["who"]]


def render(folder: Path, work: Path, track_eyes=True, plan_name="plan.json"):
    cmds = Path(tempfile.mkdtemp(prefix="montazh_"))  # путь без пробелов — для sendcmd в фильтрах
    plan = json.loads((work / plan_name).read_text())
    suffix = Path(plan_name).stem[len("plan"):]       # plan_вариант.json → итог_вариант.mp4
    interview = plan.get("format") == "interview"
    # "track": false в плане — неподвижный кадр как режим этого ролика (то же, что --static, но итог называется
    # как обычно: итог.mp4, его читают следующие этапы). --static без записи в плане — вариант для сравнения.
    static_plan = plan.get("track") is False
    track_eyes = track_eyes and not static_plan
    speed = float(plan.get("speed", 1.0))
    porog = float(plan.get("porog", POROG))  # порог речи над фоном комнаты, дБ (телефон без петлички — ниже 20)
    # время в итоге после ускорения: кадр I собранного ролика показывается кадром round(I / speed) (fps=30, round near)
    t_fin = lambda t: round(round(t * FPS) / speed) / FPS
    bad = foreign_frames(plan, folder)
    # слова — чтобы знать, где кончается предложение (после него на склейке остаётся вдох)
    wf = work / "слова_кусков.json"
    wf = wf if wf.exists() else (resolve(folder, plan["words"]) if plan.get("words") else None)
    words = load_words(wf) if interview and wf else {}
    inputs, parts, log, warn, notes = [], [], [], [], []
    aparts = []  # звуковые цепочки кусков отдельно — для замера собранного звука ("flat_gain")
    flat = plan.get("flat_gain")
    if flat is not None and interview:
        sys.exit('"flat_gain" — только для говорящей головы: у интервью свой звук (выравнивание кусков, IV_TP)')
    clip_lu = {}
    if interview and not wf:
        warn.append("нет слов (mychanie → слова_кусков.json или \"words\" в плане): все склейки — как внутри фразы")
    envs = {}
    n_in = 0
    k = 0
    zi = -1
    static_crop = (None, "")
    t_out = 0.0

    def wav_clip(c):
        wav = c.get("wav") or plan.get("wav")
        wav = resolve(folder, wav) if wav else wav_of(resolve(folder, c["file"]), work)
        if wav not in envs:
            envs[wav] = envelope(wav, porog)
        return wav

    def iv(ci, extra=0.0):
        c, wav = plan["clips"][ci], wav_clip(plan["clips"][ci])
        cf, ct = c.get("cut_from"), c.get("cut_to")
        return pieces_iv(envs[wav], level(wav, porog), audio(wav), c.get("from", cf), c.get("to", ct), cf, ct, c.get("hum", []),
                         words.get(c["file"]) or words.get("*") or [], ci == 0, ci == len(plan["clips"]) - 1,
                         c.get("cut", []), extra)

    pre = {}
    if interview:
        pre = {ci: iv(ci) for ci in range(len(plan["clips"]))}
        # между кусками записи — тоже вдох 0,30 с: если у следующего куска первое слово впритык (жёсткий край, слова
        # слиты: «места. | надо»), недостающая тишина берётся после последнего слова предыдущего куска
        for ci in range(len(plan["clips"]) - 1):
            if pre[ci + 1][2] > 1e-3:
                pre[ci] = iv(ci, pre[ci + 1][2])
    for ci, c in enumerate(plan["clips"]):
        src = resolve(folder, c["file"])
        dur = float(probe(src, "format=duration", stream=False))
        sw, sh = frame_size(src)
        wav = wav_clip(c)
        cf, ct = c.get("cut_from"), c.get("cut_to")
        hums = c.get("hum", []) + c.get("cut", [])  # края мычания и вырезанных фраз — жёсткие
        ekran = not interview and bool(c.get("ekran"))  # экран, снятый телефоном: лица нет — ни слежения, ни поиска лица
        if interview:
            raw, kept, _ = pre[ci]
            notes += kept
        else:
            raw = [[s, e, ""] for s, e in pieces_hum(with_keep(envs[wav], c.get("keep")), c.get("from", cf),
                                                     c.get("to", ct), cf, ct, hums)]
            if raw and c.get("tail_to") is not None:  # хвост: последний кусок клипа кончается не раньше этой секунды
                raw[-1][1] = max(raw[-1][1], float(c["tail_to"]))
        # границы — ровно по кадрам: иначе каждый кусок округляется при сборке и склейки в склейки.txt
        # уезжают от настоящих на 0,05–0,27 с (зритель, 2026-09-28). Жёсткий край и край мычания — внутрь куска.
        ps = []
        for s0, e0, why in raw:
            s, e = round(s0 * FPS) / FPS, round(min(e0, dur) * FPS) / FPS
            # допуск 1 мс: край в плане записан с 4 знаками (1889.6667 — это кадр 56690/30), не сдвигать его на кадр
            lo_lim = max([cf if cf is not None else -1] + [b for a, b, *_ in hums if b <= s0 + 1e-3])
            hi_lim = min([ct if ct is not None else math.inf] + [a for a, b, *_ in hums if a >= e0 - 1e-3])
            if s < lo_lim - 1e-3:
                s = math.ceil(lo_lim * FPS - 0.01) / FPS
            if e > hi_lim + 1e-3:
                e = math.floor(hi_lim * FPS + 0.01) / FPS
            ps.append([s, e, why])
        ps = [p for p in ps if p[1] - p[0] >= 1 / FPS]
        if not ps:
            continue
        if interview:
            # быстрый переход к куску (одна длинная запись): время внутри фильтров — от base
            base = max(0.0, math.floor(ps[0][0] - 2))
            src_fps = float(Fraction(probe(src, "stream=r_frame_rate")))
            inputs += ["-ss", f"{base:.3f}", "-i", str(src)]
        else:
            base = 0.0
            track = None if ekran else eyes_track(src, work) if track_eyes else face_track(src, work)
            inputs += ["-i", str(src)]
        ii = n_in
        n_in += 1
        if interview:  # громкость этого куска записи (по его кускам речи) — для выравнивания между кусками
            ls = [(lufs(src, s, e), e - s) for s, e, _ in ps]
            ls = [(l, d) for l, d in ls if l is not None]
            if ls:
                clip_lu[ci] = (10 * math.log10(sum(d * 10 ** (l / 10) for l, d in ls) / sum(d for _, d in ls)),
                               sum(d for _, d in ls))
        for s, e, why in ps:
            if ekran:  # экран — кадр целиком, крупность 1,0; чередование лица идёт мимо него
                new_plan, z = False, 1.0
            else:
                new_plan = k == 0 or e - s >= ZOOM_MIN_PIECE
                if new_plan:  # короткий кусок крупность не меняет — иначе прыжок на полсекунды
                    zi += 1
                z = ZOOMS[zi % len(ZOOMS)]
            note = ""
            # пометка экрана — перед «zoom»: titry.py берёт крупность из конца строки
            mark = "экран (кадр целиком)  " if ekran else ""
            if interview:
                # чужой кадр на краю куска (Zoom переключает с опозданием) — стоп-кадр ближайшего своего, звук как есть
                vs, ve = s, e
                for a, b in bad:
                    if a <= vs < b:
                        vs = b
                    if a < ve <= b:
                        ve = a
                if vs >= ve:
                    sys.exit(f"{c['file']} {s:.2f}–{e:.2f}: в кадре только чужой — нужны другие границы")
                for a, b in bad:
                    if vs < b and a < ve:
                        warn.append(f"чужой кадр в середине куска {s:.2f}–{e:.2f}: {a:.2f}–{b:.2f} ({b - a:.2f} с) — не спрятан")
                half = 0.5 / src_fps  # полкадра исходника: fps=30 берёт ближайший кадр — не зацепить чужой
                ts, te = (vs + half if vs > s else s), (ve - half if ve < e else e)
                # живые кадры — по сетке 30 fps от base; стоп-кадр добивает до краёв куска ровно по кадрам
                g0 = math.ceil((ts - base) * FPS - 1e-6) / FPS
                g1 = math.ceil((te - base) * FPS - 1e-6) / FPS
                face = face_box(src, base + g0 + 0.05, base + g1 - 0.05, IV_CUT_BOTTOM) if z != 1 else None
                freeze = ""
                if vs > s or ve < e:
                    d0, d1 = round(g0 - (s - base), 4), round((e - base) - g1, 4)
                    freeze = f"tpad=start_mode=clone:start_duration={d0:.4f}:stop_mode=clone:stop_duration={d1:.4f},"
                    note = "".join([f"  стоп-кадр {d0:.2f} с в начале" if d0 > 0 else "",
                                    f"  стоп-кадр {d1:.2f} с в конце" if d1 > 0 else ""])
                n = round((e - s) * FPS)
                vchain = (f"[{ii}:v]fps={FPS},trim={g0 - 0.001:.4f}:{g1 - 0.001:.4f},setpts=PTS-STARTPTS,{freeze}"
                          f"{interview_frame(z, face)},tpad=stop_mode=clone:stop_duration=0.2,trim=end_frame={n},"
                          f"setsar=1[v{k}];")
            else:
                if ekran:  # вписать кадр целиком (телефон, 1080×1920 — как есть), полосы, если пропорции другие
                    crop = (f"scale={W}:{H}:force_original_aspect_ratio=decrease:flags=lanczos:out_range=tv,"
                            f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:black")
                elif track_eyes:
                    crop = track_crop(sw, sh, track, s, e, z, cmds / f"c{k}.txt", f"crop@c{k}")
                elif new_plan or static_crop[0] != src:
                    crop = crop_expr(sw, sh, track, s, e, z)
                    static_crop = (src, crop)
                else:  # неподвижный кадр: кусок без смены крупности остаётся в кадре предыдущего — иначе фон
                    crop = static_crop[1]  # прыгает на 10–20 px без смены плана («технология | интеллект», 2026-10-13)
                vchain = f"[{ii}:v]trim={s:.3f}:{e:.3f},setpts=PTS-STARTPTS,{crop},fps={FPS},setsar=1[v{k}];"
            achain = (f"[{ii}:a]atrim={s - base:.4f}:{e - base:.4f},asetpts=PTS-STARTPTS,"
                      f"aformat=sample_rates=48000:channel_layouts=stereo,"
                      + (f"volume=@G{ci}@dB," if interview else "") +
                      f"afade=t=in:d=0.01,afade=t=out:st={max(0, e - s - 0.015):.3f}:d=0.015[a{k}];")
            parts.append(vchain + achain)
            aparts.append(achain)
            log.append(f"{t_fin(t_out):6.2f}  {c['file']}  {s:6.2f}–{e:6.2f}  {mark}zoom {z}{note}"
                       + (f"  ← {'начало' if k == 0 else why}" if interview else ""))
            t_out += e - s
            k += 1
    fc = "".join(parts) + "".join(f"[v{i}][a{i}]" for i in range(k)) + \
         f"concat=n={k}:v=1:a=1[{'v' if speed == 1 else 'vc'}][a0];"
    if speed != 1:
        # ускорение всего ролика после склеек и до громкости (Арон, 2026-09-30): видео — время кадров / speed
        # (settb=AVTB — без округления меток до кадра), обратно в 30 fps; звук — atempo, тембр тот же
        fc += f"[vc]settb=AVTB,setpts=(PTS-STARTPTS)/{speed},fps={FPS}[v];[a0]atempo={speed}[a1];"
    pre = "a0" if speed == 1 else "a1"
    sound = ""
    if flat is None:
        fc += f"[{pre}]loudnorm=I=-14:TP={IV_TP if interview else -1.5}:LRA=9[a]"
    else:
        # ровное усиление (2026-10-13, ролик «извозчики или лошади»): первый проход — собранный звук как есть
        # (те же куски, фейды и ускорение) во временный wav и его громкость; второй — одно усиление на весь ролик
        # и ограничитель пиков (упреждение 5 мс, отпускание 50 мс, задержка скомпенсирована)
        tmp = cmds / "sobrano.wav"
        afc = "".join(aparts) + "".join(f"[a{i}]" for i in range(k)) + f"concat=n={k}:v=0:a=1[a0]" + \
              (f";[a0]atempo={speed}[a1]" if speed != 1 else "")
        run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", afc, "-map", f"[{pre}]",
             "-c:a", "pcm_s32le", str(tmp)])
        i_in, lra_in, tp_in = loud_stats(tmp)
        # "flat_gain_db" — усиление закреплено числом: правка, которая добавляет тишину (хвост), сдвигает замер на 0,1 LU,
        # и весь звук ролика, уже разложенного по кадрам, стал бы другим (2026-10-17: +11,60 → +11,70 дБ — AAC дал
        # выброс −0,3 dBTP на 0,42 с, при +11,60 −1,9)
        fixed = plan.get("flat_gain_db")
        gain = float(fixed) if fixed is not None else float(flat) - i_in
        x = np.frombuffer(wave.open(str(tmp)).readframes(10 ** 10), np.int32).reshape(-1, 2)
        over = 20 * np.log10(np.abs(x).max(1) / 2.0 ** 31 + 1e-12) + gain - FLAT_CEIL  # выше потолка после усиления
        idx = np.flatnonzero(over > 0)
        places = 1 + int((np.diff(idx) > 0.05 * 48000).sum()) if len(idx) else 0  # ближе 50 мс — одно место
        fc += (f"[{pre}]volume={gain:.2f}dB,alimiter=limit={10 ** (FLAT_CEIL / 20):.5f}:attack=5:release=50:asc=0:"
               f"level=0:latency=1[a]")
        sound = (f"ровное усиление {gain:+.1f} дБ (собранный звук {i_in:.1f} LUFS, LRA {lra_in:.1f}, пик {tp_in:.1f} "
                 + (f"дБFS, закреплено в плане: flat_gain_db {float(fixed):g})" if fixed is not None else
                    f"дБFS → расчёт {float(flat):g} LUFS)") + f"; выше потолка {FLAT_CEIL:g} дБFS — {places} мест, "
                 f"{100 * (over > 0).mean():.2f} % сэмплов, до {max(0.0, float(over.max())):.1f} дБ: срезает ограничитель")
    if interview:  # кусок записи, который громче/тише всего ролика больше чем на IV_LEVEL_LU, — к общей громкости
        tot = sum(d for _, d in clip_lu.values())
        ref = 10 * math.log10(sum(d * 10 ** (l / 10) for l, d in clip_lu.values()) / tot) if tot else 0
        for ci in range(len(plan["clips"])):
            l = clip_lu.get(ci, (ref, 0))[0]
            g = ref - l if abs(ref - l) > IV_LEVEL_LU else 0.0
            fc = fc.replace(f"@G{ci}@", f"{g:.2f}")
            if ci in clip_lu:
                notes.append(f"громкость куска записи {ci + 1}: {l:.1f} LUFS (ролик {ref:.1f})"
                             + (f" → усиление {g:+.1f} дБ" if g else " — в пределах 2 LU, не трогаю"))
    out = work / (("итог" if track_eyes or interview or static_plan else "итог_статичный") + suffix + ".mp4")
    run(["ffmpeg", "-v", "error", "-stats", "-y", *inputs, "-filter_complex", fc, "-map", "[v]", "-map", "[a]",
         "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", str(out)])
    total = f"{t_fin(t_out):.2f} с, склеек: {k - 1}" + \
            (f" (ускорение {speed:g}: время склеек — в итоге после ускорения; до ускорения {t_out:.2f} с)"
             if speed != 1 else "")
    if sound:  # громкость итога — уже после AAC
        i_out, lra_out, tp_out = loud_stats(out)
        sound += f". Итог: {i_out:.1f} LUFS, LRA {lra_out:.1f}, пик {tp_out:.1f} dBTP"
    (work / f"склейки{suffix}.txt").write_text("\n".join(log) + f"\n\nИтого: {total}\n"
                                               + (f"Звук: {sound}\n" if sound else "")
                                               + "".join(f"Оставлено: {w}\n" for w in notes)
                                               + "".join(f"Внимание: {w}\n" for w in warn))
    print("\n".join(log), f"\nИтого {total} → {out}", *([f"Звук: {sound}"] if sound else []), *notes, *warn, sep="\n")


def whisper(x, words=False):
    import mlx_whisper
    return mlx_whisper.transcribe(np.asarray(x, np.float32), path_or_hf_repo="mlx-community/whisper-large-v3-turbo",
                                  language="ru", word_timestamps=words, condition_on_previous_text=False)


def norm_words(t):
    """Слова без регистра, знаков и ё — чтобы сравнить две расшифровки."""
    import re
    return re.findall(r"[а-яa-z0-9]+", t.lower().replace("ё", "е"))


def mychanie(folder: Path, work: Path, plan_name="plan.json"):
    """Кандидаты мычания в кусках плана (Арон, 2026-09-30: «вырежи мычание»). Ничего не режет — печатает улики:
    1) звонкий ровный звук ≥ HUM_VOICED с («м-м», «э-э», «и-и-и», тянущаяся гласная),
    2) ровный шум без гармоник ≥ HUM_NOISE с вплотную к слову («с-с-с»; вдох в тишине — не кандидат, это тишина),
    3) звук, который перерасшифровка куска не покрыла словами (≥ 0,3 с), и растянутые слова.
    Для каждого места: расшифровка его одного (слово или нет) и окна ±2,5 с как есть и без него (слова не теряются?).
    Решение — за монтажёром: спектр + эти улики → "hum" в клипе. Перерасшифровка кусков → слова_кусков.json."""
    sr = 16000
    plan = json.loads((work / plan_name).read_text())
    allw, found = {}, []
    for ci, c in enumerate(plan["clips"]):
        src = resolve(folder, c["file"])
        wav = c.get("wav") or plan.get("wav")
        wav = resolve(folder, wav) if wav else wav_of(src, work)
        x, v = audio(wav), envelope(wav)
        cf, ct = c.get("cut_from"), c.get("cut_to")
        lo = c.get("from", cf) - SEARCH if cf is None else cf
        hi = c.get("to", ct) + SEARCH if ct is None else ct
        seg = lambda a, b: x[int(a * sr): int(b * sr)]
        r = whisper(seg(lo, hi), words=True)
        ws = [{"w": w["word"].strip(), "s": round(lo + w["start"], 2), "e": round(lo + w["end"], 2)}
              for s in r["segments"] for w in s["words"]]
        allw.setdefault(c["file"], []).extend(ws)
        print(f"\n=== кусок {ci + 1}: {lo:.2f}–{hi:.2f}\n{' '.join(w['w'] for w in ws)}")
        i0, n = int(round(lo / HOP)), int(round((hi - lo) / HOP))
        vv = v[i0:i0 + n].copy()
        h, fl = harmonicity(x, lo, hi), spec_flux(x, lo, hi)
        breath = breaths_to_silence(vv.copy(), h, level(wav)[i0:i0 + n])

        def merged(m):  # отрезки с дырками до 40 мс
            out = []
            for s, e in runs_of(m):
                if out and s - out[-1][1] <= 4:
                    out[-1][1] = e
                else:
                    out.append([s, e])
            return out

        cand = [("звонкий ровный", s, e) for s, e in merged(vv & (h > HUM_HARM) & (fl < HUM_FLUX))
                if (e - s) * HOP >= HUM_VOICED]
        cand += [("шум у слова", s, e) for s, e in merged(vv & (h < BREATH_H) & (fl < HUM_FLUX))
                 if (e - s) * HOP >= HUM_NOISE and (vv[max(0, s - 8):s].any() or vv[e:e + 8].any())
                 and not any(bs <= s and e <= be for bs, be in breath)]
        cov = np.zeros(n, bool)
        for w in ws:
            cov[max(0, int((w["s"] - lo) / HOP)): max(0, int((w["e"] - lo) / HOP))] = True
        cand += [("звук без слов", s, e) for s, e in merged(vv & ~cov) if (e - s) * HOP >= 0.3]
        for w in ws:
            d = w["e"] - w["s"]
            if d > max(0.55, 0.09 * len(w["w"].strip(".,?!…–-")) + 0.25):
                print(f"  растянутое слово «{w['w']}» {w['s']:.2f}–{w['e']:.2f} ({d:.2f} с) — смотреть спектр")
        for bs, be in breath:
            print(f"  вдох {lo + bs * HOP:.2f}–{lo + be * HOP:.2f} — для пауз это тишина")
        for a, b, *note in c.get("hum", []):
            print(f"  в плане hum {a:.2f}–{b:.2f} {note[0] if note else ''}")
        for kind, s, e in sorted(cand, key=lambda q: q[1]):
            a, b = lo + s * HOP, lo + e * HOP
            z = np.zeros(int(0.3 * sr), np.float32)
            alone = whisper(np.r_[z, seg(a, b), z])["text"].strip()
            w0, w1 = max(lo, a - 2.5), min(hi, b + 2.5)
            p1, p2 = seg(w0, a).copy(), seg(b, w1).copy()
            f1, f2 = min(int(0.012 * sr), len(p1)), min(int(0.012 * sr), len(p2))
            p1[len(p1) - f1:] *= np.linspace(1, 0, f1)
            p2[:f2] *= np.linspace(0, 1, f2)
            t_as, t_wo = whisper(seg(w0, w1))["text"].strip(), whisper(np.r_[p1, p2])["text"].strip()
            same = norm_words(t_as) == norm_words(t_wo)
            found.append({"кусок": ci + 1, "что": kind, "от": round(a, 2), "до": round(b, 2), "одно": alone,
                          "окно": t_as, "без него": t_wo, "слова целы": same})
            print(f"  {kind:15s} {a:8.2f}–{b:8.2f} ({b - a:.2f} с)  одно: «{alone[:40]}»  без него слова "
                  f"{'целы' if same else 'МЕНЯЮТСЯ'}\n      как есть: {t_as}\n      без него: {t_wo}")
    (work / "слова_кусков.json").write_text(json.dumps(allw, ensure_ascii=False, indent=1))
    (work / "мычание.json").write_text(json.dumps(found, ensure_ascii=False, indent=1))
    print(f"\n→ {work / 'слова_кусков.json'}, {work / 'мычание.json'}. Подтверждённое — в клип: \"hum\": [[от, до, \"что\"]]")


def slova(work: Path, suffix=""):
    """Слова готового итога со временем → итог_слова.json (титровщик, сборщик). После каждой пересборки — заново."""
    import mlx_whisper
    # без опоры на прошлый текст (2026-09-30): с ней whisper тянет шаблон («Первое – это…» → «И третье – это
    # отсутствие», которого нет) и в конце ролика выдумывает целые фразы
    r = mlx_whisper.transcribe(str(work / f"итог{suffix}.mp4"), path_or_hf_repo="mlx-community/whisper-large-v3-turbo",
                               language="ru", word_timestamps=True, condition_on_previous_text=False)
    # whisper на тишине в конце дописывает «Продолжение следует...» (№3 интервью, 2026-09-30) — в титры не пускать
    fake = {"продолжение следует", "субтитры создавал dimatorzok", "субтитры сделал dimatorzok", "спасибо за просмотр",
            "редактор субтитров", "удачи"}
    # выдуманный кусок: слова без длительности (№6 интервью, 2026-09-30: «Вы Hermael Элина…» — 20 слов за 0,1 с в конце)
    empty = lambda seg: seg["words"] and np.mean([x["end"] - x["start"] < 0.03 for x in seg["words"]]) > 0.5
    segs = [seg for seg in r["segments"] if " ".join(norm_words(seg["text"])) not in fake and not empty(seg)]
    ws = [{"w": x["word"].strip(), "s": round(x["start"], 2), "e": round(x["end"], 2)}
          for seg in segs for x in seg["words"]]
    (work / f"итог_слова{suffix}.json").write_text(json.dumps(ws, ensure_ascii=False, indent=1))
    print(" ".join(x["w"] for x in ws))


if __name__ == "__main__":
    folder = Path(sys.argv[1]).expanduser().resolve()
    step = sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith("--") else "render"
    plan_name = sys.argv[sys.argv.index("--plan") + 1] if "--plan" in sys.argv else "plan.json"
    work = folder / "монтаж"
    work.mkdir(exist_ok=True)
    if step == "transcribe":
        transcribe(folder, work)
    elif step == "slova":
        slova(work, Path(plan_name).stem[len("plan"):])
    elif step == "mychanie":
        mychanie(folder, work, plan_name)
    else:
        render(folder, work, track_eyes="--static" not in sys.argv, plan_name=plan_name)
