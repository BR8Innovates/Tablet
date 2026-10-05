const { chromium } = require('/opt/node-tools/node_modules/playwright');
const { execSync } = require('child_process');
const fs = require('fs');
const TOK = JSON.parse(execSync('imo auth prepare --profile portal:uponly --json')).access_token;
const REAL = 'https://portal-gw.insuremo.com/platform/api-orchestration-test/v1/flow';
const PAGE = 'file:///home/user/Tablet/uic_pages/uponly/portal/sohar-insurance-portal/index.html';
const only = process.argv[2] ? process.argv[2].split(',') : ['UPPA001','TL001','FP001','HC001','CI001','LP001','DH001'];
const shotDir = process.argv[3] || 'shots'; fs.mkdirSync(shotDir, { recursive: true });
(async () => {
  const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome' }).catch(() => chromium.launch());
  const results = [];
  for (const prod of only) {
    const ctx = await browser.newContext({ viewport: { width: 1280, height: 1000 }, acceptDownloads: true });
    await ctx.addInitScript(t => { sessionStorage.setItem('Authorization', 'Bearer ' + t); sessionStorage.setItem('sohar_api_base', 'https://fake-gw.test/platform/api-orchestration-test/v1/flow'); }, TOK);
    await ctx.route('https://fake-gw.test/**', async route => {
      const req = route.request(); const url = REAL + req.url().split('/v1/flow')[1];
      const r = await fetch(url, { method: req.method(), headers: { Authorization: 'Bearer ' + TOK, 'Content-Type': 'application/json' }, body: req.method() === 'GET' ? undefined : req.postData() });
      const buf = Buffer.from(await r.arrayBuffer());
      await route.fulfill({ status: r.status, headers: { 'content-type': r.headers.get('content-type') || 'application/json', 'access-control-allow-origin': '*' }, body: buf });
    });
    const page = await ctx.newPage(); const errs = []; page.on('console', m => { if (m.type() === 'error') errs.push(m.text()); }); page.on('pageerror', e => errs.push('PAGEERR ' + e.message));
    const log = { product: prod, steps: [] }; const ok = (n, c, extra) => { log.steps.push({ n, ok: !!c, extra }); if (!c) console.log('  FAIL', prod, n, extra || ''); };
    try {
      await page.goto(PAGE); await page.waitForSelector('#q_product option', { state: 'attached', timeout: 30000 });
      ok('carrier chip', /Afillar/.test(await page.textContent('#carrierChip')));
      await page.selectOption('#q_product', prod);
      const nvar = await page.locator('#q_variant option').count();
      await page.fill('#q_name', 'Test Customer'); await page.fill('#q_dob', '1990-05-05');
      if (prod === 'FP001') ok('female locked', await page.locator('#q_gender').isDisabled());
      // negative: under age
      await page.fill('#q_dob', '2015-05-05'); await page.click('#btnQuote'); ok('age rule blocks', /Age at start/.test(await page.textContent('#e_q_dob')));
      await page.fill('#q_dob', '1990-05-05');
      await page.click('#btnQuote'); await page.waitForSelector('#plans .plan', { timeout: 60000 });
      const np = await page.locator('#plans .plan').count(); ok('plans', np > 0, np + ' plans, ' + nvar + ' variants');
      await page.screenshot({ path: `${shotDir}/${prod}_1_quote.png`, fullPage: true });
      await page.locator('#plans .plan').first().click(); await page.click('#btnToProposal');
      await page.fill('#p_cif', '45678'); await page.fill('#p_idno', '123456789'); await page.fill('#p_mobile', '9989374444'); await page.fill('#p_email', 'test@example.com'); await page.fill('#p_addr', 'Muscat'); await page.fill('#p_post', '100345'); await page.fill('#b_name', 'Sayyed Test'); await page.fill('#pay_acc', '896236508');
      await page.click('#btnCreateProp'); await page.waitForSelector('#propResult .alert', { timeout: 90000 });
      const pr = await page.textContent('#propResult'); ok('proposal created', /P[A-Z0-9]{5,}/.test(pr), pr.replace(/\s+/g, ' ').slice(0, 120));
      await page.screenshot({ path: `${shotDir}/${prod}_2_proposal.png`, fullPage: true });
      const [dl] = await Promise.all([page.waitForEvent('download', { timeout: 90000 }), page.click('#btnAppDoc')]); const p1 = await dl.path(); ok('application pdf', fs.readFileSync(p1).slice(0, 4).toString() === '%PDF');
      await page.click('#btnUpdateProp'); await page.waitForSelector('#propResult .alert:has-text("updated")', { timeout: 90000 }); ok('proposal updated', true);
      await page.click('#btnToIssue'); page.once('dialog', d => d.accept()); await page.click('#btnIssue'); await page.waitForSelector('#issueResult .alert', { timeout: 120000 });
      const is = await page.textContent('#issueResult'); const pol = (is.match(/PO[A-Z]+\d+/) || [])[0]; ok('policy issued', !!pol, pol);
      await page.screenshot({ path: `${shotDir}/${prod}_3_issue.png`, fullPage: true });
      const [dl2] = await Promise.all([page.waitForEvent('download', { timeout: 90000 }), page.click('#btnPolDoc')]); ok('policy pdf', fs.readFileSync(await dl2.path()).slice(0, 4).toString() === '%PDF');
      await page.click('#btnToServ'); await page.waitForSelector('#loadResult dl', { timeout: 60000 }); ok('load policy', /Afillar/.test(await page.textContent('#loadResult')));
      await page.screenshot({ path: `${shotDir}/${prod}_4_servicing.png`, fullPage: true });
      await page.click('#stabs button[data-tab="s_cancel"]'); await page.click('#btnCheck'); await page.waitForSelector('#checkResult .alert', { timeout: 120000 });
      const ck = await page.textContent('#checkResult'); ok('cancel check', /Refund/.test(ck) && /PENDING/.test(ck), ck.replace(/\s+/g, ' ').slice(0, 200));
      await page.screenshot({ path: `${shotDir}/${prod}_5_cancel.png`, fullPage: true });
      page.once('dialog', d => d.accept()); await page.click('#btnApprove'); await page.waitForSelector('#decideResult .alert', { timeout: 120000 });
      const dc = await page.textContent('#decideResult'); ok('cancel approved', /APPROVED/.test(dc) && /Cancelled/.test(dc), dc.replace(/\s+/g, ' ').slice(0, 160));
      await page.click('#stabs button[data-tab="s_comm"]'); await page.fill('#m_policy', pol); await page.click('#btnCommPolicy'); await page.waitForSelector('#commResult table', { timeout: 60000 });
      ok('commission', /Afillar/.test(await page.textContent('#commResult')));
    } catch (e) { ok('exception', false, e.message.slice(0, 200)); await page.screenshot({ path: `${shotDir}/${prod}_error.png`, fullPage: true }).catch(() => {}); }
    log.consoleErrors = errs; results.push(log); await ctx.close();
    console.log(prod, log.steps.every(s => s.ok) ? 'PASS' : 'FAIL', 'steps', log.steps.length, 'console errors', errs.length, errs.slice(0, 2));
  }
  fs.writeFileSync(shotDir + '/results.json', JSON.stringify(results, null, 1)); await browser.close();
})();
