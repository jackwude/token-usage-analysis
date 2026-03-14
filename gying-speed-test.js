const { chromium } = require('playwright');
const path = require('path');
const os = require('os');

const GYING_PROFILE = path.join(os.homedir(), '.openclaw/chrome-profiles/gying');
const BASE_URL = 'https://www.gying.net/';

// Timing results storage
const results = {
  A: [], // profile 专用目录
  B: []  // state/session 复用 (fresh profile each time)
};

async function runTestRound(mode, roundNum) {
  const timings = {
    mode,
    round: roundNum,
    stages: {},
    total: 0,
    success: false,
    error: null,
    notes: []
  };
  
  let context;
  let page;
  
  try {
    const startTime = Date.now();
    
    if (mode === 'A') {
      // Use dedicated gying profile
      context = await chromium.launchPersistentContext(GYING_PROFILE, {
        headless: true,
        args: ['--disable-blink-features=AutomationControlled']
      });
    } else {
      // Fresh profile each time (simulating no saved state)
      const tempDir = path.join(os.tmpdir(), `gying-test-b-${Date.now()}-${roundNum}`);
      context = await chromium.launchPersistentContext(tempDir, {
        headless: true,
        args: ['--disable-blink-features=AutomationControlled']
      });
    }
    
    page = context.pages()[0] || await context.newPage();
    
    // Stage 1: Open homepage
    const stage1Start = Date.now();
    await page.goto(BASE_URL, { waitUntil: 'domcontentloaded', timeout: 30000 });
    timings.stages.homepage = Date.now() - stage1Start;
    
    const currentUrl = page.url();
    
    // Check login state
    if (currentUrl.includes('/user/login')) {
      timings.notes.push('需要登录');
      timings.isLoggedIn = false;
      
      // For this test, we'll still measure homepage load time
      // but note that full flow requires login
      timings.total = Date.now() - startTime;
      timings.success = true; // Partial success - homepage loaded
      timings.partialSuccess = true;
      
      console.log(`~ ${mode}-R${roundNum}: ${timings.total}ms (首页:${timings.stages.homepage}ms) - 需要登录`);
    } else {
      timings.isLoggedIn = true;
      
      // Stage 2: Search (only if logged in)
      const stage2Start = Date.now();
      const searchSelector = 'input[type="text"], input[name="keyword"], input[name="q"], .search-input, [placeholder*="搜索"]';
      const searchInput = page.locator(searchSelector).first();
      await searchInput.fill('寻秦记', { timeout: 10000 });
      await searchInput.press('Enter', { timeout: 10000 });
      await page.waitForLoadState('domcontentloaded', { timeout: 15000 });
      timings.stages.search = Date.now() - stage2Start;
      
      // Stage 3: Enter detail page
      const stage3Start = Date.now();
      const firstResult = page.locator('a[href*="/detail/"], a[href*="/movie/"], .result-item a').first();
      await firstResult.click({ timeout: 10000 });
      await page.waitForLoadState('domcontentloaded', { timeout: 15000 });
      timings.stages.detail = Date.now() - stage3Start;
      
      // Stage 4: Extract links
      const stage4Start = Date.now();
      await page.waitForSelector('a[href*="pan.baidu"], a[href*="pan.quark"]', { timeout: 15000 });
      
      const links = await page.evaluate(() => {
        const baiduLinks = [];
        const quarkLinks = [];
        document.querySelectorAll('a').forEach(link => {
          const href = link.href;
          const text = link.textContent.trim().toLowerCase();
          if (href.includes('pan.baidu') || href.includes('baidu.com/s') || text.includes('百度')) {
            baiduLinks.push({ href });
          } else if (href.includes('pan.quark') || href.includes('quark.cn') || text.includes('夸克')) {
            quarkLinks.push({ href });
          }
        });
        return baiduLinks.length > 0 ? baiduLinks.slice(0, 3) : quarkLinks.slice(0, 3);
      });
      
      timings.stages.extract = Date.now() - stage4Start;
      timings.extractedLinks = links.length;
      timings.total = Date.now() - startTime;
      timings.success = true;
      
      console.log(`✓ ${mode}-R${roundNum}: ${timings.total}ms (首页:${timings.stages.homepage}ms, 搜索:${timings.stages.search}ms, 详情:${timings.stages.detail}ms, 提取:${timings.stages.extract}ms)`);
    }
    
  } catch (error) {
    timings.error = error.message;
    timings.total = Date.now() - startTime;
    console.log(`✗ ${mode}-R${roundNum}: 失败 - ${error.message}`);
  } finally {
    try {
      await context?.close();
    } catch (e) {}
  }
  
  return timings;
}

async function runAllTests() {
  console.log('🚀 开始 gying.net 测速对比测试\n');
  console.log('📁 A 方案：Profile 专用目录 (~/.openclaw/chrome-profiles/gying)');
  console.log('📁 B 方案：State/Session 复用 (每次新建临时 profile)\n');
  
  console.log('=== A 方案测试 ===\n');
  for (let i = 1; i <= 3; i++) {
    const result = await runTestRound('A', i);
    results.A.push(result);
    await new Promise(r => setTimeout(r, 1000));
  }
  
  console.log('\n=== B 方案测试 ===\n');
  for (let i = 1; i <= 3; i++) {
    const result = await runTestRound('B', i);
    results.B.push(result);
    await new Promise(r => setTimeout(r, 1000));
  }
  
  // Calculate statistics
  console.log('\n=== 统计结果 ===\n');
  
  function calcStats(data, label) {
    const successful = data.filter(r => r.success);
    const times = successful.map(r => r.total);
    const partialSuccess = successful.filter(r => r.partialSuccess);
    
    if (times.length === 0) {
      console.log(`${label}: 无成功数据\n`);
      return null;
    }
    
    times.sort((a, b) => a - b);
    const mean = times.reduce((a, b) => a + b, 0) / times.length;
    const median = times[Math.floor(times.length / 2)];
    const min = times[0];
    const max = times[times.length - 1];
    
    const deviations = times.map(t => Math.abs(t - median));
    deviations.sort((a, b) => a - b);
    const mad = deviations[Math.floor(deviations.length / 2)];
    
    console.log(`${label}:`);
    console.log(`  成功率：${successful.length}/${data.length} (${Math.round(successful.length/data.length*100)}%)`);
    if (partialSuccess.length > 0) {
      console.log(`  部分成功 (需登录): ${partialSuccess.length}/${data.length}`);
    }
    console.log(`  首页加载均值：${Math.round(mean)}ms`);
    console.log(`  P50/中位数：${Math.round(median)}ms`);
    console.log(`  范围：${min}ms - ${max}ms`);
    console.log(`  稳定性 (MAD): ${Math.round(mad)}ms`);
    console.log('');
    
    return { mean, median, mad, min, max, successRate: successful.length/data.length };
  }
  
  const statsA = calcStats(results.A, 'A 方案 (Profile 专用)');
  const statsB = calcStats(results.B, 'B 方案 (State 复用)');
  
  // Conclusion
  console.log('=== 结论 ===\n');
  
  if (statsA && statsB) {
    const speedDiff = statsB.mean - statsA.mean;
    const speedDiffPercent = Math.round(Math.abs(speedDiff) / statsA.mean * 100);
    
    if (Math.abs(speedDiff) < 100) {
      console.log('两者首页加载速度相近');
    } else if (speedDiff > 0) {
      console.log(`A 方案比 B 方案快约 ${speedDiff}ms (${speedDiffPercent}%)`);
    } else {
      console.log(`B 方案比 A 方案快约 ${Math.abs(speedDiff)}ms (${speedDiffPercent}%)`);
    }
    
    if (statsA.mad < statsB.mad) {
      console.log('A 方案稳定性更好 (MAD 更低)');
    } else {
      console.log('B 方案稳定性更好 (MAD 更低)');
    }
    
    console.log('\n⚠️  注意：完整测试需要登录状态。当前测试仅测量首页加载时间。');
    console.log('💡 建议：使用 Chrome 扩展 relay (profile="chrome") 并 attach 已登录的标签页进行完整测试。');
  }
  
  // Output summary JSON
  console.log('\n=== 原始数据 ===\n');
  console.log(JSON.stringify({ results, stats: { A: statsA, B: statsB } }, null, 2));
}

runAllTests().catch(console.error);
