const { chromium } = require('/opt/node-tools/node_modules/playwright');
const { execSync } = require('child_process'); const fs = require('fs');
const TOK = JSON.parse(execSync('imo auth prepare --profile portal:uponly --json')).access_token;
const REAL = 'https://portal-gw.insuremo.com/platform/api-orchestration-test/v1/flow';
const PAGE = 'file:///home/user/Tablet/uic_pages/uponly/portal/sohar-insurance-portal/index.html';
const shotDir = process.argv[2] || 'shots3'; const prod = process.argv[3] || 'HC001'; fs.mkdirSync(shotDir, { recursive: true });
(async () => {
  const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome' }).catch(() => chromium.launch());
  const ctx = await browser.newContext({ viewport: { width: 1400, height: 1000 }, acceptDownloads: true });
  await ctx.addInitScript(t => { sessionStorage.setItem('Authorization', 'Bearer ' + t); sessionStorage.setItem('sohar_api_base', 'https://fake-gw.test/platform/api-orchestration-test/v1/flow'); }, TOK);
  await ctx.route('https://fake-gw.test/**', async route => {
    const req = route.request(); const url = REAL + req.url().split('/v1/flow')[1];
    const r = await fetch(url, { method: req.method(), headers: { Authorization: 'Bearer ' + TOK, 'Content-Type': 'application/json' }, body: req.method() === 'GET' ? undefined : req.postData() });
    await route.fulfill({ status: r.status, headers: { 'content-type': r.headers.get('content-type') || 'application/json', 'access-control-allow-origin': '*' }, body: Buffer.from(await r.arrayBuffer()) });
  });
  const page = await ctx.newPage(); const errs = []; page.on('console', m => { if (m.type() === 'error') errs.push(m.text()); }); page.on('pageerror', e => errs.push('PAGEERR ' + e.message)); page.on('dialog', d => d.accept());
  const out = []; const ok = (n, c, x) => { out.push({ n, ok: !!c, x }); console.log((c ? 'PASS ' : 'FAIL ') + n + (x ? ' | ' + String(x).slice(0, 140) : '')); };
  const shot = n => page.screenshot({ path: `${shotDir}/${n}.png`, fullPage: true });
  try {
    await page.goto(PAGE); await page.waitForSelector('#d_body .tiles', { timeout: 120000 });
    ok('dashboard tiles', await page.locator('#d_body .tile').count() >= 6, await page.locator('#d_body .tile').count()); ok('dashboard charts', await page.locator('#d_body svg').count() >= 3);
    ok('user chip shows roles', /Maker/.test(await page.textContent('#userChip')) && /Proposal Checker/.test(await page.textContent('#userChip')), await page.textContent('#userChip'));
    ok('nav has all role items', await page.locator('#side button').count() === 6, await page.locator('#side button').allTextContents());
    await shot('01_dashboard');
    // maker: new quotation
    await page.click('#side button[data-v="new"]'); await page.selectOption('#q_product', prod);
    await page.fill('#q_name', 'Workflow Test'); await page.fill('#q_dob', '1990-05-05'); await page.click('#btnQuote'); await page.waitForSelector('#plans .plan', { timeout: 60000 });
    await page.locator('#plans .plan').first().click(); await shot('02_quote');
    await page.click('#btnShareQuote'); await page.fill('#sh_email', 'customer@example.com'); await page.fill('#sh_mobile', '96891234567'); await page.selectOption('#sh_ch', 'BOTH'); await page.click('#sh_send'); await page.waitForSelector('#sh_res .alert', { timeout: 60000 });
    const sres = await page.textContent('#sh_res'); ok('share quotation (dry run)', /dry run/.test(sres) && /Email/.test(sres) && /SMS/.test(sres), sres.replace(/\s+/g, ' ')); await shot('03_share'); await page.click('#sh_close');
    await page.click('#btnToProposal'); await page.fill('#p_cif', '45678'); await page.fill('#p_idno', '123456789'); await page.fill('#p_mobile', '9989374444'); await page.fill('#p_email', 'test@example.com'); await page.fill('#p_addr', 'Muscat'); await page.fill('#p_post', '100345'); await page.fill('#b_name', 'Sayyed Test'); await page.fill('#pay_acc', '896236508');
    await page.click('#btnCreateProp'); await page.waitForSelector('#n_done .alert', { timeout: 90000 });
    const done = await page.textContent('#n_done'); const pno = (done.match(/P[A-Z]+\d{8,}/) || [])[0]; ok('maker submits for approval', /submitted for approval/.test(done) && pno, pno); ok('submit shows alert to checker', /Proposal Checker/.test(done), ''); await shot('04_submitted');
    // my submissions
    await page.click('#side button[data-v="mine"]'); await page.waitForSelector('#qm_tbl table', { timeout: 60000 }); await page.selectOption('#qm_pr', prod); await page.waitForTimeout(1500); await page.waitForSelector('#qm_tbl table, #qm_tbl .empty');
    ok('my submissions lists it', (await page.textContent('#qm_tbl')).includes(pno), pno); await shot('05_mine');
    // checker queue
    await page.click('#side button[data-v="papprove"]'); await page.waitForSelector('#qp_tbl table', { timeout: 60000 }); await page.selectOption('#qp_pr', prod); await page.waitForTimeout(2500);
    const row = page.locator('#qp_tbl tr.row', { hasText: pno }); ok('checker queue shows it', await row.count() === 1, pno); await shot('06_queue');
    await row.locator('button').click(); await page.waitForSelector('#pd', { timeout: 60000 }); ok('proposal detail opens with approve/reject', await page.locator('#pd_ok').isEnabled() && await page.locator('#pd_rej').isEnabled()); await shot('07_detail');
    await page.click('#pd_share'); await page.selectOption('#sh_ch', 'EMAIL'); await page.click('#sh_send'); await page.waitForSelector('#sh_res .alert', { timeout: 60000 }); ok('share proposal (dry run)', /dry run/.test(await page.textContent('#sh_res'))); await page.click('#sh_close');
    await page.click('#pd_ok'); await page.waitForSelector('#pd_res .alert.ok', { timeout: 120000 }); const ap = await page.textContent('#pd_res'); const pol = (ap.match(/PO[A-Z]+\d{8,}/) || [])[0]; ok('checker approves and policy issues', !!pol, pol); ok('approval alerts shown', /maker/.test(ap) && /customer/.test(ap), ''); await shot('08_approved');
    // second proposal: reject
    await page.click('#side button[data-v="new"]'); await page.click('#nd_new'); await page.selectOption('#q_product', prod); await page.fill('#q_name', 'Reject Test'); await page.fill('#q_dob', '1985-03-03'); await page.click('#btnQuote'); await page.waitForSelector('#plans .plan', { timeout: 60000 });
    await page.locator('#plans .plan').nth(1).click(); await page.click('#btnToProposal'); await page.fill('#p_cif', '45679'); await page.fill('#p_idno', '987654321'); await page.fill('#p_mobile', '9989374445'); await page.fill('#p_email', 'r@example.com'); await page.fill('#p_addr', 'Sohar'); await page.fill('#p_post', '100'); await page.fill('#b_name', 'Rej Ben'); await page.fill('#pay_acc', '896236508');
    await page.click('#btnCreateProp'); await page.waitForSelector('#n_done .alert', { timeout: 90000 }); const pno2 = ((await page.textContent('#n_done')).match(/P[A-Z]+\d{8,}/) || [])[0];
    await page.click('#side button[data-v="papprove"]'); await page.waitForSelector('#qp_tbl table'); await page.selectOption('#qp_pr', prod); await page.waitForTimeout(2500); await page.locator('#qp_tbl tr.row', { hasText: pno2 }).locator('button').click(); await page.waitForSelector('#pd_rej');
    await page.click('#pd_rej'); await page.click('#rj_go'); ok('reject without reason is blocked', /at least 3/.test(await page.textContent('#e_rj_reason')));
    await page.fill('#rj_reason', 'Premium does not match the quotation'); await page.click('#rj_go'); await page.waitForSelector('#pd_res .alert.ok', { timeout: 90000 }); ok('checker rejects with a reason', /rejected/i.test(await page.textContent('#pd_res')), pno2); await shot('09_rejected');
    await page.click('#side button[data-v="mine"]'); await page.waitForSelector('#qm_tbl table'); await page.selectOption('#qm_st', 'REJECTED'); await page.waitForTimeout(2500); await page.locator('#qm_tbl tr.row', { hasText: pno2 }).locator('button').click(); await page.waitForSelector('#pd');
    ok('maker sees the reject reason', /Premium does not match/.test(await page.textContent('#pd')), ''); ok('maker view has no approve button', await page.locator('#det_mine #pd_ok').count() === 0 && await page.locator('#det_papprove #pd').count() === 0); await shot('10_mine_rejected');
    // cancellation
    await page.click('#side button[data-v="cancel"]'); await page.click('#tabRaise'); await page.fill('#c_policy', pol); await page.click('#btnCLoad'); await page.waitForSelector('#c_policyInfo .alert');
    await page.click('#btnCSubmit'); await page.waitForSelector('#c_result .alert.ok', { timeout: 120000 }); const cr = await page.textContent('#c_result'); const rq = (cr.match(/PO[A-Z]+\d{8,}-\d+/) || [])[0]; ok('maker raises cancellation request', !!rq && /Refund if approved/.test(cr), rq); await shot('11_cancel_raise');
    await page.click('#cancelTabs button[data-t="queue"]'); await page.waitForSelector('#qc_tbl table', { timeout: 60000 }); await page.selectOption('#qc_pr', prod); await page.waitForTimeout(3500);
    const crow = page.locator('#qc_tbl tr.row', { hasText: rq }); ok('request in the cancellation queue', await crow.count() === 1, rq); await shot('12_cancel_queue');
    await crow.locator('button').click(); await page.waitForSelector('#cd_ok', { timeout: 60000 }); ok('cancellation detail shows refund and approve', /Refund calculation/.test(await page.textContent('#det_cancel')) && await page.locator('#cd_ok').isEnabled()); await shot('13_cancel_detail');
    await page.click('#cd_ok'); await page.waitForSelector('#cd_res .alert.ok', { timeout: 120000 }); const cd = await page.textContent('#cd_res'); ok('cancellation approved', /APPROVED/.test(cd) && /Cancelled/.test(cd), cd.replace(/\s+/g, ' ').slice(0, 120)); await shot('14_cancel_done');
    // policies
    await page.click('#side button[data-v="policies"]'); await page.fill('#f_policy', pol); await page.click('#btnLoad'); await page.waitForSelector('#fp_com', { timeout: 60000 }); await page.click('#fp_com'); await page.waitForSelector('#fp_extra dl', { timeout: 60000 }); ok('policy view with commission', /Commission/.test(await page.textContent('#fp_extra')), ''); await shot('15_policy');
  } catch (e) { ok('exception', false, e.message.slice(0, 300)); await shot('error'); }
  ok('no console errors', errs.length === 0, errs.slice(0, 3).join(' || '));
  fs.writeFileSync(shotDir + '/results.json', JSON.stringify(out, null, 1)); console.log(out.filter(o => o.ok).length + ' of ' + out.length + ' passed'); await browser.close();
})();
