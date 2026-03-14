#!/usr/bin/env node
/**
 * GYING weekly recommendation extractor (homepage-only, fixed output).
 * Stable version: extract from homepage text blocks only.
 */

const CDP_PORT = process.env.GYING_CDP_PORT || '9224';
const ORIGIN = `http://127.0.0.1:${CDP_PORT}`;
const TARGET_URL = 'https://www.gying.net/';

async function getJson(path) {
  const res = await fetch(`${ORIGIN}${path}`);
  if (!res.ok) throw new Error(`HTTP ${res.status} ${path}`);
  return res.json();
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
  try { return await fn({ send }); } finally { try { ws.close(); } catch {} }
}

function normalizeScore(v) {
  if (!v || v === '--') return '暂无评分';
  return /^\d+(\.\d+)?$/.test(v) ? v : '暂无评分';
}

function reasonFor(item) {
  const score = Number(item.score) || 0;
  if (score >= 8.5) return '口碑很稳，优先看';
  if (score >= 8) return '高分佳作，值得看';
  if (score >= 7) return '评分不错，可尝鲜';
  if (item.type === '剧集') return '更新中，适合追更';
  if (item.type === '动漫') return '热度在线，口碑稳';
  return '近期更新，可一试';
}

(async function main() {
  try {
    const list = await getJson('/json');
    const page = list.find(t => t.type === 'page' && typeof t.url === 'string' && t.url.includes('gying.net')) || list.find(t => t.type === 'page');
    if (!page?.webSocketDebuggerUrl) throw new Error('未找到 GYING 页面，请先启动专用 Chrome');

    const raw = await withCdp(page.webSocketDebuggerUrl, async ({ send }) => {
      await send('Page.enable');
      await send('Runtime.enable');
      await send('Page.navigate', { url: TARGET_URL });
      await sleep(2000);
      return await send('Runtime.evaluate', {
        expression: `(() => {
          const pageText = document.body ? document.body.innerText : '';
          const homeSignals = ['收藏', '观看历史', '最近更新的电影', '最近更新的剧集'];
          const signalCount = homeSignals.filter(s => pageText.includes(s)).length;
          const href = location.href;
          if (signalCount < 2 && href.includes('/user/login')) {
            return { ok: false, reason: '观影网专用 Profile 已掉登录，请重新登录后再运行推荐任务' };
          }

          const lines = pageText.split('\n').map(s => s.trim()).filter(Boolean);
          const pickSection = (name) => {
            const idx = lines.findIndex(x => x === name);
            if (idx < 0) return [];
            const out = [];
            for (let i = idx + 1; i < lines.length; i++) {
              const cur = lines[i];
              if (i > idx + 1 && ['最近更新的电影', '最近更新的剧集', '最近更新的动漫'].includes(cur)) break;
              if (cur === '更多 ❯') continue;
              out.push(cur);
              if (out.length > 80) break;
            }
            return out;
          };

          const parseSection = (sectionLines, type) => {
            const items = [];
            for (let i = 0; i < sectionLines.length - 2; i++) {
              const title = sectionLines[i];
              const score = sectionLines[i + 1];
              const meta = sectionLines[i + 2];
              if (!title || /^\d+(\.\d+)?$/.test(title) || title.includes('全') || title.startsWith('第')) continue;
              if (!meta || !/^\d{4}\s*\//.test(meta)) continue;
              items.push({ title, type, score, meta });
              i += 2;
            }
            return items;
          };

          return {
            ok: true,
            items: [
              ...parseSection(pickSection('最近更新的动漫'), '动漫'),
              ...parseSection(pickSection('最近更新的电影'), '电影'),
              ...parseSection(pickSection('最近更新的剧集'), '剧集')
            ]
          };
        })()`,
        returnByValue: true,
      });
    });

    const result = raw?.result?.value;
    if (!result?.ok) {
      process.stdout.write((result?.reason || '页面结果为空') + '\n');
      return;
    }

    const items = (result.items || [])
      .map(x => ({ ...x, scoreNum: Number(x.score) || 0 }))
      .sort((a, b) => b.scoreNum - a.scoreNum)
      .slice(0, 3);

    if (!items.length) {
      process.stdout.write('🎬 本周 GYING 推荐\n暂无可提取推荐｜影视｜暂无评分｜首页结构待调整\n暂无可提取推荐｜影视｜暂无评分｜首页结构待调整\n暂无可提取推荐｜影视｜暂无评分｜首页结构待调整\n');
      return;
    }

    const lines = ['🎬 本周 GYING 推荐'];
    for (const item of items) {
      lines.push(`${item.title}｜${item.type}｜${normalizeScore(item.score)}｜${reasonFor(item)}`);
    }
    while (lines.length < 4) lines.push('暂无补位条目｜影视｜暂无评分｜等待下次更新');
    process.stdout.write(lines.slice(0, 4).join('\n') + '\n');
  } catch (e) {
    process.stdout.write(`观影网任务执行失败：${e.message || String(e)}\n`);
    process.exitCode = 1;
  }
})();
