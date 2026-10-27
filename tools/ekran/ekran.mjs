// Съёмка сайта в формате телефона по сценарию: кадр на каждое действие + где на экране место действия.
//   node tools/ekran/ekran.mjs <сценарий.json> <папка вывода>
//   node tools/ekran/ekran.mjs --vhod <адрес> …        — окно для входа Арона в аккаунты (один раз)
// "needLogin": false в сценарии — снимать и без входа (публичные страницы).
// Сценарий: {"url": "...", "steps": [ {"do": "...", ...}, ... ]}
//   {"do":"shot", "hold":1.0, "focus":"<селектор>|page|{x,y,w,h}"} — показать экран hold секунд (focus-прямоугольник — CSS px)
//   {"do":"tap", "sel":"<селектор>", "hold":0.6, "focus":"…", "focusAfter":"…"} — нажать (в кадре жёлтый «палец»);
//      в центре держим блок вокруг кнопки (focus), после нажатия — то, что открылось (focusAfter)
//   {"do":"type", "text":"...", "focus":"<селектор>", "cps":24} — печатать; кадр на каждые 2 буквы
//   {"do":"key", "key":"Escape"} · {"do":"wait", "ms":800} · {"do":"hidden", "sel":"…"} — дождаться, что блок закрылся
//   После tap с focusAfter инструмент ждёт, пока открывшийся блок появится и перестанет двигаться.
// Селекторы — Playwright: css, "role=button[name=\"…\"]", "text=…".
// Выход: frames/*.jpg (1290×… px) и кадры.json: [{file, hold (с), focus:{x,y,w,h} в px скриншота, group}]
// Дальше: python3 tools/ekran/kamera.py <папка> → вставка 9:16, где место действия всегда в центре.
import { chromium, devices } from 'playwright'; // npm i playwright (рядом с проектом или глобально)
import fs from 'fs';
import os from 'os';

// Профиль для записи: здесь хранятся входы Арона в аккаунты (ChatGPT и др.). Вне проекта, в git не попадает.
// Вход делает сам Арон: node tools/ekran/ekran.mjs --vhod https://chatgpt.com [ещё адреса…] — окно Chrome, войти, закрыть окно.
const PROFILE = `${os.homedir()}/Library/Application Support/reels-montazher/профиль-записи`;
fs.mkdirSync(PROFILE, { recursive: true });

if (process.argv[2] === '--vhod') {
  const ctx = await chromium.launchPersistentContext(PROFILE, { channel: 'chrome', headless: false, viewport: null, locale: 'ru-RU' });
  const urls = process.argv.slice(3);
  const first = ctx.pages()[0] ?? await ctx.newPage();
  for (const [i, u] of urls.entries()) await (i === 0 ? first : await ctx.newPage()).goto(u);
  console.log('Окно открыто: войди в аккаунты и закрой окно Chrome.');
  await new Promise(r => ctx.on('close', r));
  console.log('Вход сохранён в профиле записи.');
  process.exit(0);
}

const [scenarioPath, out] = process.argv.slice(2);
const sc = JSON.parse(fs.readFileSync(scenarioPath, 'utf8'));
fs.mkdirSync(`${out}/frames`, { recursive: true });
// "device": "desktop" — десктопная версия (1920×1080, Retina ×2), иначе iPhone 15 Pro Max (×3).
// "zoom": 1.75 — масштаб страницы, как Cmd+«плюс»: вёрстка та же, текст крупнее (для десктопа в 9:16).
const DESKTOP = sc.device === 'desktop';
const DPR = DESKTOP ? 2 : 3;
const dev = DESKTOP ? { viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 2 } : devices['iPhone 15 Pro Max'];

// Установленный Google Chrome, невидимо, профиль записи (с входами Арона)
const ctx = await chromium.launchPersistentContext(PROFILE, { channel: 'chrome', ...dev, locale: 'ru-RU' });
const page = ctx.pages()[0] ?? await ctx.newPage();
if (sc.zoom) await page.addInitScript(z => {
  const set = () => { document.documentElement.style.zoom = z; };
  document.documentElement ? set() : addEventListener('DOMContentLoaded', set);
}, sc.zoom);
await page.addInitScript(() => {  // личное не в кадр: названия чатов и проектов в боковой панели размыты
  const css = 'a[href^="/c/"], a[href*="/c/"], a[href^="/g/"], [data-testid^="history-item"] { filter: blur(7px) !important; }';
  const add = () => { const s = document.createElement('style'); s.textContent = css; document.documentElement.appendChild(s); };
  document.documentElement ? add() : addEventListener('DOMContentLoaded', add);
});
await page.addInitScript(() => {  // видимый «палец» в месте нажатия — в headless нет курсора
  addEventListener('pointerdown', e => {
    const d = document.createElement('div');
    d.style.cssText = `position:fixed;left:${e.clientX - 24}px;top:${e.clientY - 24}px;width:48px;height:48px;border-radius:50%;background:rgba(255,200,0,.45);border:3px solid #ffb300;z-index:2147483647;pointer-events:none;transition:all .5s`;
    document.documentElement.appendChild(d);
    setTimeout(() => { d.style.opacity = 0; d.style.transform = 'scale(1.6)'; }, 350);
    setTimeout(() => d.remove(), 900);
  }, true);
});

let n = 0, group = 0;
const frames = [];
// Место действия для камеры — не сама мелкая кнопка, а понятный блок вокруг неё (панель ввода, шапка, меню):
// поднимаемся по родителям, пока блок не станет шириной ≥ половины экрана; высоту не раздуваем больше 60 % экрана.
const boxOf = async sel => {
  if (!sel || sel === 'page') return null;
  // прямоугольник вручную (CSS px страницы): {"x":0,"y":0,"w":430,"h":200} — например, весь верх сайта-витрины
  if (typeof sel === 'object') return { x: sel.x * DPR, y: sel.y * DPR, w: sel.w * DPR, h: sel.h * DPR };
  const b = await page.locator(sel).first().evaluate(el => {
    const vw = innerWidth, vh = innerHeight;
    let r = el.getBoundingClientRect(), cur = el;
    while (r.width < vw * 0.5 && cur.parentElement && cur.parentElement !== document.body) {
      const pr = cur.parentElement.getBoundingClientRect();
      if (pr.height > vh * 0.6) break;
      cur = cur.parentElement; r = pr;
    }
    return { x: r.x, y: r.y, width: r.width, height: r.height };
  }).catch(() => null);
  return b && { x: b.x * DPR, y: b.y * DPR, w: b.width * DPR, h: b.height * DPR };
};
// Ждать, пока блок появится и перестанет двигаться (анимации выезда меню и т. п.) — вместо слепых пауз
const settle = async sel => {
  const loc = page.locator(sel).first();
  await loc.waitFor({ state: 'visible', timeout: 10000 });
  let prev = null;
  for (let i = 0; i < 40; i++) {
    const b = await loc.boundingBox();
    if (prev && b && Math.abs(b.x - prev.x) < 0.5 && Math.abs(b.y - prev.y) < 0.5 && Math.abs(b.width - prev.width) < 0.5) break;
    prev = b; await page.waitForTimeout(80);
  }
};
const shot = async (hold, focusSel) => {
  const file = `frames/${String(++n).padStart(4, '0')}.jpg`;
  await page.screenshot({ path: `${out}/${file}`, type: 'jpeg', quality: 93 });
  frames.push({ file, hold, focus: await boxOf(focusSel), group });
};

await page.goto(sc.url, { waitUntil: 'domcontentloaded' });
// cookie и подобное — закрыть до первого кадра, «только обязательные»
const cookie = page.getByRole('button', { name: /только обязательные|^отклонить$|only necessary|reject/i }).first();
try { await cookie.waitFor({ state: 'visible', timeout: 8000 }); await cookie.click(); await cookie.waitFor({ state: 'hidden', timeout: 5000 }); } catch {}
await page.waitForTimeout(1200);
// Вход слетел — не снимаем чужой экран «Войти», просим Арона войти заново
if (sc.needLogin !== false && await page.getByRole('button', { name: /^(Войти|Log in)$/ }).first().isVisible().catch(() => false)) {
  console.error('НУЖЕН ВХОД: в профиле записи нет входа на этот сайт. Запусти: node tools/ekran/ekran.mjs --vhod ' + sc.url);
  await ctx.close(); process.exit(2);
}

for (const s of sc.steps) {
  group++;
  if (s.do === 'shot') await shot(s.hold ?? 1, s.focus);
  else if (s.do === 'wait') await page.waitForTimeout(s.ms ?? 500);
  else if (s.do === 'key') await page.keyboard.press(s.key);
  else if (s.do === 'hidden') { await page.locator(s.sel).first().waitFor({ state: 'hidden', timeout: 10000 }); await page.waitForTimeout(150); }
  else if (s.do === 'tap') {
    const f = s.focus ?? s.sel;                         // focus — блок, который держим в центре (по умолчанию вокруг кнопки)
    await shot(s.before ?? 0.5, f);                     // камера сначала приезжает к месту нажатия
    await (DESKTOP ? page.locator(s.sel).first().click() : page.locator(s.sel).first().tap());
    await page.waitForTimeout(120);
    await shot(0.35, f);                                // кадр с «пальцем»
    if (s.focusAfter) await settle(s.focusAfter); else await page.waitForTimeout(s.wait ?? 700);
    await shot(s.hold ?? 0.6, s.focusAfter ?? f);       // что открылось
  } else if (s.do === 'type') {
    const step = 1 / (s.cps ?? 24) * 2;
    for (let i = 0; i < s.text.length; i += 2) { await page.keyboard.type(s.text.slice(i, i + 2)); await shot(step, s.focus); }
    await shot(s.hold ?? 1, s.focus);
  }
}
fs.writeFileSync(`${out}/кадры.json`, JSON.stringify({ viewport: page.viewportSize(), dpr: DPR, frames }, null, 1));
await ctx.close();
console.log(`кадров ${frames.length} → ${out}`);
