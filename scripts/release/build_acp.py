#!/usr/bin/env python3
"""Build the private Quantum ACP plugin from a checksum-pinned PipeWire release.

Build inside Ubuntu 22.04 for the supported x86_64 glibc baseline. Nothing is
installed into the build host, and the supplied upstream source is not modified.
"""

import argparse
import hashlib
import json
import re
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[2]
VERSION = "1.6.2"
SOURCE_URL = f"https://codeload.github.com/PipeWire/pipewire/tar.gz/refs/tags/{VERSION}"
SOURCE_SHA256 = "2014c187fccdd6d245585be4eda7dabd781dcddd921604c40ab015bba6cb042d"
ACP_SOURCES = ("acp.c", "compat.c", "alsa-mixer.c", "alsa-ucm.c", "alsa-util.c", "conf-parser.c")
DATA_PATH = "/usr/share/quantum-dkms/acp"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(archive, output):
    if digest(archive) != SOURCE_SHA256:
        raise ValueError("PipeWire source archive checksum mismatch")
    if output.exists():
        raise ValueError("Output directory must not exist")
    with tempfile.TemporaryDirectory(prefix="quantum-acp-build-") as temporary:
        work = Path(temporary)
        with tarfile.open(archive) as source:
            # Only the exact pinned archive reaches extraction.
            source.extractall(work)
        source = work / f"pipewire-{VERSION}"
        subprocess.run(["git", "-C", str(source), "apply",
                        str(ROOT / "packaging/pipewire/0001-stop-after-complete-ucm-profile.patch")], check=True)
        (work / "config.h").write_text(f'''#define PACKAGE_VERSION "{VERSION}"
#define HAVE_ALSA_UCM 1
#define HAVE_READLINK 1
#define PA_ALSA_DATA_DIR "{DATA_PATH}"
''')
        (work / "valgrind").mkdir()
        (work / "valgrind/memcheck.h").write_text(
            "#define VALGRIND_MAKE_MEM_DEFINED(address, length) ((void)0)\n")
        acp = source / "spa/plugins/alsa/acp"
        plugin = work / "libspa-alsa.so"
        subprocess.run([
            "cc", "-shared", "-fPIC", "-fvisibility=hidden", "-O2", "-D_GNU_SOURCE",
            "-DHAVE_ALSA_UCM", "-DHAVE_READLINK",
            f"-I{work}", f"-I{source / 'spa/include'}", f"-I{acp}",
            str(ROOT / "packaging/pipewire/plugin.c"),
            str(source / "spa/plugins/alsa/alsa-acp-device.c"),
            *[str(acp / name) for name in ACP_SOURCES],
            "-Wl,-z,defs", "-Wl,-Bsymbolic", "-lasound", "-lm", "-ldl", "-pthread", "-o", str(plugin),
        ], check=True)
        symbols = subprocess.check_output(["readelf", "--version-info", str(plugin)], text=True)
        versions = [tuple(map(int, value.split(".")))
                    for value in re.findall(r"GLIBC_([0-9]+\.[0-9]+)", symbols)]
        if any(version > (2, 35) for version in versions):
            raise ValueError("Build on Ubuntu 22.04: plugin exceeds the glibc 2.35 baseline")
        header = subprocess.check_output(["readelf", "-h", str(plugin)], text=True)
        if "Advanced Micro Devices X86-64" not in header:
            raise ValueError("Native packages currently support x86_64 only")
        output.mkdir(parents=True)
        shutil.copy2(plugin, output / plugin.name)
        shutil.copytree(source / "spa/plugins/alsa/mixer", output / "data")
        # Retain upstream copyright/license notices with the redistributed code.
        shutil.copy2(source / "COPYING", output / "COPYING")
        shutil.copy2(source / "LICENSE", output / "LICENSE")
        shutil.copy2(Path("/usr/share/common-licenses/LGPL-2.1"), output / "LGPL-2.1")
        rebuild = output / "source"
        for relative in ("packaging/pipewire/plugin.c",
                         "packaging/pipewire/0001-stop-after-complete-ucm-profile.patch",
                         "scripts/release/build_acp.py"):
            target = rebuild / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / relative, target)
        shutil.copy2(archive, rebuild / f"pipewire-{VERSION}.tar.gz")
        metadata = {
            "pipewire_version": VERSION,
            "source_url": SOURCE_URL,
            "source_sha256": SOURCE_SHA256,
            "router_sha256": digest(ROOT / "packaging/pipewire/plugin.c"),
            "patch_sha256": digest(ROOT / "packaging/pipewire/0001-stop-after-complete-ucm-profile.patch"),
            "plugin_sha256": digest(output / plugin.name),
            "architecture": "x86_64",
            "glibc_max": ".".join(map(str, max(versions))),
        }
        (output / "manifest.json").write_text(json.dumps(metadata, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--archive", type=Path)
    arguments = parser.parse_args()
    if arguments.archive:
        build(arguments.archive.resolve(), arguments.output.resolve())
    else:
        with tempfile.TemporaryDirectory(prefix="quantum-acp-download-") as temporary:
            archive = Path(temporary) / "pipewire.tar.gz"
            with urlopen(SOURCE_URL, timeout=60) as response, archive.open("wb") as destination:
                shutil.copyfileobj(response, destination)
            build(archive, arguments.output.resolve())
