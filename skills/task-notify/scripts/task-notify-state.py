#!/usr/bin/env python3
import argparse
import json
import os
import sys
import time
from pathlib import Path

DEFAULT_PATH = Path('/Users/fx/.openclaw/workspace/task-state.json')


def load(path: Path):
    if not path.exists():
        return {"activeTasks": [], "completedTasks": []}
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return {"activeTasks": [], "completedTasks": []}


def save(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding='utf-8')


def find_active(data, task_id):
    for task in data.get('activeTasks', []):
        if task.get('id') == task_id:
            return task
    return None


def now_ts():
    return int(time.time())


def cmd_start(args):
    data = load(args.path)
    existing = find_active(data, args.id)
    if existing:
        existing.update({
            'label': args.label,
            'status': 'running',
            'eta': args.eta or existing.get('eta'),
            'started': existing.get('started', now_ts()),
            'updated': now_ts(),
            'progress': 0,
            'note': args.note or existing.get('note', ''),
            'kind': args.kind or existing.get('kind', 'generic'),
        })
    else:
        data.setdefault('activeTasks', []).append({
            'id': args.id,
            'label': args.label,
            'kind': args.kind or 'generic',
            'status': 'running',
            'started': now_ts(),
            'updated': now_ts(),
            'eta': args.eta or '',
            'progress': 0,
            'note': args.note or '',
        })
    save(args.path, data)
    print(f"started {args.id}")


def cmd_progress(args):
    data = load(args.path)
    task = find_active(data, args.id)
    if not task:
        print(f"task not found: {args.id}", file=sys.stderr)
        sys.exit(1)
    task['updated'] = now_ts()
    if args.progress is not None:
        task['progress'] = args.progress
    if args.note is not None:
        task['note'] = args.note
    save(args.path, data)
    print(f"progress {args.id}")


def cmd_done(args):
    data = load(args.path)
    task = find_active(data, args.id)
    if not task:
        task = {
            'id': args.id,
            'label': args.label or args.id,
            'kind': args.kind or 'generic',
            'started': now_ts(),
            'progress': args.progress if args.progress is not None else 100,
        }
    else:
        data['activeTasks'] = [t for t in data.get('activeTasks', []) if t.get('id') != args.id]
    task['updated'] = now_ts()
    task['finished'] = now_ts()
    task['status'] = 'done'
    task['result'] = args.result
    if args.progress is not None:
        task['progress'] = args.progress
    else:
        task['progress'] = task.get('progress', 100)
    if args.note is not None:
        task['note'] = args.note
    data.setdefault('completedTasks', []).append(task)
    data['completedTasks'] = data['completedTasks'][-50:]
    save(args.path, data)
    print(f"done {args.id}")


def cmd_fail(args):
    args.result = 'failure'
    cmd_done(args)


def build_parser():
    p = argparse.ArgumentParser()
    p.add_argument('--path', type=Path, default=DEFAULT_PATH)
    sub = p.add_subparsers(dest='cmd', required=True)

    s = sub.add_parser('start')
    s.add_argument('id')
    s.add_argument('label')
    s.add_argument('--eta')
    s.add_argument('--note')
    s.add_argument('--kind')
    s.set_defaults(func=cmd_start)

    s = sub.add_parser('progress')
    s.add_argument('id')
    s.add_argument('--progress', type=int)
    s.add_argument('--note')
    s.set_defaults(func=cmd_progress)

    s = sub.add_parser('done')
    s.add_argument('id')
    s.add_argument('--result', default='success')
    s.add_argument('--note')
    s.add_argument('--progress', type=int)
    s.add_argument('--label')
    s.add_argument('--kind')
    s.set_defaults(func=cmd_done)

    s = sub.add_parser('fail')
    s.add_argument('id')
    s.add_argument('--note')
    s.add_argument('--progress', type=int)
    s.add_argument('--label')
    s.add_argument('--kind')
    s.set_defaults(func=cmd_fail)
    return p


if __name__ == '__main__':
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)
