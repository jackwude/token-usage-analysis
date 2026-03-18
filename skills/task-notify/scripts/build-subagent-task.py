#!/usr/bin/env python3
import argparse

TEMPLATE = '''{task}

Notification requirements (balanced mode, mandatory):
- This task is user-visible and may take time.
- Send milestone updates only at: START, 25%, 50%, 75%, and FINAL.
- Do not send high-frequency micro-updates between milestones.
- If no meaningful progress happened, skip interim updates.
- Milestone messages should be concise: what changed + current stage + any blocker.
- FINAL message must include: outcome (success/failed/timeout), elapsed time (if known), key outputs/paths, and next recommended step.
- On failure/timeout, also include: likely cause, what you already tried, and best next action.
- Prefer one clear final summary over fragmented chatter.
'''


def main():
    p = argparse.ArgumentParser()
    p.add_argument('task', help='Base task text for the sub-agent')
    args = p.parse_args()
    print(TEMPLATE.format(task=args.task.strip()))


if __name__ == '__main__':
    main()
