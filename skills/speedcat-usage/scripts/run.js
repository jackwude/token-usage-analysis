#!/usr/bin/env node
/**
 * SpeedCat checkin + usage via Chrome DevTools Protocol (no external deps).
 * Requires Chrome launched with remote debugging port 9223 and speedcat profile.
 * Outputs a fixed-format report.
 */

const CDP_PORT = process.env.SPEEDCAT_CDP_PORT || '9223';
const ORIGIN = `http://127.0.0.1:${CDP_PORT}`;
const TARGET_URL = 'https://speedcat.co/user';

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

async function httpGetJson(path) {
  const res = await fetch(`${ORIGIN}${path}`);
  if (!res.ok) throw new Error(`HTTP ${res.status} ${path}`);
  return res.json();
}

async function httpGetText(path) {
  const res = await fetch(`${ORIGIN}${path}`);
  if (!res.ok) throw new Error(`HTTP ${res.status} ${path}`);
  return res.text();
}

async function getOrCreateTarget() {
  // try find existing /user tab
  const list = await httpGetJson('/json');
  const existing = list.find(t => t.type === 'page' && typeof t.url === 'string' && t.url.startsWith(TARGET_URL));
  if (existing) return existing;

  // Some Chrome builds disable /json/new (HTTP 405). Fallback: create target via browser-level CDP.
  try {
    const created = await httpGetJson(`/json/new?${new URLSearchParams({ url: TARGET_URL }).toString()}`);
    return created;
  } catch {
    // browser ws
    const ver = await httpGetJson('/json/version');
    const browserWs = ver.webSocketDebuggerUrl;
    if (!browserWs) throw new Error('No browser webSocketDebuggerUrl');

    const targetId = await withCdp(browserWs, async ({ send }) => {
      // Target domain is usually available on browser endpoint
      const r = await send('Target.createTarget', { url: TARGET_URL });
      return r?.targetId;
    });

    // re-list and find the created target
    const list2 = await httpGetJson('/json');
    const created2 = list2.find(t => t.id === targetId) || list2.find(t => t.type === 'page' && typeof t.url === 'string' && t.url.startsWith(TARGET_URL));
    if (!created2) throw new Error('Failed to create target');
    return created2;
  }
}

async function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

async function withCdp(wsUrl, fn) {
  const ws = new WebSocket(wsUrl);
  await new Promise((resolve, reject) => {
    ws.addEventListener('open', resolve, { once: true });
    ws.addEventListener('error', () => reject(new Error('WebSocket connect failed')), { once: true });
  });

  let id = 0;
  const pending = new Map();
  ws.addEventListener('message', (ev) => {
    const msg = JSON.parse(ev.data);
    if (msg.id && pending.has(msg.id)) {
      const { resolve, reject } = pending.get(msg.id);
      pending.delete(msg.id);
      if (msg.error) reject(new Error(msg.error.message || 'CDP error'));
      else resolve(msg.result);
    }
  });

  async function send(method, params = {}) {
    const msgId = ++id;
    ws.send(JSON.stringify({ id: msgId, method, params }));
    return await new Promise((resolve, reject) => pending.set(msgId, { resolve, reject }));
  }

  try {
    return await fn({ send });
  } finally {
    try { ws.close(); } catch {}
  }
}

async function waitForLoad(send, timeoutMs = 15000) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    try {
      const r = await send('Runtime.evaluate', {
        expression: 'document.readyState',
        returnByValue: true,
      });
      if (r?.result?.value === 'complete' || r?.result?.value === 'interactive') return;
    } catch {}
    await sleep(250);
  }
}

async function main() {
  let reason = null;
  let plan_name = '-';
  let days_left = '-';
  let expire_date = '-';
  let reset_date = '-';
  let remaining_gb = '-';
  let used_today_gb = '-';
  let wallet_cny = '-';
  let rebate_cny = '-';
  let online_ip = '-';
  let last_used = '-';
  let checkin_status = '-';

  try {
    const target = await getOrCreateTarget();
    const wsUrl = target.webSocketDebuggerUrl;
    if (!wsUrl) throw new Error('No webSocketDebuggerUrl; is Chrome running with --remote-debugging-port?');

    const result = await withCdp(wsUrl, async ({ send }) => {
      await send('Page.enable');
      await send('Runtime.enable');
      await send('Network.enable');

      // Ensure we are on target URL (some created targets start at about:blank)
      try {
        const cur = await send('Runtime.evaluate', { expression: 'location.href', returnByValue: true });
        const href = cur?.result?.value || '';
        if (!String(href).startsWith(TARGET_URL)) {
          await send('Page.navigate', { url: TARGET_URL });
        }
      } catch {
        try { await send('Page.navigate', { url: TARGET_URL }); } catch {}
      }

      await waitForLoad(send, 15000);

      // If verification page appears, click the button containing "我不是恶意刷站"
      try {
        await send('Runtime.evaluate', {
          expression: `(() => {
            const btn = [...document.querySelectorAll('button, a')].find(el => (el.innerText||'').includes('我不是恶意刷站'));
            if (btn) { btn.click(); return true; }
            return false;
          })()` ,
          awaitPromise: true,
          returnByValue: true,
        });
        await sleep(1200);
        await waitForLoad(send, 15000);
      } catch {}

      // Detect login
      const isLoggedIn = await send('Runtime.evaluate', {
        expression: `(() => {
          const t = document.body?.innerText || '';
          return t.includes('Hi,') && t.includes('@');
        })()` ,
        returnByValue: true,
      });

      if (!isLoggedIn?.result?.value) {
        // Fallback: inject saved cookies (best-effort) then reload once.
        try {
          const fs = require('node:fs');
          const cookiePath = process.env.SPEEDCAT_COOKIES || `${process.env.HOME}/.openclaw/cookies/speedcat.json`;
          const raw = fs.readFileSync(cookiePath, 'utf8');
          const obj = JSON.parse(raw);
          const cookieStr = obj.cookies || '';
          const pairs = cookieStr.split(';').map(s => s.trim()).filter(Boolean);
          for (const p of pairs) {
            const eq = p.indexOf('=');
            if (eq <= 0) continue;
            const name = p.slice(0, eq);
            const value = p.slice(eq + 1);
            await send('Network.setCookie', { url: TARGET_URL, name, value });
          }
          await send('Page.reload', { ignoreCache: true });
          await waitForLoad(send, 15000);
        } catch {}

        const isLoggedIn2 = await send('Runtime.evaluate', {
          expression: `(() => {
            const t = document.body?.innerText || '';
            return t.includes('Hi,') && t.includes('@');
          })()` ,
          returnByValue: true,
        });
        if (!isLoggedIn2?.result?.value) {
          // Last fallback: perform login with creds from TOOLS.md (best-effort).
          try {
            const fs = require('node:fs');
            const toolsPath = process.env.SPEEDCAT_TOOLS || `${process.env.HOME}/.openclaw/workspace/TOOLS.md`;
            const tools = fs.readFileSync(toolsPath, 'utf8');
            const email = (tools.match(/##\s*🔐\s*SpeedCat[\s\S]*?\*\*邮箱\*\*:\s*([^\n\r]+)/) || [])[1]?.trim();
            const password = (tools.match(/##\s*🔐\s*SpeedCat[\s\S]*?\*\*密码\*\*:\s*([^\n\r]+)/) || [])[1]?.trim();
            if (email && password) {
              await send('Runtime.evaluate', {
                expression: `(() => {
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
                  const btn = [...document.querySelectorAll('button,input[type=submit],a')].find(el => {
                    const t = (el.innerText||el.value||'').trim();
                    return t.includes('登录') || t.toLowerCase().includes('login');
                  });
                  if (btn) { btn.click(); return 'clicked'; }
                  // fallback submit form
                  const form = emailEl.closest('form');
                  if (form) { form.submit(); return 'submitted'; }
                  return 'no-button';
                })()` ,
                awaitPromise: true,
                returnByValue: true,
              });
              await sleep(2000);
              await waitForLoad(send, 15000);
            }
          } catch {}

          const isLoggedIn3 = await send('Runtime.evaluate', {
            expression: `(() => {
              const t = document.body?.innerText || '';
              return t.includes('Hi,') && t.includes('@');
            })()` ,
            returnByValue: true,
          });
          if (!isLoggedIn3?.result?.value) {
            throw new Error('未登录（Profile/Cookies/自动登录均未生效）');
          }
        }
      }

      // Wait until dashboard cards appear (best-effort)
      const startWait = Date.now();
      while (Date.now() - startWait < 10000) {
        const has = await send('Runtime.evaluate', {
          expression: `(() => (document.body?.innerText || '').includes('剩余流量'))()` ,
          returnByValue: true,
        });
        if (has?.result?.value) break;
        await sleep(300);
      }

      // Try check-in (best-effort): click sign-in if available and not already "明日再来"
      try {
        const ck = await send('Runtime.evaluate', {
          expression: `(() => {
            const norm = (s) => (s || '').replace(/\s+/g,' ').trim();
            const labels = [...document.querySelectorAll('a,button')].map(el => norm(el.innerText || el.textContent));
            const hasTomorrow = labels.some(s => s.includes('明日再来'));
            if (hasTomorrow) return { status: '明日再来' };
            const btn = [...document.querySelectorAll('a,button')].find(el => {
              const t = norm(el.innerText || el.textContent);
              return t && t.includes('签到') && !t.includes('明日再来');
            });
            if (!btn) return { status: '-' };
            btn.click();
            return { status: 'clicked' };
          })()` ,
          returnByValue: true,
        });

        if (ck?.result?.value?.status === 'clicked') {
          await sleep(1200);
          // confirm modal if present
          await send('Runtime.evaluate', {
            expression: `(() => {
              const norm = (s) => (s || '').replace(/\s+/g,' ').trim();
              const ok = [...document.querySelectorAll('button,a')].find(el => {
                const t = norm(el.innerText || el.textContent);
                return t === 'OK' || t === 'Ok' || t === '确定' || t.includes('OK');
              });
              if (ok) ok.click();
              return true;
            })()` ,
            returnByValue: true,
          });
          await sleep(800);
        }
      } catch {}

      // Extract fields (best-effort)
      const extracted = await send('Runtime.evaluate', {
        expression: `(() => {
          const __DBG = ${process.env.SPEEDCAT_DEBUG === '1' ? 'true' : 'false'};
          const text = (el) => ((el && el.textContent) ? el.textContent : '').replace(/\s+/g,' ').trim();
          const hasDigit = (s) => {
            if (!s) return false;
            for (let i = 0; i < s.length; i++) {
              const c = s.charCodeAt(i);
              if (c >= 48 && c <= 57) return true;
            }
            return false;
          };
          const byHeading = (label) => {
            const h = [...document.querySelectorAll('h4,h3,h2')].find(x => text(x).includes(label));
            if (!h) return null;

            // Try a few container levels; SpeedCat cards are nested.
            const containers = [h.parentElement, h.parentElement && h.parentElement.parentElement, h.closest('div')].filter(Boolean);

            const hasDigit = (s) => {
              for (let i = 0; i < s.length; i++) {
                const c = s.charCodeAt(i);
                if (c >= 48 && c <= 57) return true;
              }
              return false;
            };

            const match = (s) => {
              if (!s) return false;
              if (s.indexOf(label) >= 0) return false;
              if (s === '' || s === '' || s === '' || s === '') return false;
              if (!hasDigit(s)) return false;
              if (label.indexOf('剩余流量') >= 0) return s.toUpperCase().indexOf('GB') >= 0;
              if (label.indexOf('钱包余额') >= 0) return s.indexOf('¥') >= 0;
              if (label.indexOf('在线IP') >= 0) return s.indexOf('/') >= 0;
              return true;
            };

            for (const c of containers) {
              const texts = [...c.querySelectorAll('div,span')].map(x => text(x)).filter(Boolean);
              const found = texts.find(match);
              if (found) return found;
            }
            return null;
          };

          const planH4 = [...document.querySelectorAll('h4')].find(x => /.+:/.test(text(x)) && !text(x).includes('剩余流量') && !text(x).includes('在线IP') && !text(x).includes('钱包余额'));
          const plan_name = planH4 ? text(planH4).replace(/:.*$/, '').replace(/:$/, '') : null;
          let days_left = null;
          // Prefer a global search to avoid DOM changes
          const bodyText = document.body ? (document.body.innerText || '') : '';
          const rawLines = bodyText.split('\\n');
          const lines = rawLines.map(s => (s || '').replace(/\\r/g,'').trim()).filter(Boolean);
          const dayLine = lines.find(s => s.indexOf('天') >= 0 && hasDigit(s));
          if (dayLine) {
            let num = '';
            for (let i = 0; i < dayLine.length; i++) {
              const c = dayLine.charCodeAt(i);
              if (c >= 48 && c <= 57) num += dayLine[i];
              else if (num) break;
            }
            days_left = num ? (num + ' 天') : null;
          }

          let reset_date = null;
          const resetLine = lines.find(s => s.indexOf('流量重置时间') >= 0);
          if (resetLine) {
            let tail = '';
            const i1 = resetLine.indexOf(':');
            const i2 = resetLine.indexOf('：');
            const ii = i1 >= 0 ? i1 : i2;
            if (ii >= 0) tail = resetLine.slice(ii + 1).trim();
            reset_date = tail || null;
          }

          const remaining = byHeading('剩余流量');
          const usedLine = [...document.querySelectorAll('li')].map(x => text(x)).find(s => s.includes('今日已用')) || null;

          const online = byHeading('在线IP数');
          const lastLine = [...document.querySelectorAll('li')].map(x => text(x)).find(s => s.includes('上次使用')) || null;

          const wallet = byHeading('钱包余额');
          const rebateLine = [...document.querySelectorAll('li')].map(x => text(x)).find(s => s.includes('累计获得返利金额')) || null;

          // checkin status
          const checkin = [...document.querySelectorAll('a,button')].map(x => text(x)).find(s => s.includes('明日再来') || s.includes('签到')) || null;

          try {
            const out = {
              plan_name,
              days_left,
              reset_date,
              remaining,
              usedLine,
              online,
              lastLine,
              wallet,
              rebateLine,
              checkin
            };
            if (__DBG) out.__body = bodyText.slice(0, 220);
            return out;
          } catch (e) {
            return { __error: String(e && e.message ? e.message : e) };
          }
        })()`,
        returnByValue: true,
      });

      if (extracted && extracted.exceptionDetails) {
        const ed = extracted.exceptionDetails;
        if (process.env.SPEEDCAT_DEBUG === '1') {
          try { console.error('DEBUG exceptionDetails:', JSON.stringify(ed)); } catch {}
        }
        const msg = ed && (ed.text || (ed.exception && ed.exception.description) || (ed.exception && ed.exception.value));
        return { __error: `Runtime.evaluate exception: ${msg || 'unknown'}` };
      }

      return (extracted && extracted.result && extracted.result.value) ? extracted.result.value : { __error: 'No value from evaluate' };
    });

    if (process.env.SPEEDCAT_DEBUG === '1') {
      try { console.error('DEBUG extracted:', JSON.stringify(result)); } catch {}
    }
    if (result && result.__error) {
      throw new Error(result.__error);
    }

    // Parse extracted
    if (result.plan_name) plan_name = result.plan_name;
    if (result.days_left) {
      const m = String(result.days_left).match(/(\d+)\s*天/);
      days_left = m ? m[1] : result.days_left;
    }
    if (result.reset_date) reset_date = result.reset_date;

    if (result.remaining) {
      const m = String(result.remaining).match(/([0-9.]+)\s*GB/i);
      remaining_gb = m ? fixed2(m[1]) : String(result.remaining);
    }

    if (result.usedLine) {
      const m = String(result.usedLine).match(/今日已用:\s*([0-9.]+)\s*GB/i);
      used_today_gb = m ? fixed2(m[1]) : '-';
    }

    if (result.wallet) {
      const m = String(result.wallet).match(/¥\s*([0-9.]+)/);
      wallet_cny = m ? fixed2(m[1]) : fixed2(result.wallet);
    }

    if (result.rebateLine) {
      const m = String(result.rebateLine).match(/¥\s*([0-9.]+)/);
      rebate_cny = m ? fixed2(m[1]) : '-';
    }

    if (result.online) online_ip = String(result.online);
    if (result.lastLine) {
      const m = String(result.lastLine).match(/上次使用:\s*(.+)$/);
      last_used = m ? m[1].trim() : String(result.lastLine);
    }

    if (result.checkin) {
      if (String(result.checkin).includes('明日再来')) checkin_status = '明日再来';
      else checkin_status = String(result.checkin);
    }

  } catch (e) {
    reason = e?.message || String(e);
  }

  const status = trafficStatus(remaining_gb);

  // Fixed template output (must be stable)
  // Note: expire_date is currently not parsed from page; keep '-' placeholder.
  if (reason) {
    // Still output template, but leave fields as '-' where unknown.
    // Put reason into checkin_status for visibility.
    checkin_status = `失败：${reason}`;
  }

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

main();
