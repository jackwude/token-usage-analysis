#!/bin/bash
set -euo pipefail

PROFILES=(
  "$HOME/.openclaw/chrome-profiles/bailian"
  "$HOME/.openclaw/chrome-profiles/speedcat"
  "$HOME/.openclaw/chrome-profiles/gying"
)
LOG_DIR="$HOME/.openclaw/logs"
LOG_FILE="$LOG_DIR/cleanup-browser-profile-cache.log"
mkdir -p "$LOG_DIR"

stamp() { date '+%Y-%m-%d %H:%M:%S'; }
log() { printf '[%s] %s\n' "$(stamp)" "$*" | tee -a "$LOG_FILE"; }

for PROFILE in "${PROFILES[@]}"; do
  if [ ! -d "$PROFILE" ]; then
    log "profile not found: $PROFILE"
    continue
  fi

  log "start cleanup: $PROFILE"
  CANDIDATES=(
    "$PROFILE/Cache"
    "$PROFILE/Code Cache"
    "$PROFILE/GPUCache"
    "$PROFILE/Default/Cache"
    "$PROFILE/Default/Code Cache"
    "$PROFILE/Default/GPUCache"
  )

  for dir in "${CANDIDATES[@]}"; do
    if [ -d "$dir" ]; then
      size=$(du -sh "$dir" 2>/dev/null | awk '{print $1}')
      rm -rf "$dir"
      log "removed: $dir (${size:-unknown})"
    else
      log "skip missing: $dir"
    fi
  done

  final_size=$(du -sh "$PROFILE" 2>/dev/null | awk '{print $1}')
  log "profile size now: ${final_size:-unknown}"
  log "done cleanup: $PROFILE"
  log "---"
done
