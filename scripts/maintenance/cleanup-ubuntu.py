#!/usr/bin/env python3
"""Preview or remove known Quantum Linux installations on Ubuntu. Never unload audio."""

import argparse
import datetime
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import uuid


PROFILE_PATHS = (
    "usr/share/alsa/ucm2/P2626/P2626.conf",
    "usr/share/alsa/ucm2/P2626/HiFi.conf",
    "usr/share/alsa/ucm2/conf.d/snd-quantum/snd-quantum.conf",
    "usr/share/alsa/ucm2/conf.d/snd-quantum2626/snd-quantum2626.conf",
    "usr/share/wireplumber/main.lua.d/51-quantum2626.lua",
    "usr/share/wireplumber/wireplumber.conf.d/51-quantum2626.conf",
    "etc/modprobe.d/quantum2626-backend.conf",
)
USER_PATHS = (
    ".config/pipewire/pipewire.conf.d/51-quantum2626-rate.conf",
    ".config/wireplumber/main.lua.d/51-quantum2626.lua",
    ".config/wireplumber/wireplumber.conf.d/51-quantum2626.conf",
)
VERSION = re.compile(r"[0-9]{8}\.rfc[0-9]+\.s[0-9]+(?:-[1-9][0-9]*)?")
MODULE = re.compile(r"snd[-_]quantum(?:2626)?\.ko(?:\.(?:xz|gz|zst))?")
REFERENCE = re.compile(r"quantum|P2626", re.IGNORECASE)


def command(arguments, allowed=(0,)):
    result = subprocess.run(arguments, text=True, capture_output=True, env=dict(os.environ, LC_ALL="C"))
    if result.returncode not in allowed:
        raise RuntimeError(f"{' '.join(arguments)} failed: {result.stderr.strip()}")
    return result


def owners(path):
    names = [str(path)]
    # dpkg records literal paths; merged-/usr aliases must not hide ownership.
    if str(path).startswith("/lib/"):
        names.append("/usr" + str(path))
    elif str(path).startswith("/usr/lib/"):
        names.append(str(path).removeprefix("/usr"))
    found = set()
    for name in names:
        result = command(["dpkg-query", "-S", name], allowed=(0, 1))
        found.update(line.rsplit(": ", 1)[0] for line in result.stdout.splitlines() if ": " in line)
    return sorted(found)


def safe_path(root, path):
    """Reject symlinks rather than following a cleanup candidate into another tree."""
    relative = path.relative_to(root)
    current = root
    for part in relative.parts:
        current = current / part
        # Ubuntu's merged-/usr layout is the only permitted directory alias.
        if current == root / "lib" and current.is_symlink():
            if (current.readlink() in (Path("usr/lib"), Path("/usr/lib"))
                    and current.resolve() == (root / "usr/lib").resolve()):
                continue
        if current.is_symlink():
            return False
    return True


def discover(root=Path("/"), user_home=None, remove_apt=False):
    plan = {"package": False, "dkms_versions": [], "files": [], "sources": [], "review": []}
    status = command(["dpkg-query", "-W", "-f=${db:Status-Abbrev}", "quantum-dkms"], allowed=(0, 1))
    plan["package"] = status.returncode == 0 and status.stdout[:2] not in ("un", "pn")
    if shutil.which("dkms"):
        registrations = command(["dkms", "status"]).stdout
        for line in registrations.splitlines():
            if not line.startswith("quantum/"):
                if re.match(r"snd[-_]quantum(?:2626)?/|quantum2626/", line):
                    plan["review"].append(f"Unrecognized Quantum DKMS identity preserved: {line}")
                continue
            version = line.split("/", 1)[1].split(",", 1)[0].split(":", 1)[0].strip()
            if VERSION.fullmatch(version):
                plan["dkms_versions"].append(version)
            else:
                plan["review"].append(f"Unrecognized DKMS registration: {line}")
    elif (root / "var/lib/dkms/quantum").exists():
        plan["review"].append("Quantum DKMS state exists but dkms is unavailable; repair DKMS first")
    plan["dkms_versions"] = sorted(set(plan["dkms_versions"]))

    def candidate(path, destination="files"):
        if not path.exists() and not path.is_symlink():
            return
        if not safe_path(root, path):
            plan["review"].append(f"Symlink preserved: {path}")
            return
        if destination == "files" and not path.is_file():
            plan["review"].append(f"Unexpected file type preserved: {path}")
            return
        ownership = owners(path)
        if any(owner not in ("quantum-dkms", "quantum-dkms:amd64") for owner in ownership):
            plan["review"].append(f"Other package owns {path}: {', '.join(ownership)}")
            return
        plan[destination].append(str(path))

    for relative in PROFILE_PATHS:
        candidate(root / relative)
    modules = root / "lib/modules"
    if modules.exists() and safe_path(root, modules):
        for kernel in sorted(modules.iterdir()):
            if not kernel.is_dir() or not safe_path(root, kernel):
                continue
            for directory in ("updates", "extra"):
                location = kernel / directory
                if location.is_symlink():
                    plan["review"].append(f"Symlink preserved: {location}")
                    continue
                if location.is_dir():
                    for path in sorted(location.rglob("*")):
                        if MODULE.fullmatch(path.name):
                            candidate(path)
    source_root = root / "usr/src"
    if source_root.is_dir() and safe_path(root, source_root):
        for path in sorted(source_root.glob("quantum-*")):
            version = path.name.removeprefix("quantum-")
            config = path / "dkms.conf"
            if VERSION.fullmatch(version) and safe_path(root, config) and config.is_file():
                text = config.read_text()
                name_ok = re.search(r'^PACKAGE_NAME=[\'\"]quantum[\'\"]\s*$', text, re.MULTILINE)
                version_ok = re.search(
                    rf'^PACKAGE_VERSION=[\'\"]{re.escape(version)}[\'\"]\s*$', text, re.MULTILINE)
                if name_ok and version_ok and not any(item.is_symlink() for item in path.rglob("*")):
                    candidate(path, "sources")
                    continue
            plan["review"].append(f"Unrecognized source tree preserved: {path}")
    if user_home is not None:
        for relative in USER_PATHS:
            candidate(user_home / relative)
    if remove_apt:
        source = root / "etc/apt/sources.list.d/quantum.sources"
        if source.is_file() and safe_path(root, source):
            text = source.read_text()
            if (text.count("URIs:") == 1
                    and "URIs: https://jamie-steele.github.io/presonus-quantum-linux\n" in text
                    and text.count("Types:") == 1):
                candidate(source)
                candidate(root / "etc/apt/keyrings/quantum-archive-keyring.gpg")
            else:
                plan["review"].append(f"Customized APT source preserved: {source}")

    # Custom or shared configs are evidence to review, never grounds for broad deletion.
    scanned = ("etc/modprobe.d", "etc/modules-load.d", "etc/pipewire/pipewire.conf.d",
               "etc/wireplumber/main.lua.d", "etc/wireplumber/wireplumber.conf.d")
    selected = set(plan["files"])
    directories = [root / relative for relative in scanned]
    shared_files = [root / "etc/asound.conf", root / "etc/modules"]
    if user_home is not None:
        directories.extend(user_home / relative for relative in (
            ".config/pipewire/pipewire.conf.d", ".config/pipewire/client.conf.d",
            ".config/wireplumber/main.lua.d", ".config/wireplumber/wireplumber.conf.d"))
        shared_files.append(user_home / ".asoundrc")
    for directory in directories:
        if not safe_path(root, directory) or not directory.is_dir():
            continue
        for path in sorted(directory.iterdir()):
            if str(path) not in selected and safe_path(root, path) and path.is_file():
                if path.stat().st_size <= 1024 * 1024 and REFERENCE.search(path.read_text(errors="replace")):
                    plan["review"].append(f"Custom/shared configuration preserved: {path}")
    for path in shared_files:
        if safe_path(root, path) and path.is_file() and path.stat().st_size <= 1024 * 1024:
            if REFERENCE.search(path.read_text(errors="replace")):
                plan["review"].append(f"Custom/shared configuration preserved: {path}")
    return plan


def apply(plan, root=Path("/")):
    if os.geteuid() != 0:
        raise RuntimeError("Apply requires root; run the preview first")
    os_release = (root / "etc/os-release").read_text()
    if not re.search(r'^ID=[\'\"]?ubuntu[\'\"]?$', os_release, re.MULTILINE):
        raise RuntimeError("Apply is currently supported only on Ubuntu")
    if any("dkms is unavailable" in item for item in plan["review"]):
        raise RuntimeError("Cannot remove Quantum DKMS state without dkms")
    # Package removal runs its own maintainer scripts. No force/dependency bypass.
    # Save every present package file as well as our manual-install candidates.
    paths = {Path(name) for name in plan["files"] + plan["sources"]}
    if plan["package"]:
        for name in command(["dpkg-query", "-L", "quantum-dkms"]).stdout.splitlines():
            path = root / name.lstrip("/")
            if path.is_file() or path.is_symlink():
                paths.add(path)
    if not paths and not plan["package"] and not plan["dkms_versions"]:
        print("No recognized Quantum installation remains. Nothing changed.")
        return None
    for path in paths:
        if not safe_path(root, path):
            raise RuntimeError(f"Unsafe backup path; no cleanup performed: {path}")
    modules = root / "lib/modules"
    kernels = []
    if modules.is_dir() and safe_path(root, modules):
        kernels = [path.name for path in sorted(modules.iterdir())
                   if path.is_dir() and safe_path(root, path)
                   and re.fullmatch(r"[a-zA-Z0-9._+-]+", path.name)]
    if kernels and not shutil.which("depmod"):
        raise RuntimeError("depmod is required before removing module files")
    if any((root / "boot" / f"initrd.img-{kernel}").exists() for kernel in kernels):
        if not shutil.which("update-initramfs"):
            raise RuntimeError("update-initramfs is required before changing existing boot images")
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_parent = root / "var/backups/quantum-cleanup"
    if not safe_path(root, backup_parent):
        raise RuntimeError("Backup directory contains a symlink")
    backup_parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    backup = backup_parent / f"{stamp}-{uuid.uuid4().hex[:8]}"
    backup.mkdir(mode=0o700)
    (backup / "plan.json").write_text(json.dumps(plan, indent=2) + "\n")
    for path in sorted(paths):
        target = backup / "files" / path.relative_to(root)
        target.parent.mkdir(parents=True, exist_ok=True)
        if path.is_dir():
            shutil.copytree(path, target, symlinks=True, dirs_exist_ok=True)
        elif path.exists():
            shutil.copy2(path, target)
    print(f"Backup: {backup}", flush=True)
    if plan["package"]:
        command(["dpkg", "--purge", "quantum-dkms"])
    for version in plan["dkms_versions"]:
        # Purging the native package may already have removed its registration.
        if command(["dkms", "status", "-m", "quantum", "-v", version]).stdout.strip():
            command(["dkms", "remove", "-m", "quantum", "-v", version, "--all"])
    for name in plan["files"] + plan["sources"]:
        path = Path(name)
        if not path.exists():
            continue
        if not safe_path(root, path) or owners(path):
            raise RuntimeError(f"Path changed or is still package-owned; stopped: {path}")
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()
    for kernel in kernels:
        command(["depmod", "-a", kernel])
        if (root / "boot" / f"initrd.img-{kernel}").exists():
            command(["update-initramfs", "-u", "-k", kernel])
    remaining = discover(root)
    if remaining["package"] or remaining["dkms_versions"] or remaining["files"] or remaining["sources"]:
        raise RuntimeError("Recognized installation remains; inspect the backup plan and rerun preview")
    print("Known installation removed. Reboot when ready; loaded modules and audio sessions were not restarted.")
    return backup


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="back up and remove the previewed installation")
    parser.add_argument("--remove-apt-source", action="store_true", help="also remove the standard Quantum feed configuration")
    parser.add_argument("--user-home", type=Path, help="also inspect dedicated Quantum overrides in this user's home")
    arguments = parser.parse_args()
    if arguments.user_home is not None:
        if not arguments.user_home.is_absolute() or arguments.user_home == Path("/"):
            parser.error("--user-home must be an absolute home-directory path other than /")
    plan = discover(user_home=arguments.user_home, remove_apt=arguments.remove_apt_source)
    print(json.dumps(plan, indent=2), flush=True)
    if arguments.apply:
        apply(plan)
    else:
        print("Preview only. No files, packages, modules or audio services were changed.")
    if plan["review"]:
        print("Preserved items need manual review; this is not a claim that every custom change was removed.")


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, ValueError) as error:
        print(f"Cleanup stopped: {error}", file=sys.stderr)
        sys.exit(1)
