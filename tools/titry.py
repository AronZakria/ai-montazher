"""Титры ролика: субтитры по словам (точно по кадрам) + заголовки. Рисует прозрачный слой .mov для sborka.py.

    python3 tools/titry.py <папка ролика>        → <папка>/монтаж/титры.mov (прозрачный, длина и частота кадров = итог.mp4)

Вход: <папка>/монтаж/итог_слова.json — слова с временем (whisper по итог.mp4, пересчитать после любой пересборки итога),
      <папка>/монтаж/титры.json — {"zagolovki": [{"text": "…", "sub": "…", "from": 0, "to": 14.2}],
                                   "ubrat": [[31.1, 45.2]],   // где субтитры не нужны (Арон читает с экрана, текст уже на экране)
                                   "pravki": [["как распознано", "как должно быть"]],
                                   "vremya": [["слово", 1.88, 1.74]],  // начало слова по whisper → верное (по спектру)
                                   "razryvy": [["будет", 7.38]]}  // после этого слова (начало по итог_слова.json) — новая строка
Раскладки:
  по умолчанию — говорящая голова: субтитры на тёмной плашке (центр 1420, ниже рта), заголовок-хук на плашке (центр 360);
  "layout": "interview" — горизонтальное видео в вертикальном кадре (montazh.py "format": "interview", Арон, 2026-09-30):
      чёрный кадр, видео в рамке y 578–1142; весь ролик сверху рубрика и заголовок, под видео субтитры — всё на чёрном, без плашек.
      {"layout": "interview", "rubrika": "СОВЕТ ОСНОВАТЕЛЯ КОМПАНИИ",
       "zagolovok": {"stroki": ["СКОЛЬКО ПРОСИТЬ", "НА СОБЕСЕДОВАНИИ"], "zoloto": ["СКОЛЬКО ПРОСИТЬ"]}, "pravki": […]}
      zoloto — слова/сочетания из строк, которые золотые; остальное белое.
  "layout": "kvadrat" — подкаст: видео на чёрном кадре (сборка kvadrat.py, 2026-10-12), рамка видео — из plan.json:
      "video_y": 416, "video_h": 960 (без них — первый квадрат 1080×1080 на y 330–1410). Заголовок весь ролик на чёрном
      поле над видео, субтитры на чёрной полосе под видео — без плашек, на видео ничего; где именно — kv_geometry():
      видео 416–1376 → заголовок под линией ленты (y 285), центр блока 352, субтитры 1438; квадрат 330–1410 → 275 и 1455.
      Склейки берутся из склейки.txt: слово не звучит через склейку, субтитр меняется ровно на её кадре.
      {"layout": "kvadrat", "zagolovok": {"stroki": ["ПРОДАЛ СЕРВИС", "ЗА МИЛЛИОН ЧЕРЕЗ 5 ДНЕЙ"], "zelenoe": ["МИЛЛИОН"]}, "pravki": […]}
      zelenoe — деньги (слова/сочетания из строк), зелёные; остальное белое.
      Правила квадрата в другой раскладке включаются по одному: "skleyki": true (склейки), "vdoh": true (вдох и короткое
      слово через паузу — не начало фразы), "skorost": true (фраза от 20 знаков в секунду сливается с соседней).
  "layout": "yaping" — япинг (формат Jessi Jean, Арон, 2026-10-13; мерки — docs/япинг.md): человек
      говорит в камеру, на экране только заголовок-хук в начале и субтитры рядом с лицом. Тонкий шрифт с засечками
      (PT Serif Regular), белый, строчными, без точек и запятых (вопросительный знак остаётся), без плашки и обводки,
      тень — мягкое затемнение под строкой, не контур; субтитр — одна строка до 5 слов, 26 знаков и 660 px. Где стоят
      строки, зависит от того, как человек сел (подбородок, петличка), — высоты задаёт титры.json ролика, по замеру режиссёра:
      {"layout": "yaping", "zagolovok": {"stroki": ["мне предложили полмиллиона", "за неделю работы с ИИ"], "y": 1131, "do": 5.63},
       "vysota": {"1.0": 1214, "1.15": 1260}, "vstavki": [{"ot": 50.07, "do": 62.57, "y": 1457, "smeny": [52.77, 54.77, 57.33, 60.2]}],
       "ubrat": [[0, 5.63]], "shrift": {"nachertanie": "Regular", "kegl": 46, "kegl_zagolovka": 56}, "pravki": […]}
      zagolovok.y — середина букв первой строки (следующие — ниже на шаг строк), стоит с "ot" (0) до "do" секунд;
      vysota — середина букв субтитра для каждой крупности плана из склейки.txt («zoom 1.15»; одно число — одна высота
      на весь ролик): строка меняет высоту ровно на кадре склейки, вместе с планом;
      vstavki — вставки на весь кадр: с "ot" до "do" субтитр стоит на высоте "y" (под карточкой); края вставки — разрыв
      фразы и смена высоты на этом кадре; "smeny" — секунды, где меняется картинка вставки: смена субтитра рядом
      ставится на этот кадр, склейки итога под вставкой не в счёт; "plotnost" — тень под вставкой (на тёмном фоне — 0);
      "cvet" у вставки — цвет строки под ней; cvet — цвет текста на весь ролик ("#1A1E21" или [r, g, b], без него белый),
      у заголовка может быть свой "cvet";
      shrift — шрифт одной строкой: "file" (путь или имя из tools/fonts), "nachertanie" (имя или номер в файле),
      "ves" (вес переменного шрифта), "kegl", "kegl_zagolovka"; ten — тень: "blur", "plotnost" (0 — без тени), "dy";
      zelenoe — слова субтитров, которые зелёные (деньги). Склейки: слово через склейку не звучит, смена субтитра — на её
      кадре; фразу рвёт только склейка со сменой крупности. В отрезках ubrat субтитра нет ни в одном кадре.
Сетка времени — кадры самого итог.mp4 (подкаст — 25 в секунду, остальное — 30).
Правила — docs/титры.md. Шрифт — tools/fonts/Montserrat (OFL), субтитры Medium, заголовки SemiBold;
япинг — системный PT Serif Regular (/System/Library/Fonts/Supplemental/PTSerif.ttc, есть в каждой macOS) или "shrift".
"""
import functools, json, re, subprocess, sys, tempfile
from fractions import Fraction
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, str(Path(__file__).parent / "ekran"))
from zona import W, H, SAFE, ICONS, ICONS_FROM

FPS = 30                             # сетка кадров; в main() берётся из самого итог.mp4 (подкаст собран в 25 кадрах в секунду)
FONT = str(Path(__file__).parent / "fonts" / "Montserrat[wght].ttf")
SLOVAR = Path(__file__).parent.parent / "docs" / "словарь_титров.json"  # общий словарь исправлений
SUB_SIZE, SUB_WEIGHT = 38, 500       # субтитры: Montserrat Medium; было 62 — Арон: «сильно меньше, на ~40 %» (2026-09-28)
TITLE_SIZE, TITLE_WEIGHT = 66, 600   # заголовки: Montserrat SemiBold
SUB_Y = 1420                         # центр плашки субтитров: ниже рта (низ лица ≤ ~1300), у нижнего края зоны (1500)
TITLE_Y = 360                        # центр полосы заголовка (220–700), над головой
MAX_WORDS, MAX_CHARS = 6, 34         # в одной фразе: шрифт меньше — фраза чуть длиннее; но всегда ОДНА строка
LEAD = 0.05                          # фраза появляется на 50 мс раньше слова — глаз успевает к звуку
# «раньше слова» = раньше ЗВУКА слова: whisper после паузы ставит начало слова в тишину, до 0,44 с раньше голоса
# (интервью с гостем, 2026-09-30). Начало фразы в тишине → берём начало звука по огибающей итога.
VOICE_DB, VOICE_FLOOR = -50, 8       # «звучит»: выше пола тишины ролика (5-й перцентиль) на 8 дБ и не тише −50 дБ
VOICE_MAX = 0.45                     # сдвиг только вперёд и не дальше (~0,4; самый большой найденный — 0,44 с, №6 «что»):
                                     # нет звука дальше — время слова не трогаем, предупреждаем
VOICE_LOUD, VOICE_RISE = 12, 0.15    # начало звука — начало речи, а не вдоха: за 0,15 с без провала поднимается на 12 дБ над порогом
PAUSE_GAP = 0.05                     # тишина не короче — пауза (короче — смычка согласного)
BLANK_MAX = 0.25                     # голос без субтитра дольше — предупреждение (время слова неверно)
MIN_SHOW = 0.4                       # фраза держится не меньше
HOLD_AFTER = 0.25                    # после последнего слова фразы, если дальше пауза/склейка
GAP_HOLD = 0.3                       # пустой экран между фразами короче — мигание: прошлая фраза держится до следующей
# Квадрат (подкаст, паузы вырезаны; зритель, 2026-10-12: «субтитр гаснет на треть секунды — мигание», «не успеть прочитать»):
GAP_HOLD_KV = 0.5                    # там пауз длиннее 0,6–0,7 с не бывает: пустой экран короче 0,5 с — тоже мигание
END_HOLD = 1.0                       # до конца ролика осталось меньше — последняя фраза стоит до последнего кадра
READ_CPS = 20                        # от стольких знаков в секунду фразу без звука не успеть прочитать — сливаем с соседней
COORD = {"и", "а", "но", "или", "либо", "да", "зато"}  # после запятой с них начинается новая часть предложения — через неё не сливаем
GLUE = {"и", "в", "во", "на", "с", "со", "к", "ко", "о", "об", "у", "по", "за", "из", "от", "до", "не", "а", "но", "что", "как", "я", "ты", "потому", "чтобы", "если",
        "ради", "для", "без", "про", "через", "при", "под", "над", "перед", "между", "весь", "всё", "все", "этот", "эта", "эту", "это",
        "свой", "свою", "мой", "мою", "такие", "такой", "вот", "очень", "самый", "одну", "один", "было", "будет",
        "ну", "или", "либо"}  # не висят в конце строки
# прилагательное/причастие не отрывается от следующего слова («сегодняшнего | дня», «эту дохлую | лошадь»): по окончанию,
# слова от 5 букв; мягко — вес против ровности строк (сумма квадратов длин)
ADJ = re.compile(r"\w{2,}(ые|ие|ый|ий|ая|яя|ое|ее|ого|его|ому|ему|ым|им|ых|их|ую|юю|ном)$")
# число не отрывается от того, что оно считает («Примерно за пять | часов я его собрал» → «Примерно за пять часов |
# я его собрал», Визионеры, 2026-10-12): цифры и числительные — тот же мягкий штраф, что после прилагательного
NUM = re.compile(r"(\d[\d.,–-]*|один|одна|одно|одну|два|две|три|четыре|пять|шесть|семь|восемь|девять|десять|сто|"
                 r"тысяч[аи]?|миллион(а|ов)?|миллиард(а|ов)?|несколько|пару)$")
# новая группа начинается с предлога или союза — только они, не все служебные: «вот», «это», «очень», «я» висеть в конце
# не должны, но группу не начинают («Происходит такая | вот огранка» — плохо; «Происходит | такая вот огранка», 2026-09-30)
GROUP = {"и", "в", "во", "на", "с", "со", "к", "ко", "о", "об", "у", "по", "за", "из", "от", "до", "а", "но", "что", "как", "потому",
         "чтобы", "если", "ради", "для", "без", "про", "через", "при", "под", "над", "перед", "между", "или", "либо"}
ADJ_CUT, GROUP_CUT = 200, 100   # штраф: разрез после прилагательного; бонус: разрез перед предлогом/союзом (новая группа)
# местоимение, которое стоит ПЕРЕД своим сказуемым, не остаётся в конце строки («ни дизайнеры мне | для этого не
# понадобились» → «ни дизайнеры | мне для этого не понадобились»; зритель, 2026-10-12). После глагола оно на месте
# («я собрал его», «помогает тебе») — глагол узнаём по окончанию; после предлога тоже («у меня», «для вас»).
# При делении куска считается как служебное слово в конце строки
PRON = {"мне", "тебе", "нам", "вам", "меня", "тебя", "нас", "вас"}
PREP = {"в", "во", "на", "с", "со", "к", "ко", "о", "об", "обо", "у", "по", "за", "из", "от", "до", "для", "без", "про", "через",
        "при", "под", "над", "перед", "между", "ради"}
VERB = re.compile(r"\w+(л|ла|ло|ли|лся|лась|лось|лись|ет|ёт|ит|ют|ут|ат|ят|ешь|ёшь|ишь|ем|ём|им|ете|ёте|ите|ть|ться|тся|й|йте)$")
LINE_W = 2 * (W - ICONS - W / 2) - 64  # ширина текста субтитра: плашка по центру, правый край ≤ 960 (иконки), поля плашки 32+32

# Интервью (Арон, 2026-09-30, макет): чёрный кадр 1080×1920, горизонтальное видео во всю ширину в рамке IV_VIDEO
# (montazh.py: IV_Y = 578, IV_H = 564). Надписи — только на чёрном, на видео не заходят; весь ролик.
IV_VIDEO = (578, 1142)                            # рамка видео по высоте
IV_RUB = dict(size=38, weight=600, y=290, fill=(200, 200, 200))  # рубрика: Montserrat SemiBold, светло-серая, по центру
IV_TITLE_SIZE, IV_TITLE_WEIGHT = 76, 800          # заголовок: Montserrat ExtraBold, капс
IV_TITLE_Y, IV_TITLE_STEP = 390, 92               # центры строк заголовка: 390, 482
WHITE, GOLD = (255, 255, 255), (255, 196, 64)     # заголовок белый, выделенные слова золотые
IV_SUB_Y = 1192                                   # субтитры: сразу под видео (1142 + 50), белые на чёрном, без плашки
IV_LINE_W = 2 * (W - ICONS - W / 2)               # строка ≤ 840 px при центре 540: правый край ≤ 960 (иконки)

# Квадрат (подкаст «Визионеры», 2026-10-12; сборка — kvadrat.py): чёрный кадр 1080×1920, видео в рамке по высоте — из plan.json
# ("video_y", "video_h"); без них — первый квадрат 1080×1080 на y 330–1410 (KV_VIDEO). Надписи — только на чёрном: заголовок
# над видео, субтитры под видео, весь ролик. На видео и на тёмную штору над головой заголовок не заходит.
# С 2026-10-12 видео 1080×960 на y 416–1376 (квадрат без нижних 120 px стола): лента Instagram показывает кадр 4:5 — с y 285,
# сетка профиля 3:4 — с y 240, и заголовок старого квадрата (y 231–326) в ленте был обрезан. Теперь поле заголовка — между
# линией ленты и видео, поле субтитров — между видео и низом зоны Reels (1500): всё видно в ленте, в сетке и в Reels.
KV_VIDEO = (330, 1410)                            # рамка видео по высоте, если в plan.json нет "video_y" / "video_h"
FEED_TOP, GRID_TOP = 285, 240                     # с этих y кадр виден в ленте (4:5) и в сетке профиля (3:4)
KV_TITLE_WEIGHT = 700                             # заголовок: Montserrat Bold, капс, белый; деньги — зелёные
KV_TITLE_ONE = 72                                 # одна строка (до ~20 знаков)
KV_TITLE_TWO, KV_TITLE_STEP = 46, 56              # две строки; с «Й» сверху и «Д», «Ц», «Щ» снизу блок занимает 105 px:
KV_TITLE_UP, KV_TITLE_DOWN = 53, 52               # на столько он выше и ниже своего центра
KV_TITLE_GAP = 12                                 # от низа блока до видео (если поле в обрез — блок по его середине)
GREEN = (59, 217, 138)                            # деньги — зелёные: C.money (#3BD98A) из tools/remotion/src/lib/theme.ts

# Склейки (раскладка kvadrat или "skleyki": true). Паузы в подкасте вырезаны, слово от слова через склейку — 0,05–0,15 с:
CUT_EPS = 0.03                                    # слово «пересекает» склейку, если заходит за неё больше чем на столько
CUT_WORD = 0.05                                   # за склейкой ≥ столько звука слова — слово звучит после неё (иначе — до неё)
CUT_SNAP = 0.3                                    # фраза, начавшаяся не позже чем через столько после склейки, ставится на склейку
                                                  # (как «разрыв < 0,3 с — прошлая держится до следующей»: иначе прошлая фраза
                                                  # несколько кадров висела бы на новом плане)
CUT_NEAR = 3                                      # смена субтитра в 1…3 кадрах от склейки (не на ней) — предупреждение

# Япинг (yapping; первый ролик — «Извозчики или лошади», 2026-10-13; мерки формата — docs/япинг.md).
# Шрифт, кегли и вид текста — формат, они здесь. ГДЕ стоят строки — зависит от записи (как человек сел, где петличка):
# это меряет режиссёр и пишет в титры.json ("zagolovok" → "y", "vysota"), в программе высот нет.
YAPING = False                                    # в main(): раскладка yaping — другой шрифт, предел строки и вид текста
# Шрифт и кегли — из титры.json → "shrift" (смена шрифта — одна строка и повторный запуск); здесь — что берётся без неё.
# Арон, 2026-10-13, на PT Serif Bold: «менее агрессивный, менее толстый… попроще, потоньше, поэлегантнее». Из чужого формата
# берём устройство (где текст, сколько слов, ритм), а вес и характер шрифта — по вкусу Арона: тонкий, простой, не жирный.
YP_FONT = dict(file="/System/Library/Fonts/Supplemental/PTSerif.ttc",  # системный PT Serif; имя без пути — из tools/fonts
               nachertanie="Regular",             # начертание: имя («Regular», «Roman», «Bold») или номер в файле
               ves=None,                          # вес для переменного шрифта (Montserrat[wght].ttf: 500 — Medium)
               kegl=46,                           # субтитр: буквы от верха «б» до низа «р» — 44 px (у оригинала 39–48)
               kegl_zagolovka=56)                 # заголовок: буквы 54 px — отличается от субтитра размером, а не жирностью
YP_TITLE_LEAD = 62 / 52                           # шаг строк заголовка к кеглю (у оригинала строки через 57–68 px)
YP_LINE_W = 660                                   # строка субтитра не шире (у оригинала — до ~600 из 1080)
YP_WORDS, YP_CHARS = 5, 26                        # фраза: до 5 слов и 26 знаков (у оригинала 2–5 слов, 15–25 знаков).
# 26, а не 25: тонкий шрифт уже, 26 знаков входят в те же 660 px, а с пределом 25 рвалось «в постоянное | убежище людей»
# и оставалось одно слово «извозчиков» (26 знаков — «в постоянное убежище людей», «извозчиков меньше не стало»)
# Тень — не контур. Арон, 2026-10-13, на тень «6 px, уплотнена в 2,6 раза»: «не хватает элегантности: вокруг обводка
# какая-то непонятная». Узкий плотный ореол повторяет форму буквы и читается как обводка, каким бы ни был контраст.
# Теперь тень — затемнение под всей строкой: буквы размыты на blur (в несколько толщин штриха — контура не остаётся)
# и приведены к плотности plotnost в самом тёмном месте (доля кадра, которую тень закрывает; от толщины шрифта не зависит).
# титры.json → "ten" меняет её вместе со шрифтом; замеры и правило проверки вида — титры.md, «Япинг».
YP_SHADOW = dict(dy=0, blur=20, plotnost=0.5)
# Цвет текста — из титры.json → "cvet" (весь ролик), у заголовка и у вставки — свой "cvet"; без него — белый, как в первом
# ролике. «Соцсеть для сообществ» (2026-10-17): Арон в белой рубашке, белая строка на ней не читается (контраст 1,4–2,9),
# а мягкое затемнение под ней — серое пятно («обводка»): на лице строка графитовая #1A1E21 без тени, под карточкой — белая.
YP_CVET = WHITE


def yp_color(v):
    """Цвет из титры.json: "#1A1E21" или [26, 30, 33] → (r, g, b)."""
    if isinstance(v, str):
        m = re.fullmatch(r"#?([0-9A-Fa-f]{6})", v.strip())
        assert m, f'япинг: цвет «{v}» — нужно "#RRGGBB"'
        return tuple(int(m.group(1)[i:i + 2], 16) for i in (0, 2, 4))
    assert isinstance(v, (list, tuple)) and len(v) == 3 and all(0 <= int(c) <= 255 for c in v), f"япинг: цвет {v} — нужно [r, g, b]"
    return tuple(int(c) for c in v)


def kv_geometry(video):
    """Квадрат: где стоят надписи при рамке видео video = (верх, низ) → (верх поля заголовка, центр блока заголовка,
    центр строки субтитров). Поле заголовка — от линии ленты (y 285) до видео, если блок туда входит с запасом; иначе —
    от верха безопасной зоны (первый квадрат 330–1410: заголовок на 220–330, в ленте обрезан). Блок прижат к видео на
    KV_TITLE_GAP: линия ленты — приблизительная, запас оставляем с её стороны. Субтитры — посередине чёрной полосы между
    видео и низом зоны Reels. Первый квадрат: (220, 275, 1455); видео 416–1376: (285, 352, 1438)."""
    need = KV_TITLE_UP + KV_TITLE_DOWN
    top = FEED_TOP if video[0] - FEED_TOP >= need + 2 * 10 else SAFE[1]
    gap = min(KV_TITLE_GAP, (video[0] - top - need) / 2)
    return top, int(video[0] - gap - KV_TITLE_DOWN), (video[1] + SAFE[3]) // 2


def font(size, weight):
    f = ImageFont.truetype(FONT, size)
    f.set_variation_by_axes([weight])
    return f


def plate(text, sub, y_center, size, weight, alpha=205):  # плотная: сквозь неё не просвечивают логотипы и текст
    """Картинка W×H: текст по центру на полупрозрачной тёмной плашке со скруглением.
    Не влезает по ширине — перенос на вторую строку (поровну по словам). Ниже 1150 справа иконки — правый край ≤ 960."""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    f1 = font(size, weight)
    right = W - ICONS if y_center + size > ICONS_FROM else SAFE[2]
    max_w = 2 * (right - W / 2) - 64                      # плашка по центру кадра и не заходит за правый край
    rows = text.split("\n")                             # «\n» в тексте — строки одного размера (заголовок)
    if len(rows) == 1 and d.textlength(text, font=f1) > max_w and size != SUB_SIZE:  # субтитры — всегда одна строка
        ws_ = text.split()
        ks = [k for k in range(1, len(ws_)) if normal(ws_[k - 1]) not in GLUE] or list(range(1, len(ws_)))
        best = min(ks, key=lambda k: abs(d.textlength(" ".join(ws_[:k]), font=f1) - d.textlength(" ".join(ws_[k:]), font=f1)))
        rows = [" ".join(ws_[:best]), " ".join(ws_[best:])]
    lines = [(r, f1) for r in rows] + ([(sub, font(round(size * 0.6), 400))] if sub else [])
    ws = [d.textlength(t, font=f) for t, f in lines]
    hs = [f.size * 1.25 for _, f in lines]
    bw, bh = max(ws) + 64, sum(hs) + 34
    x0, y0 = (W - bw) / 2, y_center - bh / 2
    assert x0 >= SAFE[0] and x0 + bw <= right and y0 >= SAFE[1] and y0 + bh <= SAFE[3], f"вне зоны: {text}"
    d.rounded_rectangle((x0, y0, x0 + bw, y0 + bh), radius=24, fill=(0, 0, 0, alpha))
    y = y0 + 17
    for (t, f), h in zip(lines, hs):
        d.text((W / 2, y + h / 2), t, font=f, fill=(255, 255, 255, 255), anchor="mm")
        y += h
    return img


def check_box(box, what, video=IV_VIDEO):
    """Надпись на чёрном кадре (интервью, квадрат): целиком в безопасной зоне (ниже 1150 справа иконки — правый край ≤ 960)
    и не на рамке видео."""
    x0, y0, x1, y1 = box
    right = W - ICONS if y1 > ICONS_FROM else SAFE[2]
    assert x0 >= SAFE[0] and x1 <= right and y0 >= SAFE[1] and y1 <= SAFE[3], f"вне зоны: {what} {box}"
    assert y1 < video[0] or y0 > video[1], f"заходит на видео {video}: {what} {box}"


def paint_line(d, line, f, y, marks, color, video, found):
    """Строка заголовка по центру кадра: слова и сочетания из marks — цветом color, остальное белое; каждое слово — в зоне
    и не на видео. found — сюда пишутся номера найденных сочетаний."""
    ws = line.split()
    paint = [False] * len(ws)
    for gi, g in enumerate(marks):  # выделенное — слово или сочетание подряд
        for i in range(len(ws) - len(g) + 1):
            if ws[i:i + len(g)] == g:
                paint[i:i + len(g)] = [True] * len(g); found.add(gi)
    x = W / 2 - d.textlength(line, font=f) / 2
    for w, g in zip(ws, paint):
        check_box(d.textbbox((x, y), w, font=f, anchor="lm"), line, video)
        d.text((x, y), w, font=f, fill=(color if g else WHITE) + (255,), anchor="lm")
        x += d.textlength(w + " ", font=f)


def kv_header(zag, video=KV_VIDEO):
    """Квадрат: заголовок на чёрном поле над видео — одна строка (крупно) или две одного размера, капс, белый, деньги
    зелёные; один слой на весь ролик. Длинное тире и многоточие — нельзя (дефис в слове и «5–10» — можно).
    Каждое слово — в безопасной зоне, не на видео и не выше верха поля (линия ленты, если заголовок стоит под ней)."""
    top, title_y, _ = kv_geometry(video)
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    rows = zag.get("stroki", [])
    assert 1 <= len(rows) <= 2, f"заголовок квадрата — одна или две строки, а не {len(rows)}"
    for t in rows:
        assert not re.search(r"—|…|\.\.|\s[–-]\s", t), f"в заголовке тире/многоточие: {t}"
    size = KV_TITLE_ONE if len(rows) == 1 else KV_TITLE_TWO
    f = font(size, KV_TITLE_WEIGHT)
    green = [z.split() for z in zag.get("zelenoe", [])]
    found = set()
    y0 = title_y - KV_TITLE_STEP * (len(rows) - 1) / 2
    for k, line in enumerate(rows):
        assert d.textlength(line, font=f) <= SAFE[2] - SAFE[0], f"заголовок не влезает по ширине ({size} px): {line}"
        paint_line(d, line, f, y0 + k * KV_TITLE_STEP, green, GREEN, video, found)
    box = img.getchannel("A").getbbox()
    assert box is None or box[1] >= top, f"заголовок выше своего поля (y {top}): {box}"
    miss = [" ".join(g) for gi, g in enumerate(green) if gi not in found]
    assert not miss, f"зелёных слов нет в заголовке: {miss}"
    return img


def iv_header(rubrika, zag):
    """Интервью: рубрика и заголовок (строки одного размера, выделенные слова золотые) — один слой на весь ролик."""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for t in [rubrika or ""] + zag.get("stroki", []):
        # Арон, 2026-09-30: «без длинных тире и всякого этого» — слова через обычный пробел
        assert not re.search(r"[—–-]|…|\.\.", t), f"в заголовке тире/многоточие: {t}"
    if rubrika:
        f = font(IV_RUB["size"], IV_RUB["weight"])
        xy = (W / 2, IV_RUB["y"])
        check_box(d.textbbox(xy, rubrika, font=f, anchor="mm"), rubrika)
        d.text(xy, rubrika, font=f, fill=IV_RUB["fill"] + (255,), anchor="mm")
    f = font(IV_TITLE_SIZE, IV_TITLE_WEIGHT)
    gold = [z.split() for z in zag.get("zoloto", [])]
    found = set()
    for k, line in enumerate(zag.get("stroki", [])):
        paint_line(d, line, f, IV_TITLE_Y + k * IV_TITLE_STEP, gold, GOLD, IV_VIDEO, found)
    miss = [" ".join(g) for gi, g in enumerate(gold) if gi not in found]
    assert not miss, f"золотых слов нет в заголовке: {miss}"
    return img


def iv_sub(text, y=IV_SUB_Y, video=IV_VIDEO):
    """Интервью, квадрат: субтитр — одна строка, белый прямо на чёрном под видео, без плашки."""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    f = font(SUB_SIZE, SUB_WEIGHT)
    assert d.textlength(text, font=f) <= LINE_W, f"не влезает в одну строку: {text}"
    xy = (W / 2, y)
    check_box(d.textbbox(xy, text, font=f, anchor="mm"), text, video)
    d.text(xy, text, font=f, fill=WHITE + (255,), anchor="mm")
    return img


@functools.lru_cache(None)
def yp_face(file, face, weight, size):
    """Шрифт япинга: файл (без пути — из tools/fonts), начертание по имени или номеру, вес переменного шрифта."""
    path = file if "/" in file else str(Path(__file__).parent / "fonts" / file)
    assert Path(path).exists(), f"нет файла шрифта: {path}"
    if isinstance(face, int):
        f = ImageFont.truetype(path, size, index=face)
    else:
        names, f = [], None
        for i in range(64):
            try:
                g = ImageFont.truetype(path, size, index=i)
            except OSError:
                break
            names.append(g.getname()[1])
            if g.getname()[1].lower() == str(face).lower():
                f = g
                break
        if f is None and weight is not None and names:   # переменный шрифт: начертание задаёт вес, имя в файле одно
            f = ImageFont.truetype(path, size)
        assert f is not None, f"в {path} нет начертания «{face}», есть: {names}"
    if weight is not None:
        f.set_variation_by_axes([weight])
    return f


def yp_font(size):
    return yp_face(YP_FONT["file"], YP_FONT["nachertanie"], YP_FONT["ves"], size)


def yp_draw(rows, size, green=(), found=None, plotnost=None, cvet=None):
    """Япинг: строки [(текст, середина букв по высоте)] шрифтом YP_FONT по центру кадра, без плашки и обводки, с мягкой
    тенью → (слой W×H, рамка букв). Середина букв — от верха «б» до низа «р» (так меряет режиссёр: PT Serif 44 — 42 px,
    52 — 50 px). green — слова и сочетания подряд, которые зелёные (деньги); found — сюда пишутся номера найденных.
    Буквы (без тени) — целиком в безопасной зоне; ниже 1150 справа иконки — правый край ≤ 960.
    Тень — одна на все строки: размытые буквы, приведённые к плотности YP_SHADOW["plotnost"] в самом тёмном месте.
    Размытие в несколько толщин штриха, поэтому контур буквы она не повторяет: это затемнение под строкой, а не ореол.
    plotnost — плотность тени для этой строки (под вставкой на тёмном фоне — 0, тень не нужна); None — общая.
    cvet — цвет букв (r, g, b); None — общий YP_CVET (титры.json → "cvet", без него белый)."""
    f = yp_font(size)
    probe = ImageDraw.Draw(Image.new("L", (1, 1)))
    _, top, _, bot = probe.textbbox((0, 0), "бр", font=f, anchor="ls")
    mask = Image.new("L", (W, H), 0)
    color = Image.new("RGB", (W, H), YP_CVET if cvet is None else cvet)
    for text, cy in rows:
        base = round(cy - (top + bot) / 2)                   # линия шрифта
        x = round(W / 2 - probe.textlength(text, font=f) / 2)
        ImageDraw.Draw(mask).text((x, base), text, font=f, fill=255, anchor="ls")
        ws = text.split()
        for gi, g in enumerate(green):  # зелёное — по ширине своих слов; буквы рисуются один раз, цвет меняется под ними
            for i in range(len(ws) - len(g) + 1):
                if ws[i:i + len(g)] == g:
                    a = x + probe.textlength(" ".join(ws[:i]) + (" " if i else ""), font=f)
                    b = x + probe.textlength(" ".join(ws[:i + len(g)]), font=f)
                    color.paste(GREEN, (int(a) - 2, base + top - 20, int(b) + 3, base + bot + 20))
                    if found is not None:
                        found.add(gi)
    box = mask.getbbox()
    what = " / ".join(t for t, _ in rows)
    right = W - ICONS if box[3] > ICONS_FROM else SAFE[2]
    assert box[0] >= SAFE[0] and box[2] <= right and box[1] >= SAFE[1] and box[3] <= SAFE[3], f"вне зоны: {what} {box}"
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    plotnost = YP_SHADOW["plotnost"] if plotnost is None else plotnost
    if plotnost > 0:
        pad = round(YP_SHADOW["blur"] * 4)
        band = (0, max(0, box[1] - pad), W, min(H, box[3] + pad))  # тень считаем только в полосе строк — быстрее
        sh = Image.new("L", (W, band[3] - band[1]), 0)
        sh.paste(mask.crop(band), (0, YP_SHADOW["dy"]))
        a = np.asarray(sh.filter(ImageFilter.GaussianBlur(YP_SHADOW["blur"]))).astype(float)
        a *= plotnost * 255 / max(a.max(), 1.0)
        sh = Image.fromarray(a.round().astype(np.uint8))
        img.paste(Image.merge("RGBA", (*Image.new("RGB", sh.size, (0, 0, 0)).split(), sh)), (0, band[1]))
    color.putalpha(mask)
    img.alpha_composite(color)
    return img, box


def yp_line(text, size, cy, green=(), found=None, plotnost=None, cvet=None):
    """Япинг: одна строка (субтитр) → (слой, рамка букв)."""
    return yp_draw([(text, cy)], size, green, found, plotnost, cvet)


# Заголовок плашкой, как у Алекса Хормози (Арон, 2026-10-19: «заголовок, вот как делает Алекс Хормози. Вот точно так же»):
# жирные заглавные белые буквы на сплошной красной плашке со слегка скруглёнными углами, строки по центру, плашка одна
# на все строки, стоит в первые секунды на груди под подбородком. Мерки — шортсы @AlexHormozi на YouTube (2026-10-19).
YP_PLASHKA = dict(cvet="#E3262B", tekst="#FFFFFF", shrift="Montserrat[wght].ttf", ves=800, kegl=62,
                  shag=1.18, pole_x=30, pole_y=18, radius=12, niz=None)
# niz — нижний край плашки вместо низа зоны Reels (1420): для сторис, где внизу только строка ответа (≈1700),
# а подбородок стоит низко (Гительман, 2026-10-27: подбородок 1290, плашка под ним кончается на ≈1480)


def yp_plashka(zag):
    """Япинг: заголовок плашкой (титры.json → "zagolovok": {"stroki", "y", "do", "plashka": {…}}). "y" — середина
    плашки. Строки — как написаны (заглавными). → (слой, рамка плашки)."""
    p = {**YP_PLASHKA, **zag["plashka"]}
    extra = set(zag["plashka"]) - set(YP_PLASHKA)
    assert not extra, f'япинг: в "plashka" незнакомые настройки: {sorted(extra)}'
    probe = ImageDraw.Draw(Image.new("L", (1, 1)))
    rows = zag["stroki"]
    room = 2 * min(min(W - ICONS, SAFE[2]) - W / 2, W / 2 - SAFE[0]) - 2 * p["pole_x"]   # плашка по центру: до колонки иконок
    while max(probe.textlength(r, font=yp_face(p["shrift"], "", p["ves"], p["kegl"])) for r in rows) > room:
        p["kegl"] -= 2                                              # длинный заголовок — кегль меньше, а не за край
    f = yp_face(p["shrift"], "", p["ves"], p["kegl"])
    _, top, _, bot = probe.textbbox((0, 0), "ЁЙQ", font=f, anchor="ls")   # высота заглавных с надстрочными
    step = round(p["kegl"] * p["shag"])
    text_h = (bot - top) + step * (len(rows) - 1)
    wmax = max(probe.textlength(r, font=f) for r in rows)
    box = (round(W / 2 - wmax / 2 - p["pole_x"]), round(zag["y"] - text_h / 2 - p["pole_y"]),
           round(W / 2 + wmax / 2 + p["pole_x"]), round(zag["y"] + text_h / 2 + p["pole_y"]))
    right = W - ICONS if box[3] > ICONS_FROM else SAFE[2]
    assert box[0] >= SAFE[0] and box[2] <= right and box[1] >= SAFE[1] and box[3] <= (p["niz"] or SAFE[3]), \
        f"плашка заголовка вне зоны: {box}"
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle(box, radius=p["radius"], fill=yp_color(p["cvet"]) + (255,))
    for k, row in enumerate(rows):
        base = round(zag["y"] - text_h / 2 - top + k * step)
        d.text((W / 2, base), row, font=f, fill=yp_color(p["tekst"]) + (255,), anchor="ms")
    return img, box


def yp_header(zag):
    """Япинг: заголовок-хук — одна–три строки кеглем YP_FONT["kegl_zagolovka"] цветом субтитров (или своим "cvet"),
    по центру, как написаны в титры.json (строчными, «ИИ» прописными). "y" — середина букв первой строки, следующие —
    ниже на шаг строк (кегль × YP_TITLE_LEAD). С "plashka" — заголовок плашкой, как у Хормози (yp_plashka).
    → (слой, рамка букв)."""
    rows = zag.get("stroki", [])
    assert 1 <= len(rows) <= 3 and "y" in zag and "do" in zag, 'япинг: "zagolovok": {"stroki": [1–3 строки], "y": …, "do": …}'
    if "plashka" in zag:
        return yp_plashka(zag)
    size = YP_FONT["kegl_zagolovka"]
    return yp_draw([(row, zag["y"] + k * round(size * YP_TITLE_LEAD)) for k, row in enumerate(rows)], size,
                   cvet=yp_color(zag["cvet"]) if "cvet" in zag else None)


def yp_case(words):
    """Япинг: субтитры строчными. Заглавная в начале предложения убирается; аббревиатуры и названия остаются как есть:
    слово латиницей (ChatGPT, Claude) и слово с заглавной не в начале (ИИ, HR). Заглавная посреди предложения — имя
    (Арон, Москва), её не трогаем; имя в начале предложения станет строчным — видно при чтении субтитры.txt."""
    start = True
    for w in words:
        core = w["w"].lstrip("«\"(")
        if start and core[:1].isupper() and not re.search(r"[A-Za-z]", core) and not any(ch.isupper() for ch in core[1:]):
            w["w"] = w["w"].lower()
        start = bool(re.search(r"[.!?…]$", w["w"]))


def krupnosti(work):
    """Крупность каждого плана итога из склейки.txt: [(секунда начала, крупность)] — «  5.63  файл  8.20–13.13  zoom 1.15»;
    строка без «zoom» — крупность 1.0."""
    f = work / "склейки.txt"
    if not f.exists():
        return [(0.0, 1.0)]
    rows = re.findall(r"^[ \t]*(\d+\.\d+)[ \t]+\S.*?(?:zoom[ \t]+(\d+(?:\.\d+)?))?[ \t]*$", f.read_text(), re.M)
    return sorted((float(t), float(z) if z else 1.0) for t, z in rows) or [(0.0, 1.0)]


def video_fps(mp4):
    """Частота кадров итога — сетка, на которой меняются субтитры: (число для счёта, строка для ffmpeg).
    Подкаст собран в родных 25 кадрах в секунду, остальное — в 30; целая частота остаётся целым числом."""
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=r_frame_rate",
                        "-of", "csv=p=0", str(mp4)], capture_output=True, text=True).stdout.strip().strip(",")
    f = Fraction(r)
    return (int(f) if f.denominator == 1 else float(f)), f"{f.numerator}/{f.denominator}"


def skleyki(work):
    """Секунды склеек итога из склейки.txt (первое число строки: «  2.56  кусок  2 …»), без начала ролика."""
    f = work / "склейки.txt"
    if not f.exists():
        return []
    return sorted({float(m.group(1)) for m in re.finditer(r"^[ \t]*(\d+\.\d+)[ \t]+\S", f.read_text(), re.M)} - {0.0})


def split_words(words):
    """Слово с пробелом внутри («раза в» — ручная правка расшифровки) — это несколько слов: иначе правила переноса их
    не видят и служебное «в» повиснет в конце строки. Время делится по буквам."""
    out = []
    for w in words:
        parts = w["w"].split()
        if len(parts) < 2:
            out.append(w); continue
        tot, acc = sum(len(p) for p in parts), 0
        for p in parts:
            a0 = w["s"] + (w["e"] - w["s"]) * acc / tot; acc += len(p)
            out.append({"w": p, "s": round(a0, 3), "e": round(w["s"] + (w["e"] - w["s"]) * acc / tot, 3)})
    return out


def fix_times(words, vremya):
    """Поправки времени слова из титры.json → "vremya": [["слово", начало по итог_слова.json, верное начало]] — когда whisper
    ошибся с началом слова посреди речи и правилом это не ловится («Google, | инструмент шикарный»: «инструмент» с 1,88,
    а «ин-» звучит с 1,74 — whisper начал слово с «с»; видно только по спектру). Слово ищется по тексту рядом с этим
    временем (±0,3 с), так что после перемонтажа поправка либо попадёт в то же слово, либо скажет, что не сработала."""
    log = []
    for word, was, now in vremya:
        near = [w for w in words if normal(w["w"]) == normal(word) and abs(w["s"] - was) <= 0.3]
        if not near:
            log.append(f"поправка времени не сработала: «{word}» около {was:.2f} с в итог_слова.json нет")
            continue
        w = min(near, key=lambda w: abs(w["s"] - was))
        log.append(f"время слова «{w['w']}»: начало {w['s']:.2f} → {now:.2f}")
        w["s"] = now
    return log


def mark_razryvy(words, razryvy):
    """Ручные разрывы из титры.json → "razryvy": [["слово", начало по итог_слова.json]] — после этого слова всегда новая
    строка: правила деления порвали мысль, а зритель увидел («что у нас актива | не будет и придётся потом» →
    «что у нас актива не будет | и придётся потом»; «то вы способны создать то | что будет удобно» → «то вы способны
    создать | то что будет удобно»; Соцсеть, 2026-10-17). Через разрыв не идут слияние коротких фраз и перенос служебных
    слов; строка, которая кончается разрывом, целиком, если входит в одну строку по ширине (пределы слов и знаков уступают).
    Слово ищется по тексту рядом с этим временем (±0,3 с), как в "vremya": после перемонтажа разрыв попадёт в то же слово
    или скажет, что не сработал."""
    log = []
    for word, was in razryvy:
        near = [w for w in words if normal(w["w"]) == normal(word) and abs(w["s"] - was) <= 0.3]
        if not near:
            log.append(f"разрыв не сработал: «{word}» около {was:.2f} с в итог_слова.json нет")
            continue
        w = min(near, key=lambda w: abs(w["s"] - was))
        w["brk"] = True
        log.append(f"разрыв строки после «{w['w']}» ({w['s']:.2f})")
    return log


def words_to_cuts(words, cuts, on):
    """Слово не звучит через склейку: склейка — разрыв записи, внутри слова её не бывает. Whisper по целому итогу тянет начало
    слова назад, в хвост предыдущего куска («но-о-о | у них»: «у» 2,36–3,08 при склейке 2,92 — фраза вышла бы на 0,6 с
    раньше голоса; Визионеры, 2026-10-12); конец слова он ставит верно. За склейкой ≥ CUT_WORD звука — слово начинается
    на склейке; меньше — оно кончается на ней. Возвращает список правок для вывода."""
    log = []
    for k, w in enumerate(words):
        for c in cuts:
            if w["s"] < c - CUT_EPS and w["e"] > c + CUT_EPS:
                was = f"{w['s']:.2f}–{w['e']:.2f}"
                if w["e"] - c >= CUT_WORD:
                    w["s"] = c
                    # звук до склейки, который whisper отдал этому слову, — конец прошлого слова («но-о-о» тянется 0,8 с,
                    # а по whisper 0,4): дотягиваем его конец, пока звук не прервётся, но не дальше склейки
                    p = words[k - 1] if k else None
                    if p is not None and p["e"] < c:
                        j = int(round(p["e"] * 100))
                        while j < min(len(on), int(round(c * 100))) and on[j]:
                            j += 1
                        if j / 100 > p["e"]:
                            log.append(f"«{p['w']}» звучит до {min(j / 100, c):.2f}, а не до {p['e']:.2f}")
                            p["e"] = round(min(j / 100, c), 2)
                else:
                    w["e"] = c
                log.append(f"«{w['w']}» {was} пересекает склейку {c:.2f} → {w['s']:.2f}–{w['e']:.2f}")
    return log


def normal(w):
    return re.sub(r"[.,!?:;«»\"]", "", w).lower()


def voice(mp4):
    """Громкость итога по 10 мс (дБ) и порог «звучит»: пол тишины ролика + VOICE_FLOOR, не ниже VOICE_DB."""
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(mp4), "-vn", "-ac", "1", "-ar", "16000", "-f", "s16le", "-"],
                         capture_output=True, check=True).stdout
    a = np.frombuffer(raw, dtype=np.int16).astype(float)
    m = len(a) // 160
    db = 10 * np.log10((a[:m * 160].reshape(m, 160) ** 2).mean(1) / 32768 ** 2 + 1e-12)
    return db, max(VOICE_DB, np.percentile(db, 5) + VOICE_FLOOR)


def speech(j, on, loud):
    """Звук с отсчёта j — речь, а не вдох: не позже чем через VOICE_RISE он без провала становится громким (на VOICE_LOUD
    выше порога). Вдох перед фразой в студийной записи — ровный шум −45…−60 дБ на 0,3–0,4 с: выше порога тишины, но громким
    не становится («сделать, [вдох 0,4 с] и до момента» — фраза вышла на 0,4 с раньше голоса; Визионеры, 2026-10-12).
    loud = None — правило выключено (прежние раскладки считаются как были)."""
    if loud is None:
        return True
    for k in range(j, min(len(on), j + round(VOICE_RISE * 100) + 1)):
        if not on[k]:
            return False
        if loud[k]:
            return True
    return False


def no_stops(word):
    """Короткое слово без смычных согласных («и», «а», «я», «у», «но», «ну», «он», «за», «на», «не», «мы», «вы»): внутри
    такого слова тишины не бывает — смычки «п/т/к/б/д/г/ц/ч» в нём нет."""
    t = re.sub(r"[^а-яё]", "", word.lower())
    return 0 < len(t) <= 3 and not set(t) & set("бпдтгкцч")


def after_pause(s, e, on, loud):
    """Начало звука после ПОСЛЕДНЕЙ паузы (≥ PAUSE_GAP) внутри отрезка слова s…e; паузы нет — None.
    Предела VOICE_MAX тут нет: отрезок ограничен концом самого слова («в» 11,92–12,68 после паузы 0,52 с звучит с 12,6)."""
    i, g, last = int(round(s * 100)), round(PAUSE_GAP * 100), None
    for j in range(i + g, min(len(on) - 2, int(round(e * 100)) - 3) + 1):
        if on[j:j + 3].all() and not on[j - g:j].any() and speech(j, on, loud):
            last = j
    return None if last is None else round(last / 100, 2)


def short_words(words, on, loud):
    """Короткие слова без смычных (no_stops), которые whisper растянул через паузу: начало — после последней паузы внутри
    отрезка слова. Делается для всех слов до деления на фразы — иначе пауза не видна и фраза через неё не рвётся
    («погружаться [пауза 0,5 с] в те материалы»: «в» по whisper 11,92–12,68, звучит с 12,6; зритель, 2026-10-12).
    Возвращает список правок для вывода."""
    log = []
    for w in words:
        if no_stops(w["w"]):
            v = after_pause(w["s"], w["e"], on, loud)
            if v is not None and v > w["s"]:
                log.append(f"«{w['w']}» {w['s']:.2f}–{w['e']:.2f}: внутри пауза, звучит с {v:.2f}")
                w["s"] = v
    return log


def voice_start(s, on, loud=None, e=None):
    """Начало звука слова, которое whisper начал в тишине: первый звучащий отрезок ≥ 30 мс не дальше VOICE_MAX после s.
    Слово начинается со звука — s как есть. Звука за VOICE_MAX нет — None (время слова ошибочно, проверить руками).
    loud задан (раскладка kvadrat или "vdoh": true): вдох — не звук слова (speech).
    e задан — это конец короткого слова без смычных (no_stops): whisper после запятой тянет его начало назад — в тишину,
    во вдох или в конец прошлого слова, а конец ставит верно («любой книги, | и через…»: «и» 3,48–3,74, а «книги» звучит
    до 3,52, тишина до 3,64, «и» — с 3,65; «часов | и 200 рублей»: «и» 14,64–14,98, звучит с 14,91). Тишины внутри такого
    слова нет, значит оно начинается после ПОСЛЕДНЕЙ паузы (≥ PAUSE_GAP) внутри своего отрезка. Визионеры, 2026-10-12."""
    i = int(round(s * 100))
    if i >= len(on) - 2:
        return s
    if e is not None:
        v = after_pause(s, e, on, loud)
        if v is not None:
            return v
    if on[i] and speech(i, on, loud):
        return s
    for j in range(i, min(len(on) - 2, i + round(VOICE_MAX * 100) + 1)):
        if on[j:j + 3].all() and speech(j, on, loud):
            return round(j / 100, 2)
    return None


def apply_pravki(words, pravki, used=None):
    """Правки по смыслу: [(как распознано, как должно быть)] — одна или несколько подряд идущих слов.
    Время: начало первого слова, конец последнего (внутри — по буквам); знак препинания последнего слова сохраняется.
    used — сюда пишутся сработавшие правки."""
    pravki = sorted(pravki, key=lambda p: -len(p[0].split()))  # сначала длинные совпадения
    out, i = [], 0
    while i < len(words):
        for src, dst in pravki:
            n = len(src.split())
            seg = words[i:i + n]
            if len(seg) == n and [normal(x["w"]) for x in seg] == [normal(x) for x in src.split()]:
                if used is not None:
                    used.add(src)
                tail = re.search(r"[.,!?:;]+$", seg[-1]["w"])
                head_up = seg[0]["w"][:1].isupper() and dst[:1].islower()
                txt = (dst[:1].upper() + dst[1:] if head_up else dst) + (tail.group() if tail and not re.search(r"[.,!?:;]$", dst) else "")
                parts = txt.split()  # правка из нескольких слов — снова отдельные слова (иначе правила переноса их не видят)
                s0, e0 = seg[0]["s"], seg[-1]["e"]
                tot = sum(len(x) for x in parts)
                acc = 0
                for x in parts:
                    a0 = s0 + (e0 - s0) * acc / tot; acc += len(x)
                    out.append({"w": x, "s": round(a0, 3), "e": round(s0 + (e0 - s0) * acc / tot, 3)})
                i += n
                break
        else:
            out.append(dict(words[i])); i += 1
    # «-то», «-нибудь», «-либо» — к предыдущему слову без пробела;
    # тире отдельным словом («Первый – буквальный») — к предыдущему слову через пробел, «—»: разрыв фразы, в конце строки не показывается
    res = []
    for w in out:
        if re.fullmatch(r"[-–—]+", w["w"]) and res:
            res[-1]["w"] = res[-1]["w"].rstrip(",") + " —"
        elif w["w"].startswith("-") and res:
            res[-1]["w"] = res[-1]["w"].rstrip(",") + w["w"]; res[-1]["e"] = w["e"]
        else:
            res.append(w)
    return res


def shown(text):
    """Как фраза выглядит на экране: точку/запятую/тире в конце не показываем — и не считаем. Япинг — без точек, запятых,
    двоеточий, тире и восклицательных знаков вообще (формат), вопросительный знак остаётся; дефис внутри слова и «5–10»
    на месте."""
    if YAPING:
        return " ".join(re.sub(r"[.,;:!…—–]+(?=\s|$)", "", text).split())
    return text.rstrip(",.;:— ")


def fits(text):
    """Фраза помещается в ОДНУ строку субтитров (по реальной ширине шрифта; LINE_W — с полями плашки или без, по раскладке)."""
    f = yp_font(YP_FONT["kegl"]) if YAPING else font(SUB_SIZE, SUB_WEIGHT)
    return f.getlength(shown(text)) <= LINE_W  # в полосе субтитров справа иконки Instagram


def chunks(words, cuts=()):
    """Фразы до MAX_WORDS слов, всегда в одну строку: разрыв на знаках препинания и паузах; служебные слова не висят
    в конце; фраза короче MIN_SHOW по звуку сливается с соседней (хвост с запятой — к предыдущей), иначе мелькает.
    cuts — склейки: разрыв фразы, как пауза (паузу вырезал монтаж, склейка стоит на её месте)."""
    txt = lambda c: " ".join(x["w"] for x in c)
    # 1) куски мысли: разрыв на знаках препинания и паузах > 0,35 с
    parts, cur = [], []
    for i, w in enumerate(words):
        cur.append(w)
        nxt = words[i + 1] if i + 1 < len(words) else None
        cut = nxt and any(w["e"] <= t + CUT_EPS and nxt["s"] >= t - CUT_EPS for t in cuts)
        if not nxt or re.search(r"[.,!?:;—]$", w["w"]) or nxt["s"] - w["e"] > 0.35 or cut or w.get("brk"):
            parts.append(cur); cur = []
    if cur:
        parts.append(cur)
    # короткий кусок, который начинает следующий (не хвост с запятой, не конец предложения: «что 100,», «ну,»), — к следующему
    # ДО деления, если следующий сам в одну фразу не влезает и будет делиться: иначе он делится без короткого куска,
    # а слитая потом фраза рвёт пару («что 100, хочу 90 на время | испытательного срока» →
    # «что 100, хочу 90 | на время испытательного срока», 2026-09-30). Следующий влезает целиком — как раньше, слияние после деления.
    single = lambda c: len(c) <= MAX_WORDS and len(shown(txt(c))) <= MAX_CHARS and fits(txt(c))
    k = 0
    while k < len(parts) - 1:
        c = parts[k]
        tail = bool(re.search(r"[,;:—]$", c[-1]["w"])) and c[0]["w"].lower().strip(",.") not in GLUE
        if (c[-1]["e"] - c[0]["s"] < MIN_SHOW and not re.search(r"[.!?]$", c[-1]["w"]) and not tail
                and not single(parts[k + 1]) and not c[-1].get("brk")):
            parts[k:k + 2] = [c + parts[k + 1]]
        else:
            k += 1
    # одно слово в конце предложения после запятой/паузы — к предыдущему куску ДО деления: иначе оно на экране сиротой
    # («и дальше можно перечислить | почему», 2026-09-30, №1 без ускорения: «почему.» 0,42 с — не короткое, слияние коротких
    # его не берёт). Деление само решит, где резать слитый кусок (не влезает — режет ровно, одно слово в конце не оставит).
    k = 1
    while k < len(parts):
        c, p = parts[k], parts[k - 1]
        if len(c) == 1 and re.search(r"[.!?]$", c[0]["w"]) and not re.search(r"[.!?]$", p[-1]["w"]) and not p[-1].get("brk"):
            parts[k - 1:k + 1] = [p + c]
        else:
            k += 1

    def split(c):
        """Кусок мысли → фразы: как можно меньше фраз, каждая ≤ MAX_WORDS слов, ≤ MAX_CHARS видимых знаков и в одну строку;
        из таких разбиений — фраза не кончается служебным словом, не короче MIN_SHOW по звуку и фразы ровные по длине.
        Раньше фраза набивалась до предела — в конце оставалось одно слово и рвались пары («таким | образом»,
        «на языке | бизнеса», «по этой | позиции», «день 12 | только»; 2026-09-30)."""
        m = len(c)
        vid = lambda i, j: shown(txt(c[i:j]))
        if c[-1].get("brk") and fits(vid(0, m)):  # строка до ручного разрыва — целиком, если входит в одну строку по ширине
            return [c]
        ok = lambda i, j: j - i == 1 or (j - i <= MAX_WORDS and len(vid(i, j)) <= MAX_CHARS and fits(vid(i, j)))
        low = lambda k: c[k]["w"].lower().strip(",.")
        best = {0: ((0, 0, 0, 0), [])}  # конец → (цена: фраз, висит служебное, коротких, ровность), разрезы
        for j in range(1, m + 1):
            for i in range(j):
                if i not in best or not ok(i, j):
                    continue
                glue = j < m and (low(j - 1) in GLUE or (  # «ни дизайнеры мне | для этого не понадобились»
                    low(j - 1) in PRON and not re.search(r"[,;:—]$", c[j - 1]["w"])
                    and (j - 2 < i or not (VERB.match(low(j - 2)) or low(j - 2) in PREP))))
                short = c[j - 1]["e"] - c[i]["s"] < MIN_SHOW
                look = len(vid(i, j)) ** 2
                if j < m and low(j) not in GROUP and ADJ.match(low(j - 1)) and not re.search(r"[,;:—]$", c[j - 1]["w"]):
                    look += ADJ_CUT
                if j < m and low(j) not in GROUP and NUM.fullmatch(low(j - 1)) and not re.search(r"[,;:—]$", c[j - 1]["w"]):
                    look += ADJ_CUT  # «за пять | часов», «10 | тысяч», «за миллион | рублей»
                if j < m and low(j) in GROUP:
                    look -= GROUP_CUT
                cost = tuple(a + b for a, b in zip(best[i][0], (1, glue, short, look)))
                if j not in best or cost < best[j][0]:
                    best[j] = (cost, best[i][1] + [j])
        cuts = [0] + best[m][1]
        # одно слово в конце куска не остаётся одно, если весь кусок — до MAX_WORDS слов и входит в строку по ширине:
        # предел знаков (замена ширины для чтения) уступает, как уступает правилу «служебное слово не висит»
        # («пока я не смотрел | переписки» → «пока я не смотрел переписки», 27 знаков, 627 px из 660; Соцсеть, 2026-10-17)
        if len(cuts) > 2 and cuts[-1] - cuts[-2] == 1 and m <= MAX_WORDS and fits(vid(0, m)):
            return [c]
        return [c[a:b] for a, b in zip(cuts, cuts[1:])]

    out = [h for c in parts for h in split(c)]
    ends = lambda c: bool(re.search(r"[.!?]$", c[-1]["w"]))   # фраза заканчивает предложение
    def merge_short():  # короткие фразы (< MIN_SHOW по звуку) — слить с соседней ВНУТРИ предложения
        for i, c in enumerate(out):
            if c[-1]["e"] - c[0]["s"] >= MIN_SHOW:
                continue
            # «назад,», «так,» — хвост предыдущей мысли; но «но,», «либо,», «ну,» — начало следующей
            tail = bool(re.search(r"[,;:—]$", c[-1]["w"])) and c[0]["w"].lower().strip(",.") not in GLUE
            order = ["prev", "next"] if tail else ["next", "prev"]
            for side in order:
                if side == "next" and i + 1 < len(out) and not ends(c) and not c[-1].get("brk") and fits(txt(c + out[i + 1])):
                    out[i] = c + out.pop(i + 1); return True
                if side == "prev" and i > 0 and not ends(out[i - 1]) and not out[i - 1][-1].get("brk") and fits(txt(out[i - 1] + c)):
                    out[i - 1] = out[i - 1] + out.pop(i); return True
        return False

    def glue_forward():  # служебные слова с конца фразы — в начало следующей (не через конец предложения)
        moved = False
        for i in range(len(out) - 1):
            while (len(out[i]) > 1 and out[i][-1]["w"].lower().strip(",.") in GLUE and not ends(out[i])
                   and not out[i][-1].get("brk") and fits(txt([out[i][-1]] + out[i + 1]))):
                out[i + 1].insert(0, out[i].pop()); moved = True
        return moved

    for _ in range(20):  # по кругу, пока есть что править: перенос служебных может снова дать короткую фразу
        a1 = False
        while merge_short():
            a1 = True
        if not glue_forward() and not a1:
            break
    # 3) не влезает в одну строку — разрезать там, где обе части держатся ≥ MIN_SHOW
    #    и первая не кончается служебным словом
    res = []
    for c in out:
        while not fits(txt(c)) and len(c) > 1:
            ok = [k for k in range(1, len(c))
                  if c[k - 1]["w"].lower().strip(",.") not in GLUE
                  and c[k - 1]["e"] - c[0]["s"] >= MIN_SHOW and c[-1]["e"] - c[k]["s"] >= MIN_SHOW]
            if not ok:  # нет «красивого» места — режем всё равно: двух строк не бывает (Арон, 2026-09-28)
                ok = [k for k in range(1, len(c)) if fits(txt(c[:k]))] or [1]
            k = min(ok, key=lambda k: abs(len(txt(c[:k])) - len(txt(c[k:]))))
            res.append(c[:k]); c = c[k:]
        res.append(c)
    out = res
    return [c for c in out if c]


def main():
    global LINE_W, FPS, YAPING, MAX_WORDS, MAX_CHARS, YP_CVET
    folder = Path(sys.argv[1]).expanduser()
    work = folder / "монтаж"
    words = split_words(json.loads((work / "итог_слова.json").read_text()))
    cfg = json.loads((work / "титры.json").read_text()) if (work / "титры.json").exists() else {}
    interview, kvadrat = cfg.get("layout") == "interview", cfg.get("layout") == "kvadrat"
    yaping = cfg.get("layout") == "yaping"
    assert cfg.get("layout") in (None, "interview", "kvadrat", "yaping"), f"неизвестная раскладка: {cfg.get('layout')}"
    if yaping:
        YAPING, LINE_W, MAX_WORDS, MAX_CHARS = True, YP_LINE_W, YP_WORDS, YP_CHARS
        assert not cfg.get("zagolovki"), "япинг: заголовок — zagolovok (строки, высота, до какой секунды), не zagolovki"
        extra = set(cfg.get("shrift", {})) - set(YP_FONT) | set(cfg.get("ten", {})) - set(YP_SHADOW)
        assert not extra, f'япинг: в "shrift" / "ten" незнакомые настройки: {sorted(extra)}'
        YP_FONT.update(cfg.get("shrift", {}))
        YP_SHADOW.update(cfg.get("ten", {}))
        YP_CVET = yp_color(cfg.get("cvet", WHITE))
        name = yp_font(YP_FONT["kegl"]).getname()
        print(f"шрифт: {name[0]} {name[1] if YP_FONT['ves'] is None else 'вес ' + str(YP_FONT['ves'])}, субтитр {YP_FONT['kegl']}, "
              f"заголовок {YP_FONT['kegl_zagolovka']}; "
              f"тень: размытие {YP_SHADOW['blur']} px, плотность {YP_SHADOW['plotnost']:.0%}, сдвиг {YP_SHADOW['dy']}; "
              f"цвет #{''.join(f'{c:02X}' for c in YP_CVET)}")
    if interview or kvadrat:
        LINE_W = IV_LINE_W  # без плашки — строка сама ≤ 840 px
        assert not cfg.get("zagolovki"), "интервью, квадрат: заголовок — zagolovok (весь ролик), не zagolovki"
    FPS, fps_arg = video_fps(work / "итог.mp4")  # смена субтитра — ровно на кадре ролика
    # квадрат: рамка видео — из плана монтажа ("video_y", "video_h"); без них — первый квадрат 330–1410
    plan = json.loads((work / "plan.json").read_text()) if kvadrat and (work / "plan.json").exists() else {}
    kv_video = (plan.get("video_y", KV_VIDEO[0]), plan.get("video_y", KV_VIDEO[0]) + plan.get("video_h", KV_VIDEO[1] - KV_VIDEO[0]))
    # склейки: в квадрате (подкаст) — всегда; в других раскладках — только по "skleyki": true (прежние ролики считаются как были)
    cuts = skleyki(work) if cfg.get("skleyki", kvadrat or yaping) else []
    # япинг: крупность каждого плана — от неё высота субтитра. Фразу рвёт только склейка со сменой крупности: там строка
    # переезжает вместе с планом. Склейка без смены крупности — вырезанная пауза, план и место строки те же, фраза через
    # неё стоит («извозчиками | или лошадьми?» — одна строка); смена субтитра рядом с ней всё равно ставится на её кадр.
    plans = krupnosti(work) if yaping else [(0.0, 1.0)]
    zoom_at = lambda t: [z for t0, z in plans if t0 <= t + 1e-6][-1]
    breaks = [t for t in cuts if zoom_at(t) != zoom_at(t - 0.02)] if yaping else cuts
    # япинг, "vstavki": вставка на весь кадр (карточка) закрывает лицо — субтитр там стоит на своей высоте (под карточкой).
    # Края вставки — как склейка со сменой крупности: разрыв фразы, строка меняет место ровно на этом кадре. Склейки итога
    # ПОД вставкой зритель не видит: смена субтитра к ним не притягивается; притягивается к "smeny" — секундам, где
    # меняется картинка самой вставки (подсветка): иначе строка сменится посреди её плавного перехода.
    # "cvet" вставки — цвет строки под карточкой (на графите — белый, когда на лице строка тёмная); без него — общий
    vst = [(v["ot"], v["do"], v["y"], v.get("smeny", []), v.get("plotnost"), yp_color(v["cvet"]) if "cvet" in v else None)
           for v in cfg.get("vstavki", [])] if yaping else []
    under = lambda t: any(v[0] < t < v[1] for v in vst)
    breaks = sorted(set(breaks) | {t for v in vst for t in v[:2]})
    edges = sorted({t for t in cuts if not under(t)} | {t for v in vst for t in [v[0], v[1]] + list(v[3])}) if yaping else cuts
    db, thr = voice(work / "итог.mp4")
    on = db > thr
    for line in fix_times(words, cfg.get("vremya", [])):
        print(line)
    for line in words_to_cuts(words, cuts, on):
        print("слово через склейку:", line)
    # начало фразы — начало речи, а не вдох перед ней и не конец прошлого слова (speech, no_stops): в квадрате (чистая
    # студийная запись) всегда, в других раскладках — по "vdoh": true. На прежних роликах одно правило вдоха сдвигает
    # 21 фразу на 0,07–0,33 с позже (проверено на двух: субтитр выходил на вдохе) — утверждённое без слова Арона не трогаем.
    vdoh = cfg.get("vdoh", kvadrat)
    loud = db > thr + VOICE_LOUD if vdoh else None
    for line in short_words(words, on, loud) if vdoh else []:
        print("слово через паузу:", line)
    slovar = json.loads(SLOVAR.read_text()) if SLOVAR.exists() else {}
    own = [tuple(p) for p in cfg.get("pravki", [])]
    # правка ролика сильнее общего словаря: то же слово в "pravki" отменяет запись словаря («Телеграм» → «Telegram» в словаре,
    # а в «Соцсети для сообществ» заголовок «из Телеграма» и строка «в Телеграм» — кириллицей, 2026-10-17)
    mine = {" ".join(normal(x) for x in src.split()) for src, _ in own}
    pravki = [(k, v) for k, v in slovar.items() if not k.startswith("_") and " ".join(normal(x) for x in k.split()) not in mine] + own
    used = set()
    words = apply_pravki(words, pravki, used)
    for src, dst in own:
        if src not in used:
            print(f"правка не сработала (в расшифровке нет): «{src}» → «{dst}»")
    for line in mark_razryvy(words, cfg.get("razryvy", [])):
        print(line)
    if yaping:
        yp_case(words)
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                                str(work / "итог.mp4")], capture_output=True, text=True).stdout)
    if yaping:
        # длина слоя — по ВИДЕО, а не по контейнеру: звук итога бывает на полкадра длиннее («Соцсеть для сообществ»:
        # видео 41,767 с = 1253 кадра, контейнер 41,784 с → слой в 1254 кадра и последняя фраза «до 41,80»). У «Извозчиков»
        # оба дают 2240 кадров. Прежние раскладки считают по контейнеру, как были (у «Дня 12» слой на кадр длиннее видео).
        vdur = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=duration",
                               "-of", "csv=p=0", str(work / "итог.mp4")], capture_output=True, text=True).stdout.strip()
        dur = float(vdur) if vdur not in ("", "N/A") else dur
    ubrat = cfg.get("ubrat", [])
    fr = lambda t: max(0, min(round(t * FPS), round(dur * FPS)))   # секунды → номер кадра

    # события: (кадр начала, кадр конца, картинка-слой)
    subs = []
    cs = chunks(words, breaks)
    gap = GAP_HOLD_KV if kvadrat or yaping else GAP_HOLD  # япинг: паузы вырезаны целиком, пустой экран на полсекунды — мигание
    txt = lambda c: shown(" ".join(x["w"] for x in c))
    hide = [(fr(u0), fr(u1)) for u0, u1 in ubrat]         # отрезки без субтитров — в кадрах
    cut_between = lambda c1, c2: any(c1[-1]["e"] <= t + CUT_EPS and c2[0]["s"] >= t - CUT_EPS for t in cuts)

    def timing(cs):
        """Когда каждая фраза на экране: [(кадр появления, кадр исчезновения, текст, номер фразы)] и предупреждения."""
        warn, subs = [], []
        starts = []  # начало звука первого слова каждой фразы
        for c in cs:
            v = voice_start(c[0]["s"], on, loud, c[0]["e"] if vdoh and no_stops(c[0]["w"]) else None)
            if v is None:
                warn.append(f"нет звука {VOICE_MAX} с после начала слова «{c[0]['w']}» ({c[0]['s']:.2f}) — время слова в итог_слова.json, похоже, неверно")
                v = c[0]["s"]
            starts.append(v)
        for i in range(len(cs) - 2, -1, -1):  # сдвиг к звуку не делает фразу короче MIN_SHOW (не мелькает): не позже следующей − 0,4 с,
            starts[i] = max(cs[i][0]["s"], min(starts[i], starts[i + 1] - MIN_SHOW))  # и не раньше слова по whisper («Смотри», №7)
        begins = [v - LEAD for v in starts]  # появление фразы: за 50 мс до звука первого слова
        # Склейка: субтитр меняется ровно на её кадре, а не за кадр-два до или после (двойной скачок — картинка, потом текст).
        # Первое слово звучит после склейки — упреждение за неё не заходит (иначе новая фраза кадр висит на старом плане);
        # фраза начинается вскоре после склейки (≤ CUT_SNAP), а прошлая до склейки договорена — ставится на склейку;
        # пауза после склейки длиннее — прошлая фраза гаснет на склейке, а не через четверть секунды на новом плане.
        for i, c in enumerate(cs):
            for t in edges:
                if starts[i] >= t - CUT_EPS and begins[i] < t:
                    begins[i] = t
                elif (t < begins[i] <= t + CUT_SNAP and (i == 0 or cs[i - 1][-1]["e"] <= t + CUT_EPS)
                      and (i == 0 or t - begins[i - 1] >= MIN_SHOW)):
                    begins[i] = t
        for i, c in enumerate(cs):
            a = begins[i]
            nxt = begins[i + 1] if i + 1 < len(cs) else dur
            b = min(nxt, max(c[-1]["e"] + HOLD_AFTER, a + MIN_SHOW))
            for t in edges:
                if c[-1]["e"] <= t + CUT_EPS and a < t < b:
                    b = max(t, a + MIN_SHOW)
            mid = (a + b) / 2
            if any(u0 <= mid <= u1 for u0, u1 in ubrat):
                continue
            subs.append((fr(a), fr(b), txt(c), i))
        # пустой экран между фразами короче gap — мигание: предыдущая держится до следующей (но не дальше склейки —
        # на новом плане прошлая фраза не висит)
        for i in range(len(subs) - 1):
            a, b, t, k = subs[i]
            nx = subs[i + 1][0]
            if 0 < nx - b < round(gap * FPS):
                subs[i] = (a, min([fr(x) for x in edges if b <= fr(x) < nx] + [nx]), t, k)
        # квадрат: после последней фразы до конца ролика меньше END_HOLD (хвост тишины, стоп-кадр) — стоит до последнего кадра
        if (kvadrat or yaping) and subs and 0 < fr(dur) - subs[-1][1] <= round(END_HOLD * FPS):
            subs[-1] = (subs[-1][0], fr(dur)) + subs[-1][2:]
        # япинг: в отрезке без субтитров (заголовок, вставка на весь кадр) субтитра нет ни в одном кадре — фраза, которая
        # осталась рядом, обрезается по его границе («и начинайте» после карточки: слово с 62,56, упреждение вывело бы
        # строку на 62,50 — на два последних кадра карточки)
        if yaping:
            cut_subs = []
            for a, b, t, k in subs:
                for u0, u1 in hide:
                    if u0 <= a < u1:
                        a = u1
                    if u0 < b <= u1 or a < u0 < b:
                        b = u0
                if b - a < round(MIN_SHOW * FPS):
                    warn.append(f"у отрезка без субтитров фраза «{t}» стоит {max(b - a, 0) / FPS:.2f} с — "
                                + ("убрана" if b <= a else "мелькнёт"))
                if b > a:
                    cut_subs.append((a, b, t, k))
            subs = cut_subs
        return subs, warn

    subs, warn = timing(cs)
    # Быстрая фраза (от READ_CPS знаков в секунду) сливается с соседней, если вместе они входят в одну строку и читаются
    # медленнее: «Примерно за пять часов» 0,92 с + «я его собрал» → одна фраза на 2 с. Не сливаем через конец предложения,
    # через склейку (новый план — новая фраза), через паузу без субтитра и через запятую перед «и/а/но» (новая часть
    # предложения: «любой книги, | и через пять дней я продал»). Квадрат — всегда; другая раскладка — "skorost": true.
    speed = cfg.get("skorost", kvadrat)
    rate = lambda a, b, t: len(t) * FPS / max(b - a, 1)
    while speed:
        on_air = {k: (a, b) for a, b, t, k in subs}
        cps = {k: rate(a, b, t) for a, b, t, k in subs}
        best = None
        for k in sorted((k for k in cps if cps[k] >= READ_CPS), key=lambda k: -cps[k]):
            for j in (k, k - 1):  # слить фразу j со следующей за ней
                if j < 0 or j not in on_air or j + 1 not in on_air:
                    continue
                c1, c2 = cs[j], cs[j + 1]
                if (re.search(r"[.!?]$", c1[-1]["w"]) or c1[-1].get("brk") or cut_between(c1, c2) or on_air[j][1] != on_air[j + 1][0]
                        or (re.search(r"[,;:—]$", c1[-1]["w"]) and normal(c2[0]["w"]) in COORD) or not fits(txt(c1 + c2))):
                    continue
                new = rate(on_air[j][0], on_air[j + 1][1], txt(c1 + c2))
                if new < cps[k] and (best is None or new < best[0]):
                    best = (new, j)
            if best:
                break
        if not best:
            break
        cs[best[1]:best[1] + 2] = [cs[best[1]] + cs[best[1] + 1]]
        subs, warn = timing(cs)
    for line in warn:
        print(line)
    if speed:
        for a, b, t, k in subs:
            if rate(a, b, t) >= READ_CPS:
                print(f"быстрая фраза: «{t}» — {len(t)} зн. за {(b - a) / FPS:.2f} с = {rate(a, b, t):.0f} зн/с (слить с соседней нельзя)")
    subs = [(a, b, t) for a, b, t, k in subs]
    # голос без субтитра — whisper грубо ошибся со временем слова: правилом это не чинится, только видно — пишем, где смотреть
    # (№4 интервью «испытывали» поставлено после склейки, на 1,25 с позже голоса; №3 «Следующий» — на 0,4 с позже голоса
    # после склейки; 2026-09-30). Время слова правится в итог_слова.json по огибающей и короткому окну whisper.
    covered = np.zeros(len(on), bool)
    for a, b, _ in subs:
        covered[round(a * 100 / FPS): round(b * 100 / FPS)] = True
    for u0, u1 in ubrat:
        covered[int(u0 * 100): int(u1 * 100)] = True
    heard = on.copy()
    if vdoh:  # вдох (звук, который так и не стал громким) — не голос: субтитра на нём нет, и не должно быть
        edge = np.flatnonzero(np.diff(np.concatenate(([0], on.astype(int), [0]))))
        for a0, b0 in zip(edge[::2], edge[1::2]):
            if not loud[a0:b0].any():
                heard[a0:b0] = False
    free = np.flatnonzero(heard & ~covered)
    if len(free):
        runs = np.split(free, np.flatnonzero(np.diff(free) > 10) + 1)  # перерыв < 0,1 с (слог, взрывной звук) — одно место
        for r in runs:
            g0, g1 = r[0] / 100, (r[-1] + 1) / 100
            if g1 - g0 >= BLANK_MAX:
                w0 = next((x["w"] for x in reversed(words) if x["s"] < g0), "—")
                w1 = next((x["w"] for x in words if x["s"] >= g0), "—")
                print(f"голос без субтитра {g0:.2f}–{g1:.2f} с (между «{w0}» и «{w1}») — время слова в итог_слова.json, похоже, неверно")
    # смена субтитра в 1…CUT_NEAR кадрах от склейки, но не на ней, — двойной скачок (картинка, потом текст): смотреть это место
    changes = {a: f"появляется «{t}»" for a, b, t in subs}
    for a, b, t in subs:
        changes.setdefault(b, f"гаснет «{t}»")
    for t in edges:
        for k, what in sorted(changes.items()):
            if 0 < abs(k - fr(t)) <= CUT_NEAR:
                print(f"у склейки {t:.2f} (кадр {fr(t)}) {what} на кадре {k} — в {abs(k - fr(t))} кадр. от неё, мелькнёт на границе")
    titles = [(fr(z["from"]), fr(z["to"]), z["text"], z.get("sub")) for z in cfg.get("zagolovki", [])]
    # интервью, квадрат: заголовок (в интервью ещё рубрика) — с первого до последнего кадра, один слой под всеми субтитрами
    header = (iv_header(cfg.get("rubrika"), cfg.get("zagolovok", {})) if interview
              else kv_header(cfg.get("zagolovok", {}), kv_video) if kvadrat else None)

    # раскладка по кадрам: на каждом кадре — какой субтитр и какой заголовок; одинаковые подряд — один PNG с длительностью
    n = fr(dur)
    state = []
    if yaping:
        # заголовок стоит с "ot" до "do" и уходит без анимации; высота субтитра — по крупности плана в этом кадре
        zag = cfg.get("zagolovok")
        yp_head, yp_from, yp_to = None, 0, 0
        if zag:
            (yp_head, hbox), yp_from, yp_to = yp_header(zag), fr(zag.get("ot", 0)), fr(zag["do"])
            print(f"заголовок: кадры {yp_from}–{yp_to - 1}, буквы x {hbox[0]}–{hbox[2]}, y {hbox[1]}–{hbox[3]}")
        vys = cfg.get("vysota")
        assert vys is not None, 'япинг: в титры.json нужна "vysota" — середина букв субтитра (число или {"крупность": y})'
        vst_fr = [(fr(a), fr(b), y, pl, cv) for a, b, y, _, pl, cv in vst]  # вставка: кадры [начало, конец), высота, тень, цвет
        if isinstance(vys, list):
            # [[с секунды, y], …] — высота по кускам: дубли сидят по-разному, строка — под подбородком своего куска
            # (Арон, 2026-10-19: «поднять субтитры повыше»); секунда должна быть склейкой — строка меняет место вместе с кадром
            cuts = {fr(t0) for t0, _ in plans}
            vys_fr = sorted((fr(t0), y) for t0, y in vys)
            off = [f0 for f0, _ in vys_fr if f0 and f0 not in cuts]
            assert vys_fr[0][0] == 0 and not off, f'япинг: "vysota" по кускам — первая с 0, остальные на склейках (не склейка: кадры {off})'
            y_plan = lambda k: [y for f0, y in vys_fr if f0 <= k][-1]
        else:
            vys = {float(z): y for z, y in vys.items()} if isinstance(vys, dict) else {z: vys for _, z in plans}
            miss = sorted({z for _, z in plans} - set(vys))
            assert not miss, f'япинг: в "vysota" нет высоты для крупности {miss} (крупности планов — в склейки.txt)'
            plan_fr = [(fr(t0), z) for t0, z in plans]      # план начинается на кадре своей склейки
            y_plan = lambda k: vys[[z for f0, z in plan_fr if f0 <= k][-1]]
        y_at = lambda k: next((y for a, b, y, _, _ in vst_fr if a <= k < b), None) or y_plan(k)
        ten_at = lambda k: next((pl for a, b, _, pl, _ in vst_fr if a <= k < b), None)   # None — общая тень
        cvet_at = lambda k: next((cv for a, b, _, _, cv in vst_fr if a <= k < b), None)  # None — общий цвет
        yp_green = [shown(g).split() for g in cfg.get("zelenoe", [])]
        yp_found = set()
        for a, b, t in subs:
            jump = [k for k in range(a + 1, b) if y_at(k) != y_at(k - 1)]
            if jump:
                print(f"фраза «{t}» ({a / FPS:.2f}–{b / FPS:.2f}) стоит через смену высоты строки (кадр {jump[0]}: склейка "
                      "со сменой крупности или край вставки) — строка прыгнет на этом кадре")
    for k in range(n):
        s = next((t for a, b, t in subs if a <= k < b), None)
        if yaping:
            state.append(((s, y_at(k), ten_at(k), cvet_at(k)) if s else None, yp_head is not None and yp_from <= k < yp_to))
            continue
        z = next(((t, u) for a, b, t, u in titles if a <= k < b), None)
        state.append((s, z))
    tmp = Path(tempfile.mkdtemp(prefix="titry_"))
    cache, lines, runs, k = {}, [], [], 0
    while k < n:
        j = k
        while j < n and state[j] == state[k]:
            j += 1
        key = state[k]
        if key not in cache:
            img = header.copy() if header is not None else Image.new("RGBA", (W, H), (0, 0, 0, 0))
            if yaping:
                if key[1]:
                    img.alpha_composite(yp_head)
                if key[0]:
                    img.alpha_composite(yp_line(key[0][0], YP_FONT["kegl"], key[0][1], yp_green, yp_found, key[0][2], key[0][3])[0])
            elif key[1]:
                img.alpha_composite(plate(key[1][0], key[1][1], TITLE_Y, TITLE_SIZE, TITLE_WEIGHT, alpha=175))
            if yaping:
                pass
            elif key[0] and interview:
                img.alpha_composite(iv_sub(key[0]))
            elif key[0] and kvadrat:
                img.alpha_composite(iv_sub(key[0], kv_geometry(kv_video)[2], kv_video))
            elif key[0]:
                img.alpha_composite(plate(key[0], None, SUB_Y, SUB_SIZE, SUB_WEIGHT))
            p = tmp / f"{len(cache):04d}.png"
            img.save(p)
            cache[key] = p
        lines.append(f"file '{cache[key]}'\nduration {(j - k) / FPS:.6f}\n")
        runs.append((cache[key], j - k))
        k = j
    lines.append(f"file '{cache[state[-1]]}'\n")
    (tmp / "list.txt").write_text("".join(lines))
    out = work / "титры.mov"
    if yaping:
        # Кадр в кадр: картинки идут в ffmpeg потоком, по одной на каждый кадр ролика. Через список картинок с длительностями
        # (как ниже) время смены округляется до сетки 1/25 с читалки картинок, и в ролике на 30 кадров/с смена на кадре вида
        # 6k + 3 выходит на соседний кадр — не тот, что в субтитры.txt (25 кадров/с — точно). Здесь это была бы строка нового
        # плана на последнем кадре старого, на новой высоте — скачок виден. Проверка слоя по кадрам, 2026-10-13: в этом
        # ролике 8 смен из 55 вышли на кадр раньше, из них 3 на склейках со сменой крупности; в «Дне 12» 8 из 57 и
        # в интервью № 1 4 из 34 — на кадр позже (там слой не пересобирался: утверждённые ролики не меняем).
        enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}",
                                "-framerate", fps_arg, "-i", "-", "-vf", "format=argb", "-c:v", "qtrle", str(out)],
                               stdin=subprocess.PIPE)
        for png, count in runs:
            data = Image.open(png).convert("RGBA").tobytes()
            for _ in range(count):
                enc.stdin.write(data)
        enc.stdin.close()
        assert enc.wait() == 0, "ffmpeg не записал титры.mov"
        # сверка записанного слоя: кадров столько же, и картинка меняется ровно на тех кадрах, что в раскладке
        md5 = [row.rsplit(",", 1)[-1].strip() for row in subprocess.run(
            ["ffmpeg", "-v", "error", "-i", str(out), "-f", "framemd5", "-"], capture_output=True, text=True).stdout.splitlines()
            if row and not row.startswith("#")]
        got = [i for i in range(1, len(md5)) if md5[i] != md5[i - 1]]
        want, acc = [], 0
        for _, count in runs[:-1]:
            acc += count; want.append(acc)
        assert len(md5) == n and got == want, (f"слой титры.mov не совпал с раскладкой: кадров {len(md5)} из {n}, смены не на своих "
                                               f"кадрах: {sorted(set(got) ^ set(want))[:10]}")
    else:
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(tmp / "list.txt"),
                        "-vf", f"fps={fps_arg},format=argb", "-c:v", "qtrle", "-t", f"{dur:.3f}", str(out)], check=True)
    (work / "субтитры.txt").write_text("\n".join(f"{a / FPS:6.2f}–{b / FPS:6.2f}  {t}" for a, b, t in subs) + "\n")
    if yaping:
        lost = [" ".join(g) for gi, g in enumerate(yp_green) if gi not in yp_found]
        if lost:
            print(f"зелёных слов нет ни в одной фразе (фраза разбита иначе?): {lost}")
    print(f"субтитров {len(subs)}, заголовков {len(titles) + bool(header) + bool(yaping and cfg.get('zagolovok'))}, "
          f"сетка {fps_arg} кадр/с → {out}")


if __name__ == "__main__":
    main()
