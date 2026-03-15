#!/usr/bin/env python3
import requests
import time
import json

API_KEY = "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"
TIMEOUT = 60

MODELS = [
    "meta/llama-3.3-70b-instruct",
    "meta/llama-3.1-405b-instruct",
    "meta/llama-3.2-90b-vision-instruct",
    "google/gemma-3-27b-it",
    "deepseek-ai/deepseek-v3.2",
    "deepseek-ai/deepseek-r1-distill-qwen-32b",
    "nvidia/llama-3.1-nemotron-70b-instruct",
    "nvidia/nemotron-4-340b-instruct",
    "qwen/qwen3.5-397b-a17b",
    "moonshotai/kimi-k2.5",
    "minimaxai/minimax-m2.5",
    "minimaxai/minimax-m2.1",
]

results = []

print("🚀 开始测试 NVIDIA 模型延迟 (超时：60 秒)")
print("=" * 60)

for model in MODELS:
    print(f"📊 测试 {model} ... ", end="", flush=True)
    
    start_time = time.time()
    
    try:
        response = requests.post(
            "https://integrate.api.nvidia.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": model,
                "messages": [{"role": "user", "content": "Say hello"}],
                "max_tokens": 10
            },
            timeout=TIMEOUT
        )
        
        elapsed = time.time() - start_time
        
        if response.status_code == 200:
            results.append({
                "model": model,
                "status": "✅",
                "time": elapsed,
                "error": None
            })
            print(f"{elapsed:.2f}s ✅")
        else:
            results.append({
                "model": model,
                "status": "❌",
                "time": None,
                "error": f"HTTP {response.status_code}: {response.text[:100]}"
            })
            print(f"失败 (HTTP {response.status_code})")
            
    except requests.exceptions.Timeout:
        elapsed = time.time() - start_time
        results.append({
            "model": model,
            "status": "❌",
            "time": None,
            "error": f"超时 (>60s)"
        })
        print(f"❌ 超时")
        
    except Exception as e:
        elapsed = time.time() - start_time
        results.append({
            "model": model,
            "status": "❌",
            "time": None,
            "error": str(e)[:100]
        })
        print(f"❌ 错误：{e}")

print("")
print("=" * 60)
print("📋 测试结果汇总（按延迟排序）")
print("=" * 60)
print("")

# 排序：成功的按时间排序，失败的排后面
successful = [r for r in results if r["status"] == "✅"]
failed = [r for r in results if r["status"] == "❌"]

successful.sort(key=lambda x: x["time"])

print("| 排名 | 模型 | 状态 | 响应时间 (秒) |")
print("|------|------|------|---------------|")

rank = 1
for r in successful:
    print(f"| {rank} | {r['model']} | {r['status']} | {r['time']:.2f} |")
    rank += 1

for r in failed:
    error_short = r['error'][:30] + "..." if len(r['error']) > 30 else r['error']
    print(f"| {rank} | {r['model']} | {r['status']} | 失败 ({error_short}) |")
    rank += 1

print("")
print("=" * 60)
print("💡 推荐建议")
print("=" * 60)

if successful:
    fastest = successful[0]
    print(f"\n🏆 最快模型：{fastest['model']} ({fastest['time']:.2f}秒)")
    
    # 按速度分级
    fast = [r for r in successful if r['time'] < 2]
    medium = [r for r in successful if 2 <= r['time'] < 5]
    slow = [r for r in successful if r['time'] >= 5]
    
    print(f"\n⚡ 快速 (<2s): {len(fast)} 个模型")
    for r in fast:
        print(f"  - {r['model']} ({r['time']:.2f}s)")
    
    print(f"\n🐢 中等 (2-5s): {len(medium)} 个模型")
    for r in medium:
        print(f"  - {r['model']} ({r['time']:.2f}s)")
    
    print(f"\n🐌 慢速 (>5s): {len(slow)} 个模型")
    for r in slow:
        print(f"  - {r['model']} ({r['time']:.2f}s)")
    
    print(f"\n❌ 失败/超时：{len(failed)} 个模型")
    for r in failed:
        print(f"  - {r['model']}: {r['error'][:50]}")
    
    print("\n📌 综合推荐:")
    if fast:
        print(f"  1. 追求速度：{fast[0]['model']}")
    if len(successful) >= 3:
        # 推荐前 3 快的
        print(f"  2. 备选方案：{[r['model'].split('/')[-1] for r in successful[:3]]}")

print("")
print("=" * 60)

# 保存结果到文件
with open("nvidia-model-test-results.json", "w") as f:
    json.dump(results, f, indent=2)

print("📁 结果已保存到：nvidia-model-test-results.json")
