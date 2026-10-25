#!/usr/bin/env python3
"""Reproduce and test the Quantum UCM stall through full ACP, without hardware."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time


ROOT = Path(__file__).resolve().parents[2]
UCM_SHA256 = "15925edf379b6e98dedf0362a9efe6132a3e1ceb9972351f7b19a02a50af0517"
ACP_SOURCES = ("acp.c", "compat.c", "alsa-mixer.c", "alsa-ucm.c", "alsa-util.c", "conf-parser.c")


def run(arguments, **options):
    return subprocess.run(arguments, check=True, text=True, **options)


def write(path, contents):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(contents)


def create_profile(stock, destination, count, conflicts=()):
    shutil.copytree(stock, destination, symlinks=True)
    write(destination / "P2626/P2626.conf", '''Syntax 4
SectionUseCase."HiFi" {
    Comment "Synthetic compatibility test"
    File "/P2626/HiFi.conf"
}
''')
    devices = []
    for index in range(count):
        incompatible = []
        for first, second in conflicts:
            if first == index:
                incompatible.append(second)
            elif second == index:
                incompatible.append(first)
        restrictions = ""
        if incompatible:
            names = " ".join(f'"Line{other}"' for other in incompatible)
            restrictions = f"    ConflictingDevice [ {names} ]\n"
        devices.append(f'''SectionDevice."Line{index}" {{
{restrictions}    Value {{
        PlaybackPCM "null:Line{index}"
        PlaybackChannels 2
        PlaybackPriority {1000 - index}
    }}
}}
''')
    write(destination / "P2626/HiFi.conf", "\n".join(devices))


def compile_variant(source, directory, name, ucm_source):
    acp = source / "spa/plugins/alsa/acp"
    include = [f"-I{directory}", f"-I{source / 'spa/include'}", f"-I{acp}"]
    files = [ucm_source if filename == "alsa-ucm.c" else acp / filename
             for filename in ACP_SOURCES]
    library = directory / f"libacp-{name}.so"
    run(["cc", "-shared", "-fPIC", "-O1", "-g", "-D_GNU_SOURCE",
         "-DHAVE_ALSA_UCM", "-DHAVE_READLINK", *include,
         *map(str, files), "-lasound", "-lm", "-o", str(library)])
    executable = directory / f"discovery-{name}"
    run(["cc", "-Wall", "-Wextra", "-Werror", "-O1", "-g", "-rdynamic",
         f"-I{acp}", str(ROOT / "tests/fixtures/acp/discovery.c"),
         f"-L{directory}", f"-Wl,-rpath,{directory}", f"-l:{library.name}",
         "-lasound", "-ldl", "-o", str(executable)])
    return executable


def discover(executable, ucm, directory, name, devices, profiles, expect_timeout=False):
    environment = dict(os.environ, ALSA_CONFIG_UCM2=str(ucm),
                       ALSA_CONFIG_PATH=str(directory / "asound.conf"),
                       ACP_TEST_DEVICES=str(devices), ACP_TEST_PROFILES=str(profiles))
    start = time.monotonic()
    result = subprocess.run([str(executable)], env=environment, capture_output=True,
                            text=True, timeout=8)
    elapsed = time.monotonic() - start
    write(directory / f"{name}.stdout", result.stdout)
    write(directory / f"{name}.stderr", result.stderr)
    if expect_timeout:
        if result.returncode != 124 or "pcm_opens=0" not in result.stderr:
            raise RuntimeError(f"{name}: expected pre-PCM discovery stall, got {result.returncode}")
    elif result.returncode:
        raise RuntimeError(f"{name} failed ({result.returncode}): {result.stderr}")
    layout = []
    for line in result.stdout.splitlines():
        if line.startswith("PROFILE\t"):
            _, profile, *members = line.split("\t")
            layout.append((profile, sorted(members)))
    print(f"{name}: exit={result.returncode}, elapsed={elapsed:.3f}s", flush=True)
    return {"case": name, "returncode": result.returncode, "elapsed_seconds": elapsed,
            "profiles": sorted(layout)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="Extracted, unmodified PipeWire 1.6.2 source")
    arguments = parser.parse_args()
    if Path("/dev/snd").exists():
        raise RuntimeError("Run in a disposable container without sound devices; see packaging/pipewire/README.md")
    source = arguments.source.resolve()
    acp = source / "spa/plugins/alsa/acp"
    if hashlib.sha256((acp / "alsa-ucm.c").read_bytes()).hexdigest() != UCM_SHA256:
        raise ValueError("Expected the unmodified PipeWire 1.6.2 alsa-ucm.c")
    directory = Path(tempfile.mkdtemp(prefix="quantum-full-acp-", dir="/tmp"))
    print(f"Evidence: {directory}", flush=True)
    write(directory / "config.h", f'''#define PACKAGE_VERSION "1.6.2"
#define HAVE_ALSA_UCM 1
#define HAVE_READLINK 1
#define PA_ALSA_DATA_DIR "{source / 'spa/plugins/alsa/mixer'}"
''')
    # Only Valgrind instrumentation is disabled; ACP logic remains unchanged.
    write(directory / "valgrind/memcheck.h",
          "#define VALGRIND_MAKE_MEM_DEFINED(address, length) ((void)0)\n")
    write(directory / "asound.conf", "pcm.null { type null }\n")
    patched_root = directory / "patched"
    patched_ucm = patched_root / "spa/plugins/alsa/acp/alsa-ucm.c"
    patched_ucm.parent.mkdir(parents=True)
    shutil.copyfile(acp / "alsa-ucm.c", patched_ucm)
    run(["git", "-C", str(patched_root), "apply",
         str(ROOT / "packaging/pipewire/0001-stop-after-complete-ucm-profile.patch")])
    original = compile_variant(source, directory, "original", acp / "alsa-ucm.c")
    fixed = compile_variant(source, directory, "fixed", patched_ucm)
    stock = Path("/usr/share/alsa/ucm2")
    quantum = directory / "quantum-ucm2"
    shutil.copytree(stock, quantum, symlinks=True)
    shutil.copytree(ROOT / "alsa/ucm2", quantum, dirs_exist_ok=True)
    results = [discover(original, quantum, directory, "quantum-original", 39, 2, True),
               discover(fixed, quantum, directory, "quantum-fixed", 39, 2)]
    for name, count, conflicts, profiles in (
        ("single", 1, (), 2),
        ("compatible-four", 4, (), 2),
        ("pair-conflict", 3, ((0, 1),), 3),
        ("chain-conflict", 3, ((0, 1), (1, 2)), 3),
        ("two-conflict-pairs", 4, ((0, 1), (2, 3)), 5),
    ):
        fixture = directory / f"{name}-ucm2"
        create_profile(stock, fixture, count, conflicts)
        before = discover(original, fixture, directory, f"{name}-original", count, profiles)
        after = discover(fixed, fixture, directory, f"{name}-fixed", count, profiles)
        if before["profiles"] != after["profiles"]:
            raise RuntimeError(f"{name}: changed maximal profiles or device membership")
        results.extend((before, after))
    write(directory / "results.json", json.dumps(results, indent=2) + "\n")
    print("PASS: full ACP Quantum discovery completes after patch; all compatibility layouts preserved.")


if __name__ == "__main__":
    main()
