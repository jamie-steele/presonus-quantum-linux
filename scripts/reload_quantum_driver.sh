#!/bin/bash
# Reload snd-quantum2626: stop audio, kill anything using card 4, rmmod, insmod, start audio.
# Run with: ./scripts/reload_quantum_driver.sh
# If rmmod still fails, log out completely, switch to TTY2 (Ctrl+Alt+F2), run:
#   sudo rmmod snd_quantum2626 && sudo insmod /home/jamie/source/Quantum2626/driver/snd-quantum2626.ko
# Then switch back (Ctrl+Alt+F1) and log in.

set -e
DRIVER_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/driver"
CARD=4

echo "Stopping user audio services (pipewire first so wireplumber doesn't respawn)..."
systemctl --user stop pipewire-pulse 2>/dev/null || true
systemctl --user stop wireplumber 2>/dev/null || true
systemctl --user stop pipewire 2>/dev/null || true
sleep 4

echo "Killing any process using Quantum (card $CARD)..."
for try in 1 2 3 4 5; do
  killed=
  for dev in /dev/snd/controlC$CARD /dev/snd/pcmC${CARD}D0p /dev/snd/pcmC${CARD}D0c; do
    if [ -e "$dev" ]; then
      pids=$(sudo fuser "$dev" 2>/dev/null || true)
      for pid in $pids; do
        if [ -n "$pid" ]; then
          sudo kill -9 "$pid" 2>/dev/null && echo "  Killed PID $pid" && killed=1
        fi
      done
    fi
  done
  sleep 2
  still=$(sudo lsof /dev/snd/controlC$CARD /dev/snd/pcmC${CARD}D0p /dev/snd/pcmC${CARD}D0c 2>/dev/null || true)
  if [ -z "$still" ]; then
    break
  fi
  if [ -z "$killed" ] && [ -n "$still" ]; then
    echo "ERROR: Something still has the Quantum open and did not exit:"
    echo "$still"
    echo "Log out completely, switch to TTY2 (Ctrl+Alt+F2), run:"
    echo "  sudo rmmod snd_quantum2626 && sudo insmod $DRIVER_DIR/snd-quantum2626.ko"
    echo "Then Ctrl+Alt+F1 and log in again."
    exit 1
  fi
done

still=$(sudo lsof /dev/snd/controlC$CARD /dev/snd/pcmC${CARD}D0p /dev/snd/pcmC${CARD}D0c 2>/dev/null || true)
if [ -n "$still" ]; then
  echo "ERROR: Something still has the Quantum open:"
  echo "$still"
  echo "Log out completely, switch to TTY2 (Ctrl+Alt+F2), run:"
  echo "  sudo rmmod snd_quantum2626 && sudo insmod $DRIVER_DIR/snd-quantum2626.ko"
  echo "Then Ctrl+Alt+F1 and log in again."
  exit 1
fi

echo "Unloading module..."
sudo rmmod snd_quantum2626
echo "Loading module..."
sudo insmod "$DRIVER_DIR/snd-quantum2626.ko"
echo "Starting user audio..."
systemctl --user start pipewire pipewire-pulse wireplumber 2>/dev/null || true
echo "Done."
