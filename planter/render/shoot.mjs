// 저장소 루트를 가상 주소로 내보내고 미리보기를 PNG 로 찍는다 (서버 없이).
// node planter/render/shoot.mjs out.png "/planter/render/preview.html?parts=..." 1600 1000
import { createRequire } from 'node:module';
import { readFileSync, existsSync } from 'node:fs';
import { extname, join, normalize } from 'node:path';
const { chromium } = createRequire(import.meta.url)('playwright');
const ROOT = new URL('../..', import.meta.url).pathname;
const [out, url, w = '1600', h = '1000'] = process.argv.slice(2);
const TYPES = { '.html': 'text/html', '.js': 'text/javascript', '.json': 'application/json', '.stl': 'application/octet-stream' };
const browser = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
const page = await browser.newPage({ viewport: { width: +w, height: +h }, deviceScaleFactor: 2 });
await page.route('http://planter.local/**', route => {
  const rel = normalize(decodeURIComponent(new URL(route.request().url()).pathname)).replace(/^\/+/, '');
  const file = join(ROOT, rel);
  if (!file.startsWith(ROOT) || !existsSync(file)) return route.fulfill({ status: 404, body: 'not found' });
  route.fulfill({ status: 200, body: readFileSync(file), contentType: TYPES[extname(file)] || 'application/octet-stream' });
});
page.on('pageerror', e => console.error('pageerror', e.message));
page.on('console', m => { if (m.type() === 'error') console.error(m.text()); });
await page.goto('http://planter.local' + url);
await page.waitForFunction(() => window.__done === true, null, { timeout: 300000 });
await page.screenshot({ path: out });
await browser.close();
console.log('wrote', out);
