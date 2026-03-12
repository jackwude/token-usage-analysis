#!/usr/bin/env python3
import argparse

TEMPLATE = '''{task}

Notification requirements:
- This task is user-visible and may take time.
- Report only major milestones, not every small action.
- Preferred cadence: at most every 2-3 minutes, or on meaningful milestones such as 25% / 50% / 75% / final.
- Good milestone examples: environment ready, data gathered, processing started, processing finished, result packaged, blocked on X.
- If there is no meaningful change, do not send a progress update.
- Final response must include: outcome, total time if known, key outputs/paths, and next recommended step.
- Keep updates short and practical.
- Prefer one clear final summary over many fragmented messages.
'''


def main():
    p = argparse.ArgumentParser()
    p.add_argument('task', help='Base task text for the sub-agent')
    args = p.parse_args()
    print(TEMPLATE.format(task=args.task.strip()))


if __name__ == '__main__':
    main()
