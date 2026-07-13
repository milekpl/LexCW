#!/usr/bin/env bash
# Backup IPA ML models to Mega.nz
set -euo pipefail

LOG="/home/milek/flask-app/instance/logs/ipa_model_backup.log"
mkdir -p "$(dirname "$LOG")"

echo "=== $(date): IPA model backup start ===" >> "$LOG"

if rclone sync /home/milek/flask-app/instance/ipa_models/ MEGA:ipa_models/ \
    --progress \
    --log-file "$LOG" \
    --log-level INFO \
    2>&1; then
    echo "=== $(date): IPA model backup complete ===" >> "$LOG"
else
    echo "=== $(date): IPA model backup FAILED (exit $?) ===" >> "$LOG"
fi
