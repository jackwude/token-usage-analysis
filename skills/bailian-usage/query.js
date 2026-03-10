#!/usr/bin/env node

/**
 * 百炼套餐用量查询脚本
 * 自动登录阿里云百炼控制台并获取套餐信息
 */

const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

// 配置
const BAILIAN_URL = 'https://bailian.console.aliyun.com/cn-beijing/?tab=coding-plan#/efm/index';
const TOOLS_PATH = path.join(process.env.HOME, '.openclaw/workspace/TOOLS.md');

// 从 TOOLS.md 读取账号信息
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

// 主函数
async function main() {
    console.log('🔍 开始查询百炼套餐用量...\n');
    
    // 读取账号
    const creds = readCredentials();
    console.log(`✓ 已读取账号：${creds.account}`);
    
    // 注意：实际浏览器自动化需要通过 OpenClaw browser 工具执行
    // 这个脚本主要用于演示流程，实际执行由 Agent 调用 browser 工具完成
    
    console.log('\n📋 查询流程：');
    console.log('1. 打开百炼控制台');
    console.log('2. 登录账号');
    console.log('3. 进入"我的订阅"页面');
    console.log('4. 提取套餐信息');
    console.log('5. 关闭页面');
    
    console.log('\n✅ 请通过 OpenClaw browser 工具执行实际查询');
}

main().catch(err => {
    console.error('❌ 错误:', err.message);
    process.exit(1);
});
