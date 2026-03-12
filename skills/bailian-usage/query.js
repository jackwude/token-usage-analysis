#!/usr/bin/env node

/**
 * 百炼套餐用量查询（Agent Browser state-first）
 * 主链路：state load -> 打开百炼 -> 检查登录 -> 必要时账号密码登录 -> state save -> 提取套餐信息
 */

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawnSync } = require('node:child_process');

const BAILIAN_URL = 'https://bailian.console.aliyun.com/cn-beijing/?tab=coding-plan#/efm/index';
const TOOLS_PATH = path.join(process.env.HOME, '.openclaw/workspace/TOOLS.md');
const SESSION = process.env.BAILIAN_SESSION || 'bailian';
const STATE_PATH = process.env.BAILIAN_STATE_PATH || path.join(os.homedir(), '.openclaw/browser-states/bailian.json');

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

function readCredentials() {
  const content = fs.readFileSync(TOOLS_PATH, 'utf-8');
  const accountMatch = content.match(/\*\*账号\*\*:\s*(.+)/);
  const passwordMatch = content.match(/\*\*密码\*\*:\s*(.+)/);

  if (!accountMatch || !passwordMatch) {
    throw new Error('未在 TOOLS.md 中找到百炼账号信息');
  }

  return {
    account: accountMatch[1].trim(),
    password: passwordMatch[1].trim()
  };
}

function getBodyText() {
  const raw = runAB(['eval', 'document.body ? document.body.innerText : ""'], { allowFail: true });
  const s = raw.trim();
  if (s.startsWith('"') && s.endsWith('"')) {
    try { return JSON.parse(s); } catch {}
  }
  return s;
}

function isLoggedIn(text) {
  return !text.includes('\n登录\n') && !text.includes('请登录') && text.includes('我的订阅');
}

function clickIfContains(label) {
  runAB(['eval', `(() => {
    const norm = s => (s || '').replace(/\s+/g, ' ').trim();
    const el = [...document.querySelectorAll('button,a,span,div')].find(x => norm(x.innerText || x.textContent) === ${JSON.stringify(label)} || norm(x.innerText || x.textContent).includes(${JSON.stringify(label)}));
    if (el && el.click) { el.click(); return true; }
    return false;
  })()`], { allowFail: true });
}

function tryLogin(account, password) {
  // 尝试点击顶部登录
  clickIfContains('登录');
  runAB(['wait', '3000'], { allowFail: true });

  // 尝试切换账号密码登录并填写
  runAB(['eval', `(() => {
    const norm = s => (s || '').replace(/\s+/g,' ').trim();
    const clickByText = (t) => {
      const el = [...document.querySelectorAll('button,a,span,div')].find(x => norm(x.innerText || x.textContent).includes(t));
      if (el && el.click) { el.click(); return true; }
      return false;
    };

    clickByText('账号');
    clickByText('密码');
    clickByText('账号密码');

    const setVal = (el, v) => {
      el.focus();
      el.value = v;
      el.dispatchEvent(new Event('input', { bubbles: true }));
      el.dispatchEvent(new Event('change', { bubbles: true }));
    };

    const inputs = [...document.querySelectorAll('input')];
    const user = inputs.find(i => {
      const p = (i.placeholder || '').toLowerCase();
      const n = (i.name || '').toLowerCase();
      return i.type === 'text' || i.type === 'email' || p.includes('账号') || p.includes('邮箱') || n.includes('user') || n.includes('login');
    });
    const pass = inputs.find(i => i.type === 'password' || (i.placeholder || '').includes('密码'));
    if (user) setVal(user, ${JSON.stringify(account)});
    if (pass) setVal(pass, ${JSON.stringify(password)});

    const btn = [...document.querySelectorAll('button,a,span,div')].find(x => {
      const t = norm(x.innerText || x.textContent).toLowerCase();
      return t === '登录' || t.includes('登录') || t.includes('sign in');
    });
    if (btn && btn.click) { btn.click(); return 'clicked'; }
    return 'no-login-button';
  })()`], { allowFail: true });

  runAB(['wait', '6000'], { allowFail: true });
  runAB(['open', BAILIAN_URL], { allowFail: true });
  runAB(['wait', '3000'], { allowFail: true });
}

function parseUsage(text) {
  const pick = (re) => (text.match(re) || [])[1] || '-';

  const status = text.includes('生效中') ? '✅ 生效中' : (text.includes('已过期') ? '❌ 已过期' : '-');
  const daysLeft = pick(/剩余\s*(\d+)\s*天/);
  const expireDate = pick(/(\d{4}-\d{2}-\d{2})\s*到期/);

  const autoRenew = text.includes('自动续费')
    ? (text.includes('未开启') ? '❌ 未开启' : (text.includes('已开启') ? '✅ 已开启' : '-'))
    : '-';

  const lastStat = pick(/最后统计时间[:：]\s*([^\n]+)/);
  const h5Usage = pick(/近\s*5\s*小时[^\n]*?([0-9.]+%)/);
  const h5Reset = pick(/近\s*5\s*小时[^\n]*?(\d{4}-\d{2}-\d{2}\s*\d{2}:\d{2}:\d{2})/);
  const w1Usage = pick(/近\s*一周[^\n]*?([0-9.]+%)/);
  const w1Reset = pick(/近\s*一周[^\n]*?(\d{4}-\d{2}-\d{2}\s*\d{2}:\d{2}:\d{2})/);
  const m1Usage = pick(/近\s*一月[^\n]*?([0-9.]+%)/);
  const m1Reset = pick(/近\s*一月[^\n]*?(\d{4}-\d{2}-\d{2}\s*\d{2}:\d{2}:\d{2})/);

  return {
    status,
    daysLeft,
    expireDate,
    autoRenew,
    lastStat,
    h5Usage,
    h5Reset,
    w1Usage,
    w1Reset,
    m1Usage,
    m1Reset,
    rawHasSubscription: text.includes('我的订阅')
  };
}

function outputReport(data, err) {
  if (err) {
    console.log('## 📊 百炼 Coding Plan 套餐详情\n');
    console.log('查询失败：' + err);
    return;
  }

  console.log('## 📊 百炼 Coding Plan 套餐详情\n');
  console.log(`**套餐状态：** ${data.status} | 剩余 **${data.daysLeft} 天**（${data.expireDate} 到期）`);
  console.log(`**自动续费：** ${data.autoRenew}\n`);
  console.log('**用量消耗：**');
  console.log(`- 最后统计时间：${data.lastStat}`);
  console.log(`- 近 5 小时：**${data.h5Usage}**（${data.h5Reset} **重置**）`);
  console.log(`- 近一周：**${data.w1Usage}**（${data.w1Reset} **重置**）`);
  console.log(`- 近一月：**${data.m1Usage}**（${data.m1Reset} **重置**）\n`);
  console.log('**可用模型：** 千问系列 / 智谱 / Kimi / MiniMax');
}

async function main() {
  let err = null;
  let data = null;

  try {
    fs.mkdirSync(path.dirname(STATE_PATH), { recursive: true });

    if (fs.existsSync(STATE_PATH)) {
      runAB(['state', 'load', STATE_PATH], { allowFail: true });
    }

    runAB(['open', BAILIAN_URL]);
    runAB(['wait', '3000'], { allowFail: true });

    // 关闭可能挡住页面的大弹层
    clickIfContains('close');
    clickIfContains('收起产品面板');

    let text = getBodyText();

    if (!isLoggedIn(text)) {
      const creds = readCredentials();
      tryLogin(creds.account, creds.password);
      text = getBodyText();
    }

    // 尝试进入“我的订阅”tab
    clickIfContains('我的订阅');
    runAB(['wait', '2500'], { allowFail: true });
    text = getBodyText();

    runAB(['state', 'save', STATE_PATH], { allowFail: true });

    data = parseUsage(text);
    if (!data.rawHasSubscription || data.lastStat === '-') {
      throw new Error('未获取到订阅用量数据（可能仍未完成登录，建议手动登录百炼一次后重试）');
    }
  } catch (e) {
    err = e?.message || String(e);
  } finally {
    runAB(['close'], { allowFail: true });
  }

  outputReport(data || {}, err);
}

main();
