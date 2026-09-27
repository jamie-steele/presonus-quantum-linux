#!/usr/bin/env python3
"""Parse UCM offline against a virtual card; never open a hardware PCM."""

from pathlib import Path
import json
import os
import shutil
import subprocess
import sys
import tempfile


def main():
    audio = Path(sys.argv[1]).resolve()
    with tempfile.TemporaryDirectory(prefix="quantum-ucm-") as directory:
        root = Path(directory)
        shutil.copytree("/usr/share/alsa/ucm2", root / "ucm2", symlinks=True)
        shutil.copytree(audio / "ucm2", root / "ucm2", dirs_exist_ok=True)
        environment = dict(os.environ, ALSA_CONFIG_UCM2=str(root / "ucm2"))
        result = subprocess.run(
            ["alsaucm", "-c", "P2626", "dump", "json"],
            env=environment, capture_output=True, text=True,
        )
        if result.returncode:
            sys.stderr.write(result.stderr)
            result.check_returncode()
        profile = json.loads(result.stdout)["Verbs"]["HiFi"]
        playback = []
        capture = []
        for device in profile["Devices"].values():
            values = device["Values"]
            if "PlaybackPCM" in values:
                if int(values["PlaybackChannels"]) != 2:
                    raise ValueError("Playback endpoints must be stereo")
                bindings = values["PlaybackPCM"].split(",")[-2:]
                playback.extend(int(channel) for channel in bindings)
            if "CapturePCM" in values:
                if int(values["CaptureChannels"]) != 1:
                    raise ValueError("Capture endpoints must be mono")
                capture.append(int(values["CapturePCM"].rsplit(",", 1)[1]))
        if sorted(playback) != list(range(26)) or sorted(capture) != list(range(26)):
            raise ValueError("UCM must cover all 26 channels exactly once per direction")
        print("UCM parsed: 13 stereo outputs, 26 mono inputs, exact channel coverage; no PCM opened")


if __name__ == "__main__":
    main()
