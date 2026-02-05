#!/bin/bash
# Reload snd-quantum2626: stop audio, kill anything using card 4, rmmod, insmod, start audio.
# Run with: ./scripts/reload_quantum_driver.sh
# Optional: MODPARAMS="reg_srate_offset=0x108 reg_srate_value=48000" ./scripts/reload_quantum_driver.sh
# Optional: RELOAD_ONLY=1 ... (do not start pipewire at the end)
# Optional: RELOAD_FORCE_MASK=1 ... (mask user audio so it cannot respawn; unmask at end)
# If rmmod still fails, log out completely, switch to TTY2 (Ctrl+Alt+F2), run:
#   sudo rmmod snd_quantum2626 && sudo insmod /home/jamie/source/Quantum2626/driver/snd-quantum2626.ko
# Then switch back (Ctrl+Alt+F1) and log in.

set -e
DRIVER_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/driver"
CARD=4

# Stop socket first so nothing restarts pipewire when we stop it
echo "Stopping user audio (socket, then services)..."
systemctl --user stop pipewire.socket 2>/dev/null || true
systemctl --user stop pipewire-pulse 2>/dev/null || true
systemctl --user stop pipewire 2>/dev/null || true
systemctl --user stop wireplumber 2>/dev/null || true
sleep 3

if [ -n "${RELOAD_FORCE_MASK:-}" ]; then
  echo "Masking user audio (prevents respawn)..."
  systemctl --user mask pipewire.socket pipewire pipewire-pulse wireplumber 2>/dev/null || true
  sleep 2
  for dev in /dev/snd/controlC$CARD /dev/snd/pcmC${CARD}D0p /dev/snd/pcmC${CARD}D0c; do
    [ -e "$dev" ] && sudo fuser -k "$dev" 2>/dev/null || true
  done
  sleep 2
fi

echo "Releasing Quantum (card $CARD): stop + kill until free..."
MAX_TRIES=12
for try in $(seq 1 $MAX_TRIES); do
  # Stop again each time (wireplumber/pipewire can respawn)
  systemctl --user stop pipewire.socket pipewire-pulse pipewire wireplumber 2>/dev/null || true
  sleep 2
  killed=
  for dev in /dev/snd/controlC$CARD /dev/snd/pcmC${CARD}D0p /dev/snd/pcmC${CARD}D0c; do
    if [ -e "$dev" ]; then
      pids=$(sudo fuser "$dev" 2>/dev/null || true)
      for pid in $pids; do
        if [ -n "$pid" ]; then
          sudo kill -9 "$pid" 2>/dev/null && echo "  [try $try/$MAX_TRIES] Killed PID $pid" && killed=1
        fi
      done
    fi
  done
  still=$(sudo lsof /dev/snd/controlC$CARD /dev/snd/pcmC${CARD}D0p /dev/snd/pcmC${CARD}D0c 2>/dev/null || true)
  if [ -z "$still" ]; then
    echo "  Card $CARD free after $try attempt(s)."
    break
  fi
  if [ $try -eq $MAX_TRIES ]; then
    echo "ERROR: After $MAX_TRIES tries, something still has the Quantum open:"
    echo "$still"
    echo ""
    echo "Last resort: run with RELOAD_FORCE_MASK=1 to temporarily mask user audio:"
    echo "  RELOAD_FORCE_MASK=1 ./scripts/reload_quantum_driver.sh"
    echo "Or log out, TTY2: sudo rmmod snd_quantum2626 && sudo insmod $DRIVER_DIR/snd-quantum2626.ko"
    exit 1
  fi
  sleep 1
done

still=$(sudo lsof /dev/snd/controlC$CARD /dev/snd/pcmC${CARD}D0p /dev/snd/pcmC${CARD}D0c 2>/dev/null || true)
if [ -n "$still" ]; then
  echo "ERROR: Something still has the Quantum open:"
  echo "$still"
  exit 1
fi

echo "Unloading module..."
sudo rmmod snd_quantum2626
echo "Loading module..."
if [ -n "${MODPARAMS:-}" ]; then
  echo "  with params: $MODPARAMS"
  sudo insmod "$DRIVER_DIR/snd-quantum2626.ko" $MODPARAMS
else
  sudo insmod "$DRIVER_DIR/snd-quantum2626.ko"
fi
if [ -n "${RELOAD_FORCE_MASK:-}" ]; then
  echo "Unmasking user audio..."
  systemctl --user unmask pipewire.socket pipewire pipewire-pulse wireplumber 2>/dev/null || true
fi
if [ -z "${RELOAD_ONLY:-}" ]; then
  echo "Starting user audio..."
  systemctl --user start pipewire pipewire-pulse wireplumber 2>/dev/null || true
fi
echo "Done."
