#!/usr/bin/env python3
"""Select packaged Quantum policy without starting WirePlumber or opening audio."""

from pathlib import Path
import os
import re
import subprocess
import sys
import tempfile


POLICIES = {
    "0.4": ("main.lua.d", "51-quantum2626.lua"),
    "0.5": ("wireplumber.conf.d", "51-quantum2626.conf"),
}


def installed_series():
    result = subprocess.run(
        ["wireplumber", "--version"], capture_output=True, text=True, timeout=10,
    )
    if result.returncode:
        # Jammy's WirePlumber 0.4.8 predates --version.
        result = subprocess.run(
            ["dpkg-query", "-W", "-f=${Version}", "wireplumber"],
            capture_output=True, text=True, check=True, timeout=10,
        )
    match = re.search(r"(?:^|\s)(?:\d+:)?0\.(\d+)\.\d+", result.stdout)
    if not match or int(match.group(1)) < 4:
        raise ValueError("Cannot determine a supported WirePlumber version")
    return "0.4" if match.group(1) == "4" else "0.5"


def check_parents(path, root):
    for parent in path.parents:
        if parent.is_symlink():
            raise ValueError(f"Refusing symlink directory: {parent}")
        if parent == root:
            return
    raise ValueError(f"Policy path is outside the installation root: {path}")


def select_policy(root, series=None, remove=False):
    assets = root / "usr/share/quantum-dkms/wireplumber"
    if not remove and series not in POLICIES:
        raise ValueError(f"Unsupported WirePlumber series: {series}")

    changes = []
    for policy_series, (directory, name) in POLICIES.items():
        source = assets / name
        destination = root / "usr/share/wireplumber" / directory / name
        target = "/" + str(source.relative_to(root))
        check_parents(destination, root)

        owned_link = destination.is_symlink() and os.readlink(destination) == target
        if remove:
            if owned_link:
                changes.append((destination, None))
            continue

        check_parents(source, root)
        if source.is_symlink() or not source.is_file():
            raise ValueError(f"Missing regular packaged policy: {source}")
        if destination.is_symlink():
            if not owned_link:
                raise ValueError(f"Preserved unexpected policy symlink: {destination}")
        elif destination.exists():
            if not destination.is_file() or destination.read_bytes() != source.read_bytes():
                raise ValueError(f"Preserved customized policy; review before retrying: {destination}")

        if policy_series == series:
            if not owned_link:
                changes.append((destination, target))
        elif destination.exists() or destination.is_symlink():
            changes.append((destination, None))

    # Inspect both paths before changing either, so a custom inactive rule is
    # preserved without partially switching the policy.
    for destination, target in changes:
        if target is None:
            destination.unlink()
        else:
            destination.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.TemporaryDirectory(prefix=".quantum-", dir=destination.parent) as directory:
                temporary = Path(directory) / destination.name
                temporary.symlink_to(target)
                temporary.replace(destination)


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("configure", "remove"):
        raise ValueError("Usage: wireplumber_policy.py configure|remove")
    remove = sys.argv[1] == "remove"
    select_policy(Path("/"), None if remove else installed_series(), remove)


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(f"Quantum WirePlumber policy: {error}", file=sys.stderr)
        sys.exit(1)
