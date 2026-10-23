#!/usr/bin/env python3
"""Migrate known manual/tar installs after the replacement DKMS build succeeds."""

import hashlib
import json
from pathlib import Path
import re
import shutil
import sys
import tempfile

import cleanup_state


ROOT = Path("/")
ASSETS = Path(__file__).resolve().parent


def older_release(candidate, target):
    if not cleanup_state.VERSION.fullmatch(candidate) or not cleanup_state.VERSION.fullmatch(target):
        return False
    return cleanup_state.command(
        ["dpkg", "--compare-versions", candidate, "lt", target], allowed=(0, 1)).returncode == 0


def module_files(plan):
    return [Path(name) for name in plan["files"]
            if cleanup_state.MODULE.fullmatch(Path(name).name)]


def migrate(target, root=ROOT, assets=ASSETS):
    if not re.fullmatch(r"[0-9]{8}\.rfc[0-9]+\.s[0-9]+-[1-9][0-9]*", target):
        raise ValueError("Invalid target native version")
    plan = cleanup_state.discover(root)
    versions = [version for version in plan["dkms_versions"] if older_release(version, target)]
    sources = [Path(name) for name in plan["sources"]
               if older_release(Path(name).name.removeprefix("quantum-"), target)
               and not cleanup_state.owners(Path(name))]
    policy = root / "etc/modprobe.d/quantum2626-backend.conf"
    known = json.loads((assets / "migration-identities.json").read_text())
    policy_owners = cleanup_state.owners(policy) if policy.exists() else []
    replace_policy = (all(owner in ("quantum-dkms", "quantum-dkms:amd64") for owner in policy_owners)
                      and cleanup_state.safe_path(root, policy) and policy.is_file()
                      and hashlib.sha256(policy.read_bytes()).hexdigest() == known["inhouse_policy_sha256"])
    files = module_files(plan)
    if not versions and not sources and not files and not replace_policy:
        report_review(plan, root)
        return None
    parent = root / "var/backups/quantum-migration"
    if not cleanup_state.safe_path(root, parent):
        raise RuntimeError("Migration backup path contains a symlink")
    parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    backup = Path(tempfile.mkdtemp(prefix="configure.", dir=parent))
    (backup / "plan.json").write_text(json.dumps({
        "target": target, "dkms_versions": versions, "sources": [str(path) for path in sources],
        "modules": [str(path) for path in files], "replace_generated_policy": replace_policy,
    }, indent=2) + "\n")

    def save(path):
        if not cleanup_state.safe_path(root, path):
            raise RuntimeError(f"Migration path contains a symlink: {path}")
        destination = backup / "files" / path.relative_to(root)
        if destination.exists():
            return
        destination.parent.mkdir(parents=True, exist_ok=True)
        if path.is_dir():
            shutil.copytree(path, destination, symlinks=True)
        else:
            shutil.copy2(path, destination)

    for path in files + sources + ([policy] if replace_policy else []):
        save(path)
    print(f"Quantum migration backup: {backup}", flush=True)
    for version in versions:
        cleanup_state.command(["dkms", "remove", "-m", "quantum", "-v", version, "--all"])
    # DKMS removal can restore an original manual module. Inspect and back it up
    # before removing it too; the newly built target is installed after migration.
    for path in module_files(cleanup_state.discover(root)) + sources:
        if not path.exists():
            continue
        if not cleanup_state.safe_path(root, path) or cleanup_state.owners(path):
            raise RuntimeError(f"Migration path changed or became package-owned: {path}")
        save(path)
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()
    if replace_policy:
        if hashlib.sha256(policy.read_bytes()).hexdigest() != known["inhouse_policy_sha256"]:
            raise RuntimeError("Backend policy changed during migration")
        shutil.copyfile(assets / "backend-upstream.conf", policy)
    report_review(cleanup_state.discover(root), root)
    print("Known legacy installations retired; installing the new DKMS module next.", flush=True)
    return backup


def report_review(plan, root):
    for item in plan["review"]:
        print(f"Quantum migration: {item}", file=sys.stderr)
    policy = root / "etc/modprobe.d/quantum2626-backend.conf"
    if cleanup_state.safe_path(root, policy) and policy.is_file():
        if re.search(r"^\s*blacklist\s+snd[-_]quantum\s*(?:#.*)?$", policy.read_text(), re.MULTILINE):
            print("Quantum migration: preserved customized backend policy blacklists snd-quantum; "
                  "review it before reboot.", file=sys.stderr)


if __name__ == "__main__":
    try:
        migrate(sys.argv[1])
    except (OSError, RuntimeError, ValueError) as error:
        print(f"Quantum migration stopped: {error}", file=sys.stderr)
        sys.exit(1)
