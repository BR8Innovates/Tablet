const { chromium } = require('/opt/node-tools/node_modules/playwright');
const { execSync } = require('child_process'); const fs = require('fs');
const TOK = JSON.parse(execSync('imo auth prepare --profile portal:uponly --json')).access_token;
const REAL = 'https://portal-gw.insuremo.com/platform/api-orchestration-test/v1/flow';
const PAGE = 'file:///home/user/Tablet/uic_pages/uponly/portal/sohar-insurance-portal/index.html';
fs.mkdirSync('shots5', { recursive: true });
(async () => {
  const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome' }).catch(() => chromium.launch());
  const out = []; const ok = (n, c, x) => { out.push({ n, ok: !!c }); console.log((c ? 'PASS ' : 'FAIL ') + n + (x ? ' | ' + String(x).slice(0, 120) : '')); };
  async function mk(withPortalToken) {
    const ctx = await browser.newContext({ viewport: { width: 1300, height: 900 } });
    await ctx.addInitScript(([t, w]) => { if (w) sessionStorage.setItem('Authorization', 'Bearer ' + t); sessionStorage.setItem('sohar_api_base', 'https://fake-gw.test/platform/api-orchestration-test/v1/flow'); }, [TOK, withPortalToken]);
    const proxy = async (route, url) => { const req = route.request(); const r = await fetch(url, { method: req.method(), headers: Object.assign({ 'Content-Type': 'application/json' }, req.headers()['authorization'] ? { Authorization: req.headers()['authorization'] } : {}, req.headers()['x-mo-tenant-id'] ? { 'x-mo-tenant-id': req.headers()['x-mo-tenant-id'], 'x-mo-user-source-id': 'platform' } : {}), body: req.method() === 'GET' ? undefined : req.postData() }); await route.fulfill({ status: r.status, headers: { 'content-type': r.headers.get('content-type') || 'application/json', 'access-control-allow-origin': '*' }, body: Buffer.from(await r.arrayBuffer()) }); };
    await ctx.route('https://fake-gw.test/**', route => proxy(route, REAL + route.request().url().split('/v1/flow')[1]));
    await ctx.route('https://portal-gw.insuremo.com/cas/**', route => proxy(route, route.request().url()));
    return ctx;
  }
  try {
    let ctx = await mk(true), page = await ctx.newPage(); const errs = []; page.on('pageerror', e => errs.push(e.message));
    await page.goto(PAGE); await page.waitForSelector('#loginForm');
    ok('login screen is shown first', await page.locator('#loginScreen').isVisible() && !(await page.locator('#side button').count()));
    ok('InsureMO-session button offered when a portal session exists', await page.locator('#lg_session').isVisible());
    await page.screenshot({ path: 'shots5/01_login.png' });
    await page.click('#lg_go'); ok('empty form is refused', /Enter your user name and password/.test(await page.textContent('#loginMsg')));
    await page.fill('#lg_user', 'nobody@example.com'); await page.fill('#lg_pass', 'wrong-password-123'); await page.click('#lg_go'); await page.waitForFunction(() => /Sign-in failed|not available|could not be reached/.test(document.getElementById('loginMsg').textContent), null, { timeout: 30000 });
    const m = await page.textContent('#loginMsg'); ok('wrong password gives a plain message and stays on the login screen', /Sign-in failed/.test(m) && await page.locator('#loginScreen').isVisible(), m);
    ok('no menu or data before sign-in', !(await page.locator('#side button').count()));
    await page.screenshot({ path: 'shots5/02_login_failed.png' });
    const stored = await page.evaluate(() => JSON.stringify(Object.assign({}, sessionStorage)) + document.cookie); ok('password is not stored', !stored.includes('wrong-password-123'));
    await page.click('#lg_session'); await page.waitForSelector('#d_body .tiles', { timeout: 90000 });
    ok('continue with the InsureMO session opens the dashboard', !(await page.locator('#loginScreen').isVisible()) && /Maker/.test(await page.textContent('#userChip')), await page.textContent('#userChip'));
    ok('sign-out button visible', await page.locator('#btnSignOut').isVisible()); await page.screenshot({ path: 'shots5/03_in.png' });
    page.on('dialog', d => d.accept());
    await page.click('#btnSignOut'); await page.waitForSelector('#loginForm'); await page.waitForSelector('#loginMsg .alert');
    ok('sign out returns to the login screen with a message', /signed out/.test(await page.textContent('#loginMsg')) && await page.locator('#loginScreen').isVisible(), await page.textContent('#loginMsg'));
    ok('no console errors', errs.length === 0, errs.join('|')); await ctx.close();
    ctx = await mk(false); page = await ctx.newPage(); await page.goto(PAGE); await page.waitForSelector('#loginForm');
    ok('no InsureMO session: only the user name / password form', !(await page.locator('#lg_session').isVisible())); await ctx.close();
  } catch (e) { ok('exception', false, e.message.slice(0, 300)); }
  console.log(out.filter(o => o.ok).length + ' of ' + out.length + ' passed'); await browser.close();
})();
