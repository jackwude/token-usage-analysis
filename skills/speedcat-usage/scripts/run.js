#!/usr/bin/env node
/**
 * SpeedCat checkin + usage via agent-browser (state-first).
 * - Prefer `agent-browser state load` from ~/.openclaw/browser-states/speedcat.json
 * - If not logged in, auto login with creds (env or TOOLS.md)
 * - Save state back after successful login/use
 * - Output fixed-format report
 */

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawnSync } = require('node:child_process');

const SESSION = process.env.SPEEDCAT_SESSION || 'speedcat';
const STATE_PATH = process.env.SPEEDCAT_STATE_PATH || path.join(os.homedir(), '.openclaw/browser-states/speedcat.json');
const USER_URL = 'https://speedcat.co/user';
const LOGIN_URL = 'https://speedcat.co/auth/login';

function stripAnsi(s) {
  return String(s || '').replace(/\x1B\[[0-9;]*m/g, '');
}

function runAB(args, { allowFail = false } = {}) {
  const r = spawnSync('agent-browser', ['--session', SESSION, ...args], { encoding: 'utf8' });
  if (r.status !== 0 && !allowFail) {
    throw new Error(stripAnsi((r.stderr || r.stdout || `agent-browser failed: ${args.join(' ')}`).trim()));
  }
  return stripAnsi((r.stdout || '').trim());
}

function fixed2(n) {
  if (n == null || n === '' || Number.isNaN(Number(n))) return '-';
  return Number(n).toFixed(2);
}

function trafficStatus(remainingGb) {
  const x = Number(remainingGb);
  if (!Number.isFinite(x)) return '-';
  if (x >= 50) return '✅ 充足';
  if (x >= 10) return '⚠️ 关注';
  return '❌ 紧张';
}

function readCreds() {
  if (process.env.SPEEDCAT_EMAIL && process.env.SPEEDCAT_PASSWORD) {
    return { email: process.env.SPEEDCAT_EMAIL, password: process.env.SPEEDCAT_PASSWORD };
  }
  try {
    const toolsPath = process.env.SPEEDCAT_TOOLS || path.join(os.homedir(), '.openclaw/workspace/TOOLS.md');
    const tools = fs.readFileSync(toolsPath, 'utf8');
    const email = (tools.match(/##\s*🔐\s*SpeedCat[\s\S]*?\*\*邮箱\*\*:\s*([^\n\r]+)/) || [])[1]?.trim();
    const password = (tools.match(/##\s*🔐\s*SpeedCat[\s\S]*?\*\*密码\*\*:\s*([^\n\r]+)/) || [])[1]?.trim();
    if (email && password) return { email, password };
  } catch {}
  return { email: '', password: '' };
}

function asJsonEvalResult(out) {
  const s = (out || '').trim();
  if (!s) return null;
  try { return JSON.parse(s); } catch {}
  const i = s.lastIndexOf('\n');
  if (i >= 0) {
    try { return JSON.parse(s.slice(i + 1)); } catch {}
  }
  return null;
}

function evalJson(js) {
  const out = runAB(['eval', js]);
  const parsed = asJsonEvalResult(out);
  return parsed;
}

function currentUrl() {
  const out = runAB(['get', 'url'], { allowFail: true });
  const m = out.match(/https?:\/\/\S+/);
  return m ? m[0] : out.trim();
}

function clickVerifyIfNeeded() {
  const url = currentUrl();
  if (!url.includes('/verify')) return;
  runAB(['eval', `(() => {
    const btn = [...document.querySelectorAll('button,a')].find(el => (el.innerText||'').includes('我不是恶意刷站'));
    if (btn) { btn.click(); return true; }
    return false;
  })()`], { allowFail: true });
  runAB(['wait', '2500'], { allowFail: true });
}

function isLoggedIn() {
  const v = evalJson(`(() => {
    const t = document.body?.innerText || '';
    return t.includes('Hi,') && t.includes('@') && !location.pathname.includes('/auth/login');
  })()`);
  return Boolean(v);
}

function loginWithCreds(email, password) {
  runAB(['open', LOGIN_URL]);
  runAB(['wait', '1500'], { allowFail: true });
  clickVerifyIfNeeded();
  runAB(['eval', `(() => {
    const setVal = (el, v) => {
      el.focus();
      el.value = v;
      el.dispatchEvent(new Event('input', { bubbles: true }));
      el.dispatchEvent(new Event('change', { bubbles: true }));
    };
    const emailEl = document.querySelector('input[type=email],input[name=email],input[placeholder*=邮箱],input[placeholder*=mail]');
    const passEl = document.querySelector('input[type=password],input[name=password],input[name=passwd],input[placeholder*=密码]');
    if (!emailEl || !passEl) return 'no-fields';
    setVal(emailEl, ${JSON.stringify(email)});
    setVal(passEl, ${JSON.stringify(password)});
    const remember = [...document.querySelectorAll('input[type=checkbox],label,span')].find(el => (el.innerText||'').includes('记住我'));
    if (remember && remember.click) remember.click();
    const btn = [...document.querySelectorAll('button,input[type=submit],a')].find(el => {
      const t = (el.innerText || el.value || '').trim().toLowerCase();
      return t.includes('登录') || t.includes('login');
    });
    if (btn) { btn.click(); return 'clicked'; }
    const form = emailEl.closest('form');
    if (form) { form.submit(); return 'submitted'; }
    return 'no-button';
  })()`], { allowFail: true });
  runAB(['wait', '5000'], { allowFail: true });
  clickVerifyIfNeeded();
  runAB(['open', USER_URL]);
  runAB(['wait', '2500'], { allowFail: true });
}

function doCheckinBestEffort() {
  const status = evalJson(`(() => {
    const norm = s => (s || '').replace(/\s+/g, ' ').trim();
    const labels = [...document.querySelectorAll('a,button')].map(el => norm(el.innerText || el.textContent));
    if (labels.some(t => t.includes('明日再来'))) return '明日再来';
    const btn = [...document.querySelectorAll('a,button')].find(el => {
      const t = norm(el.innerText || el.textContent);
      return t.includes('签到') && !t.includes('明日再来');
    });
    if (!btn) return '-';
    btn.click();
    return 'clicked';
  })()`);

  if (status === 'clicked') {
    runAB(['wait', '1200'], { allowFail: true });
    runAB(['eval', `(() => {
      const ok = [...document.querySelectorAll('button,a')].find(el => {
        const t = (el.innerText || el.textContent || '').trim();
        return t === 'OK' || t === 'Ok' || t === '确定' || t.includes('OK');
      });
      if (ok) ok.click();
      return true;
    })()`], { allowFail: true });
    runAB(['wait', '800'], { allowFail: true });
  }
  return status || '-';
}

function extractData() {
  const obj = evalJson(`(() => {
    const text = (el) => ((el && el.textContent) ? el.textContent : '').replace(/\s+/g, ' ').trim();
    const bodyText = document.body ? (document.body.innerText || '') : '';
    const lines = bodyText.split('\n').map(s => (s || '').trim()).filter(Boolean);

    const planH4 = [...document.querySelectorAll('h4')].find(x => /.+:/.test(text(x)) && !text(x).includes('剩余流量') && !text(x).includes('在线IP') && !text(x).includes('钱包余额'));
    const plan_name = planH4 ? text(planH4).replace(/:.*$/, '').replace(/:$/, '') : null;

    const dayLine = lines.find(s => s.includes('天') && /\d+/.test(s));
    let days_left = null;
    if (dayLine) {
      const m = dayLine.match(/(\d+)\s*天/);
      days_left = m ? m[1] : null;
    }

    const resetLine = lines.find(s => s.includes('流量重置时间')) || '';
    const reset_date = resetLine.split(/[:：]/).slice(1).join(':').trim() || null;

    const remLine = lines.find(s => s.includes('剩余流量') && /[0-9.]+\s*GB/i.test(s)) || '';
    const remMatch = remLine.match(/([0-9.]+)\s*GB/i);
    const remaining_gb = remMatch ? remMatch[1] : null;

    const usedLine = lines.find(s => s.includes('今日已用')) || '';
    const usedMatch = usedLine.match(/([0-9.]+)\s*GB/i);
    const used_today_gb = usedMatch ? usedMatch[1] : null;

    const walletLine = lines.find(s => s.includes('钱包余额')) || '';
    const walletMatch = walletLine.match(/¥\s*([0-9.]+)/);
    const wallet_cny = walletMatch ? walletMatch[1] : null;

    const rebateLine = lines.find(s => s.includes('累计获得返利金额')) || '';
    const rebateMatch = rebateLine.match(/¥\s*([0-9.]+)/);
    const rebate_cny = rebateMatch ? rebateMatch[1] : null;

    const onlineLine = lines.find(s => s.includes('在线IP')) || null;
    const online_ip = onlineLine ? onlineLine.split(/[:：]/).slice(1).join(':').trim() || onlineLine : null;

    const lastLine = lines.find(s => s.includes('上次使用')) || null;
    const last_used = lastLine ? lastLine.split(/[:：]/).slice(1).join(':').trim() || lastLine : null;

    const checkin = [...document.querySelectorAll('a,button')].map(x => text(x)).find(s => s.includes('明日再来') || s.includes('签到')) || null;

    return {
      plan_name, days_left, reset_date,
      remaining_gb, used_today_gb,
      wallet_cny, rebate_cny,
      online_ip, last_used,
      checkin
    };
  })()`);

  return obj || {};
}

function printReport({ reason = null, data = {} }) {
  const plan_name = data.plan_name || '-';
  const days_left = data.days_left || '-';
  const expire_date = '-';
  const reset_date = data.reset_date || '-';
  const remaining_gb = data.remaining_gb ? fixed2(data.remaining_gb) : '-';
  const used_today_gb = data.used_today_gb ? fixed2(data.used_today_gb) : '-';
  const wallet_cny = data.wallet_cny ? fixed2(data.wallet_cny) : '-';
  const rebate_cny = data.rebate_cny ? fixed2(data.rebate_cny) : '-';
  const online_ip = data.online_ip || '-';
  const last_used = data.last_used || '-';
  let checkin_status = data.checkin || '-';
  if (reason) checkin_status = `失败：${reason}`;

  const status = trafficStatus(remaining_gb);

  process.stdout.write(
`## 📊 SpeedCat 用量详情

**套餐：** ${plan_name} | 剩余 **${days_left} 天**（到期日：${expire_date}）
**流量重置：** ${reset_date}

**流量使用：**
- 剩余流量：**${remaining_gb} GB**
- 今日已用：**${used_today_gb} GB**

**账户信息：**
- 钱包余额：**¥ ${wallet_cny}**（累计返利：¥ ${rebate_cny}）

**用量判断：** ${status}

### 附加信息（波动项）
- 在线 IP：${online_ip}
- 上次使用：${last_used}
- 今日签到：${checkin_status}
`);
}

function main() {
  let reason = null;
  let data = {};

  try {
    fs.mkdirSync(path.dirname(STATE_PATH), { recursive: true });

    if (fs.existsSync(STATE_PATH)) {
      runAB(['state', 'load', STATE_PATH], { allowFail: true });
    }

    runAB(['open', USER_URL]);
    runAB(['wait', '1800'], { allowFail: true });
    clickVerifyIfNeeded();

    let logged = isLoggedIn();

    if (!logged) {
      const { email, password } = readCreds();
      if (!email || !password) throw new Error('未找到 SpeedCat 账号密码');
      loginWithCreds(email, password);
      logged = isLoggedIn();
      if (!logged) throw new Error('自动登录失败（可能触发额外验证）');
    }

    // Save/refresh state once confirmed logged in.
    runAB(['state', 'save', STATE_PATH], { allowFail: true });

    const ck = doCheckinBestEffort();
    data = extractData();
    if (!data.checkin && ck) data.checkin = ck;

    // Save again after check-in/use to keep freshest state.
    runAB(['state', 'save', STATE_PATH], { allowFail: true });
  } catch (e) {
    reason = e?.message || String(e);
  } finally {
    runAB(['close'], { allowFail: true });
  }

  printReport({ reason, data });
}

main();
