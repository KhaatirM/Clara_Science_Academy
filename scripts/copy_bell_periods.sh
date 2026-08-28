#!/usr/bin/env bash
# Copy the 4th grade bell periods to grades 5-8 on the live server.
#
#   bash scripts/copy_bell_periods.sh            # apply
#   bash scripts/copy_bell_periods.sh --dry-run  # preview only
set -euo pipefail

cd "$(dirname "$0")/.."

SOURCE_GRADE="${SOURCE_GRADE:-4}"
TARGET_GRADES="${TARGET_GRADES:-5,6,7,8}"

python scripts/copy_bell_periods.py \
  --source "$SOURCE_GRADE" \
  --targets "$TARGET_GRADES" \
  "$@"
