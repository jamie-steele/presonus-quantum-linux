#!/bin/bash
# Capture dmesg during playback for dump_on_trigger comparison.
# Prereq: driver loaded with dump_on_trigger=1 (see driver README).
# Stop wireplumber first so the Quantum card is free.

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
NOTES="$REPO_ROOT/notes"
STAMP="$(date +%Y%m%d_%H%M)"
OUT="$NOTES/MMIO_during_playback_$STAMP.txt"

# Card number for Quantum (often 4; check with: cat /proc/asound/cards)
CARD="${QUANTUM_CARD:-4}"

mkdir -p "$NOTES"
echo "Stop wireplumber so card $CARD is free:" >&2
echo "  systemctl --user stop wireplumber" >&2
echo "Then run this script. It will start aplay for 4s and capture dmesg." >&2
read -p "Continue? [y/N] " -n 1 -r; echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then exit 0; fi

aplay -D "plughw:$CARD,0" -r 48000 -f S16_LE -c 2 /dev/zero &
APID=$!
sleep 4
kill $APID 2>/dev/null || true
wait $APID 2>/dev/null || true

sudo dmesg | grep -E "MMIO|quantum|prepare|trigger" | tail -120 > "$OUT"
echo "Saved to $OUT" >&2
echo "Start wireplumber again: systemctl --user start wireplumber" >&2
