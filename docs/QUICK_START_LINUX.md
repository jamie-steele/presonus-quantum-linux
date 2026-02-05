# Quick Start - Linux Testing

## Fast Track

```bash
# 1. Build
cd driver
make

# 2. Load with debug
sudo insmod snd-quantum2626.ko dump_on_trigger=1

# 3. Check status
dmesg | tail -30
../scripts/linux_test_driver.sh

# 4. Check LED
# Blue LED should be SOLID if initialized correctly

# 5. Test playback
aplay /usr/share/sounds/alsa/Front_Left.wav

# 6. Watch dmesg
sudo dmesg -w
```

## What to Report

1. **LED Status:** Solid or not solid?
2. **dmesg output:** Copy register values
3. **Audio:** Plays or no sound?
4. **Errors:** Any errors in dmesg?

## Full Guide

See `docs/LINUX_TESTING_GUIDE.md` for detailed instructions.
