"""Съёмка из Chrome Арона (его аккаунты) — кадры в формате ekran.mjs, дальше kamera.py.

Действия на странице делает Claude через Claude в Chrome; этот скрипт только снимает окно записи.
Окно записи — отдельное окно Chrome 520×960 с группой вкладок Claude (создаётся через AppleScript, см.
docs/запись_экрана.md). Chrome не рисует закрытые окна, поэтому на время съёмки окно выходит вперёд.

    python3 tools/ekran/okno.py start <папка>                 — окно вперёд, новая съёмка
    python3 tools/ekran/okno.py shot  <папка> <hold> <группа> <innerH> [x y w h]  — кадр; x y w h — место действия, px кадра
                                                                  innerH 0 — окно целиком, с адресной строкой
    python3 tools/ekran/okno.py stop  <папка>                 — Claude обратно вперёд
"""
import json, subprocess, sys, time
from pathlib import Path
from PIL import Image

EDGE = 14  # по краям страницы Claude в Chrome рисует розовое свечение «управляю вкладкой» — обрезаем
import os
W_REC, H_REC = int(os.environ.get('OKNO_W', 520)), int(os.environ.get('OKNO_H', 960))  # OKNO_W=1280 — десктоп для длинных текстов  # размер окна записи — по нему находим окно среди окон Chrome (узкое: ChatGPT перестраивается, текст крупнее относительно колонки)


def window_id():
    """Номер окна записи для screencapture: окно Google Chrome размером 520×960."""
    out = subprocess.run([str(Path(__file__).parent / "okna")], capture_output=True, text=True).stdout
    for line in out.splitlines():
        p = line.split()
        if len(p) >= 5 and int(float(p[3])) == W_REC and int(float(p[4])) == H_REC:
            return p[0]
    sys.exit("Окно записи не найдено (Chrome 520×960). Создать заново — см. docs/запись_экрана.md")


def osa(script):
    subprocess.run(["osascript", "-e", script], check=True, capture_output=True)


def main():
    cmd, folder = sys.argv[1], Path(sys.argv[2])
    meta = folder / "кадры.json"
    if cmd == "start":
        (folder / "frames").mkdir(parents=True, exist_ok=True)
        wid = window_id()
        # окно записи — первым окном Chrome и Chrome вперёд; Арону на это время мышь и клавиатуру не трогать
        osa(f'tell application "Google Chrome"\nrepeat with w in windows\nset b to bounds of w\n'
            f'if (item 3 of b) - (item 1 of b) = {W_REC} and (item 4 of b) - (item 2 of b) = {H_REC} then set index of w to 1\n'
            f'end repeat\nactivate\nend tell')
        time.sleep(1.2)
        meta.write_text(json.dumps({"window": wid, "dpr": 1, "frames": []}, ensure_ascii=False, indent=1))
        print("окно", wid, "впереди")
    elif cmd == "shot":
        d = json.loads(meta.read_text())
        hold, group, inner_h = float(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5])
        n = len(d["frames"]) + 1
        raw = folder / "frames" / f"raw_{n:04d}.png"
        subprocess.run(["screencapture", "-x", "-o", "-l", d["window"], str(raw)], check=True)
        img = Image.open(raw).convert("RGB")
        if inner_h > 0:  # только страница, без вкладок и адресной строки; 0 — окно целиком (кадр с адресом сайта)
            img = img.crop((0, img.height - inner_h, img.width, img.height))
            img = img.crop((EDGE, EDGE, img.width - EDGE, img.height - EDGE))
        f = f"frames/{n:04d}.jpg"
        img.save(folder / f, quality=93)
        raw.unlink()
        focus = None
        if len(sys.argv) >= 10:
            x, y, w, h = map(float, sys.argv[6:10])
            off = EDGE if inner_h > 0 else 0
            focus = {"x": x - off, "y": y - off, "w": w, "h": h}
        d["frames"].append({"file": f, "hold": hold, "focus": focus, "group": group})
        meta.write_text(json.dumps(d, ensure_ascii=False, indent=1))
        print(f, img.size)
    elif cmd == "stop":
        osa('tell application "Claude" to activate')
        print("Claude впереди")


if __name__ == "__main__":
    main()
