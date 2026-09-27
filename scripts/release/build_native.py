#!/usr/bin/env python3
"""Build native DKMS packages from one verified, extracted RFC source bundle."""

import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[2]
HOMEPAGE = "https://github.com/jamie-steele/presonus-quantum-linux"


def write(path, text, executable=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    path.chmod(0o755 if executable else 0o644)


def package_version(bundle, revision):
    upstream = (bundle / "VERSION").read_text().strip()
    if not re.fullmatch(r"[0-9]{8}\.rfc[0-9]+\.s[0-9]+", upstream):
        raise ValueError("Invalid RFC version")
    if not re.fullmatch(r"[1-9][0-9]*", revision):
        raise ValueError("Packaging revision must be a positive integer")
    return upstream, f"{upstream}-{revision}"


def stage(bundle, destination, version):
    source = destination / "usr/src" / f"quantum-{version}"
    shutil.copytree(bundle / "module", source)
    config = source / "dkms.conf"
    original = config.read_text()
    updated, count = re.subn(r'^PACKAGE_VERSION="[^"]+"$',
                            f'PACKAGE_VERSION="{version}"', original, flags=re.MULTILINE)
    if count != 1:
        raise ValueError("Unexpected DKMS version declaration")
    config.write_text(updated)
    shutil.copytree(bundle / "alsa/ucm2", destination / "usr/share/alsa/ucm2")
    # Each WirePlumber generation reads only its own configuration directory.
    for name, directory in (("51-quantum2626.lua", "main.lua.d"),
                            ("51-quantum2626.conf", "wireplumber.conf.d")):
        target = destination / "usr/share/wireplumber" / directory / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(bundle / "alsa/wireplumber" / name, target)
    target = destination / "etc/modprobe.d/quantum2626-backend.conf"
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(bundle / "quantum2626-backend.conf", target)
    documentation = destination / "usr/share/doc/quantum-dkms"
    documentation.mkdir(parents=True)
    for name in ("manifest.json", "README.md", "LICENSE.repository"):
        shutil.copyfile(bundle / name, documentation / name)
    shutil.copyfile(bundle / "module/COPYING", documentation / "COPYING")
    shutil.copytree(bundle / "patches", documentation / "patches")


def lifecycle(version, command):
    common = (ROOT / "packaging/native/lifecycle.sh").read_text()
    return f'#!/bin/sh\nversion="{version}"\n' + common + "\n" + command + "\n"


def build_deb(payload, output, version, environment):
    control = payload / "DEBIAN"
    write(control / "control", f"""Package: quantum-dkms
Version: {version}
Section: kernel
Priority: optional
Architecture: amd64
Maintainer: PreSonus Quantum Linux contributors <jamie-steele@users.noreply.github.com>
Depends: dkms (>= 3), build-essential, kmod, alsa-ucm-conf, wireplumber (>= 0.4), initramfs-tools
Homepage: {HOMEPAGE}
Description: Experimental PreSonus Quantum RFC driver and desktop audio profiles
 Nicholas Johnson's unmerged snd-quantum RFC, built locally through DKMS.
 Includes Quantum 2626 ALSA UCM and WirePlumber desktop integration.
 Matching kernel headers must be installed before configuring this package.
""")
    write(control / "conffiles", "/etc/modprobe.d/quantum2626-backend.conf\n")
    scripts = {
        "postinst": 'case "${1:-}" in configure) configure_module ;; esac',
        "prerm": 'case "${1:-}" in remove|upgrade|deconfigure) remove_module ;; esac',
        "postrm": 'case "${1:-}" in remove|purge) refresh_boot_images ;; esac',
    }
    for name, command in scripts.items():
        write(control / name, lifecycle(version, command), executable=True)
    subprocess.run(["dpkg-deb", "--root-owner-group", "--build", str(payload),
                    str(output / f"quantum-dkms_{version}_amd64.deb")],
                   check=True, env=environment)


def build_rpm(payload, output, upstream, revision, family, work, environment):
    top = work / family
    top.mkdir()
    release = revision + (".fc43" if family == "fedora" else ".suse")
    dependencies = "alsa-ucm" if family == "fedora" else "alsa-ucm-conf"
    version = f"{upstream}-{revision}"
    files = []
    for path in sorted(payload.rglob("*")):
        name = "/" + str(path.relative_to(payload))
        if path.is_dir() and (name.startswith(f"/usr/src/quantum-{version}")
                              or name.startswith("/usr/share/doc/quantum-dkms")
                              or name == "/usr/share/alsa/ucm2/P2626"):
            files.append("%dir " + name)
        elif path.is_file():
            prefix = "%config(noreplace) " if name.startswith("/etc/") else ""
            files.append(prefix + name)
    common = lifecycle(version, "")
    spec = f"""Name: quantum-dkms
Version: {upstream}
Release: {release}
Summary: Experimental PreSonus Quantum RFC driver and desktop audio profiles
License: GPL-2.0-only AND MIT
URL: {HOMEPAGE}
BuildArch: x86_64
Requires: dkms >= 3, gcc, make, kmod, {dependencies}, wireplumber >= 0.4, dracut
Requires(preun): dkms
Requires(post): dkms
AutoReqProv: no

%description
Nicholas Johnson's unmerged snd-quantum RFC, built locally through DKMS.
Includes Quantum 2626 ALSA UCM and WirePlumber desktop integration.
Install matching kernel-devel (Fedora) or kernel-default-devel (openSUSE) first.

%install
mkdir -p %{{buildroot}}
cp -a {payload}/. %{{buildroot}}/

%post
{common}
configure_module

%preun
{common}
# On same-version reinstall the new instance uses the same DKMS registration.
if [ "${{1:-0}}" = 0 ] || rpm -q --queryformat '%%{{VERSION}}-%%{{RELEASE}}\\n' quantum-dkms | grep -Fxv '{upstream}-{release}' >/dev/null; then
    remove_module
fi

%postun
{common}
refresh_boot_images

%files
%defattr(-,root,root,-)
{chr(10).join(files)}
"""
    spec_path = top / "quantum.spec"
    write(spec_path, spec)
    subprocess.run(["rpmbuild", "-bb", "--define", f"_topdir {top}",
                    "--define", "_buildhost reproducible", "--define", "debug_package %{nil}",
                    "--define", "use_source_date_epoch_as_buildtime 1",
                    "--define", "clamp_mtime_to_source_date_epoch 1", str(spec_path)],
                   check=True, env=environment)
    for rpm in (top / "RPMS").rglob("*.rpm"):
        shutil.copyfile(rpm, output / rpm.name)


def build(bundle, output, revision):
    upstream, version = package_version(bundle, revision)
    output.mkdir(parents=True, exist_ok=False)
    timestamp = int(datetime.datetime.strptime(upstream[:8], "%Y%m%d").replace(
        tzinfo=datetime.timezone.utc).timestamp())
    environment = dict(os.environ, SOURCE_DATE_EPOCH=str(timestamp))
    with tempfile.TemporaryDirectory(prefix="quantum-native-") as temporary:
        work = Path(temporary)
        payload = work / "payload"
        stage(bundle, payload, version)
        build_rpm(payload, output, upstream, revision, "fedora", work, environment)
        build_rpm(payload, output, upstream, revision, "opensuse", work, environment)
        build_deb(payload, output, version, environment)
    metadata = {
        "upstream": json.loads((bundle / "manifest.json").read_text()),
        "native_version": version,
        "packaging_commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "packaging_dirty": bool(subprocess.check_output(
            ["git", "status", "--porcelain"], cwd=ROOT)),
    }
    write(output / f"native-{revision}-manifest.json", json.dumps(metadata, indent=2) + "\n")
    checksums = "".join(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}\n"
                        for path in sorted(output.iterdir()))
    write(output / f"native-{revision}-SHA256SUMS", checksums)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--revision", default=(ROOT / "packaging/native/revision").read_text().strip())
    arguments = parser.parse_args()
    build(arguments.bundle.resolve(), arguments.output.resolve(), arguments.revision)
