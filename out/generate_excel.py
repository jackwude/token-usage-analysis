#!/usr/bin/env python3
import json
import os
from datetime import datetime, timezone, timedelta
from openpyxl import Workbook

# 当前时间（2026-03-08 18:18 GMT+8）
now = datetime.now(timezone(timedelta(hours=8)))
seven_days_ago = now - timedelta(days=7)

def timestamp_to_datetime(ts_ms):
    """将毫秒时间戳转换为 datetime"""
    if not ts_ms:
        return None
    return datetime.fromtimestamp(ts_ms / 1000, tz=timezone(timedelta(hours=8)))

def is_within_7_days(ts_ms):
    """检查时间是否在 7 天内"""
    if not ts_ms:
        return False
    dt = timestamp_to_datetime(ts_ms)
    return dt >= seven_days_ago

def load_detail(filepath):
    """加载详情文件"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except:
        return None

def extract_note_info(detail_data, keyword):
    """从详情数据中提取笔记信息"""
    if not detail_data or 'data' not in detail_data or 'note' not in detail_data['data']:
        return None
    
    note = detail_data['data']['note']
    time_ms = note.get('time')
    
    # 验证时间是否在 7 天内
    if not is_within_7_days(time_ms):
        print(f"  跳过：时间不在 7 天内 ({timestamp_to_datetime(time_ms)})")
        return None
    
    user = note.get('user', {})
    interact = note.get('interactInfo', {})
    
    note_id = note.get('noteId', '')
    xsec_token = note.get('xsecToken', '')
    
    info = {
        'keyword': keyword,
        'note_id': note_id,
        'xsec_token': xsec_token,
        'title': note.get('title', '') or '(无标题)',
        'author_nickname': user.get('nickname', '') or user.get('nickName', ''),
        'publish_time': timestamp_to_datetime(time_ms).isoformat() if time_ms else '',
        'like_count': interact.get('likedCount', '0'),
        'comment_count': interact.get('commentCount', '0'),
        'collect_count': interact.get('collectedCount', '0'),
        'url': f'https://www.xiaohongshu.com/discovery/item/{note_id}',
        'desc_full': note.get('desc', ''),
        'fetched_at': now.isoformat()
    }
    return info

def main():
    # 收集所有笔记信息
    all_notes = []
    
    # 关键词 1: 游戏助手 卸载
    print("处理关键词 1: 游戏助手 卸载")
    k1_notes = []
    for i in range(1, 10):
        filepath = f'/Users/fx/.openclaw/workspace/out/detail_k1_n{i}.json'
        if os.path.exists(filepath):
            detail = load_detail(filepath)
            info = extract_note_info(detail, '游戏助手 卸载')
            if info:
                k1_notes.append(info)
                print(f"  有效笔记 {len(k1_notes)}: {info['title'][:30]}...")
                if len(k1_notes) >= 2:
                    break
    all_notes.extend(k1_notes[:2])
    print(f"  关键词 1 完成：{len(k1_notes[:2])} 条")
    
    # 关键词 2: 游戏助手 关闭
    print("\n处理关键词 2: 游戏助手 关闭")
    k2_notes = []
    for i in range(1, 10):
        filepath = f'/Users/fx/.openclaw/workspace/out/detail_k2_n{i}.json'
        if os.path.exists(filepath):
            detail = load_detail(filepath)
            info = extract_note_info(detail, '游戏助手 关闭')
            if info:
                k2_notes.append(info)
                print(f"  有效笔记 {len(k2_notes)}: {info['title'][:30]}...")
                if len(k2_notes) >= 2:
                    break
    all_notes.extend(k2_notes[:2])
    print(f"  关键词 2 完成：{len(k2_notes[:2])} 条")
    
    # 关键词 3: 游戏助手 异常
    print("\n处理关键词 3: 游戏助手 异常")
    k3_notes = []
    for i in range(1, 10):
        filepath = f'/Users/fx/.openclaw/workspace/out/detail_k3_n{i}.json'
        if os.path.exists(filepath):
            detail = load_detail(filepath)
            info = extract_note_info(detail, '游戏助手 异常')
            if info:
                k3_notes.append(info)
                print(f"  有效笔记 {len(k3_notes)}: {info['title'][:30]}...")
                if len(k3_notes) >= 2:
                    break
    all_notes.extend(k3_notes[:2])
    print(f"  关键词 3 完成：{len(k3_notes[:2])} 条")
    
    # 生成 Excel
    print(f"\n生成 Excel，共 {len(all_notes)} 条记录...")
    wb = Workbook()
    ws = wb.active
    ws.title = "小红书笔记"
    
    # 表头
    headers = ['keyword', 'note_id', 'xsec_token', 'title', 'author_nickname', 
               'publish_time', 'like_count', 'comment_count', 'collect_count', 
               'url', 'desc_full', 'fetched_at']
    ws.append(headers)
    
    # 数据行
    for note in all_notes:
        row = [note.get(h, '') for h in headers]
        ws.append(row)
    
    # 调整列宽
    for col in ws.columns:
        max_length = 0
        column = col[0].column_letter
        for cell in col:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        adjusted_width = min(max_length + 2, 100)
        ws.column_dimensions[column].width = adjusted_width
    
    # 保存
    output_path = '/Users/fx/.openclaw/workspace/out/xhs_game_assistant_week7.xlsx'
    wb.save(output_path)
    print(f"Excel 已保存：{output_path}")
    
    # 输出摘要
    print("\n=== 摘要 ===")
    for note in all_notes:
        print(f"[{note['keyword']}] {note['title'][:40]} | {note['author_nickname']} | {note['publish_time'][:10]}")
    
    return output_path, all_notes

if __name__ == '__main__':
    main()
