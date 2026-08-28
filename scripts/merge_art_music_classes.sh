#!/usr/bin/env bash
# Merge each grade's separate Art and Music classes into one Art/Music class.
#
#   bash scripts/merge_art_music_classes.sh --dry-run  # preview only
#   bash scripts/merge_art_music_classes.sh            # apply
set -euo pipefail

cd "$(dirname "$0")/.."

GRADES="${GRADES:-0,1,2,3,4,5,6,7,8}"

python scripts/merge_art_music_classes.py --grades "$GRADES" "$@"
