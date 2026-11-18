// 렌더 페이지를 열어 PNG로 저장한다. 서버를 띄우지 않고, 가상 주소 요청을
// bookshelf 폴더의 파일로 바로 응답한다.
// 사용법: node render/shoot.mjs [hero front detail silhouette growth]
import { createRequire } from 'node:module';
import { mkdirSync, readFileSync, existsSync } from 'node:fs';
import { extname, join, normalize } from 'node:path';

const { chromium } = createRequire(import.meta.url)('playwright');

const ROOT = new URL('..', import.meta.url).pathname;   // bookshelf/
const BASE = 'http://bookshelf.local';
const OUT = join(ROOT, 'renders/');
mkdirSync(OUT, { recursive: true });
const TYPES = { '.html': 'text/html', '.js': 'text/javascript', '.json': 'application/json',
                '.stl': 'application/octet-stream', '.css': 'text/css' };

const shots = [
  { name: 'hero',       url: '/render/render.html?view=hero&w=1600&h=1200',  w: 1600, h: 1200 },
  { name: 'front',      url: '/render/render.html?view=front&w=1000&h=1200', w: 1000, h: 1200 },
  { name: 'detail',     url: '/render/render.html?view=detail&id=27&w=1800&h=1000', w: 1800, h: 1000 },
  { name: 'silhouette', url: '/render/drawing.html?fig=silhouette', w: 1600, h: 1160 },
  { name: 'growth',     url: '/render/drawing.html?fig=growth',     w: 1800, h: 900 },
];
const only = process.argv.slice(2);

const browser = await chromium.launch({
  args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'],
});
for (const s of shots) {
  if (only.length && !only.includes(s.name)) continue;
  const page = await browser.newPage({ viewport: { width: s.w, height: s.h }, deviceScaleFactor: 2 });
  await page.route(`${BASE}/**`, route => {
    const rel = normalize(decodeURIComponent(new URL(route.request().url()).pathname)).replace(/^\/+/, '');
    const file = join(ROOT, rel);
    if (!file.startsWith(ROOT) || !existsSync(file)) return route.fulfill({ status: 404, body: 'not found' });
    route.fulfill({ status: 200, body: readFileSync(file),
                    contentType: TYPES[extname(file)] || 'application/octet-stream' });
  });
  page.on('pageerror', e => console.error(s.name, 'pageerror', e.message));
  page.on('console', m => { if (m.type() === 'error') console.error(s.name, m.text()); });
  const t = Date.now();
  await page.goto(BASE + s.url);
  await page.waitForFunction(() => window.__done === true, null, { timeout: 300000 });
  await page.waitForTimeout(300);
  await page.screenshot({ path: `${OUT}${s.name}.png` });
  console.log(s.name, `${((Date.now() - t) / 1000).toFixed(1)}s`);
  await page.close();
}
await browser.close();
