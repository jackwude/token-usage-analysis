(() => {
  const text = (el) => ((el && el.textContent) ? el.textContent : '').replace(/\s+/g, ' ').trim();
  const bodyText = document.body ? (document.body.innerText || '') : '';
  const lines = bodyText.split('\n').map(s => (s || '').trim()).filter(Boolean);

  // 辅助函数：从文本中提取数字 + 单位
  const extractNum = (str, unit) => {
    if (!str) return null;
    const regex = new RegExp(`([0-9.]+)\\s*${unit}`, 'i');
    const m = str.match(regex);
    return m ? m[1] : null;
  };

  // 套餐名称：尝试多种选择器
  const planH4 = [...document.querySelectorAll('h4,h3,.plan-name,.package-name')].find(x => /.+:/.test(text(x)) && !text(x).includes('剩余流量') && !text(x).includes('在线 IP') && !text(x).includes('钱包余额'));
  const plan_name = planH4 ? text(planH4).replace(/:.*$/, '').replace(/:$/, '') : null;

  // 剩余天数
  const dayLine = lines.find(s => s.includes('天') && /\d+/.test(s));
  let days_left = null;
  if (dayLine) {
    const m = dayLine.match(/(\d+)\s*天/);
    days_left = m ? m[1] : null;
  }

  // 流量重置时间
  const resetLine = lines.find(s => s.includes('流量重置')) || '';
  const reset_date = resetLine.split(/[:：]/).slice(1).join(':').trim() || null;

  // 剩余流量：尝试多种方式
  let remaining_gb = null;
  const remLine1 = lines.find(s => s.includes('剩余流量'));
  if (remLine1) {
    remaining_gb = extractNum(remLine1, 'GB');
    if (!remaining_gb) {
      const mb = extractNum(remLine1, 'MB');
      if (mb) remaining_gb = (parseFloat(mb) / 1024).toFixed(2);
    }
  }
  // fallback: 查找包含 GB 的数字
  if (!remaining_gb) {
    const gbLine = lines.find(s => /[0-9.]+\s*GB/.test(s));
    if (gbLine) remaining_gb = extractNum(gbLine, 'GB');
  }

  // 今日已用
  let used_today_gb = null;
  const usedLine = lines.find(s => s.includes('今日已用'));
  if (usedLine) {
    const gbMatch = usedLine.match(/([0-9.]+)\s*GB/i);
    const mbMatch = usedLine.match(/([0-9.]+)\s*MB/i);
    if (gbMatch) {
      used_today_gb = gbMatch[1];
    } else if (mbMatch) {
      used_today_gb = (parseFloat(mbMatch[1]) / 1024).toFixed(2);
    }
  }

  // 钱包余额：尝试多种方式
  let wallet_cny = null;
  const walletLine = lines.find(s => s.includes('钱包余额') || s.includes('余额'));
  if (walletLine) {
    const match = walletLine.match(/¥\s*([0-9.]+)/);
    if (match) wallet_cny = match[1];
  }

  // 累计返利
  let rebate_cny = null;
  const rebateLine = lines.find(s => s.includes('返利') || s.includes('累计'));
  if (rebateLine) {
    const match = rebateLine.match(/¥\s*([0-9.]+)/);
    if (match) rebate_cny = match[1];
  }

  // 在线 IP
  const onlineLine = lines.find(s => s.includes('在线 IP') || s.includes('IP 地址'));
  const online_ip = onlineLine ? onlineLine.split(/[:：]/).slice(1).join(':').trim() : null;

  // 上次使用
  const lastLine = lines.find(s => s.includes('上次使用') || s.includes('最后使用'));
  const last_used = lastLine ? lastLine.split(/[:：]/).slice(1).join(':').trim() : null;

  // 签到状态
  const checkin = [...document.querySelectorAll('a,button,span')].map(x => text(x)).find(s => s.includes('明日再来') || s.includes('签到') || s.includes('已签到'));

  return {
    plan_name, days_left, reset_date,
    remaining_gb, used_today_gb,
    wallet_cny, rebate_cny,
    online_ip, last_used,
    checkin
  };
})()
