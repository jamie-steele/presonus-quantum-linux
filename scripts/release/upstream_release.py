#!/usr/bin/env python3
"""Discover complete Quantum RFCs and create source-only, auditable DKMS releases."""

import argparse
import datetime
import email.policy
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tarfile
import tempfile
import urllib.error
import urllib.parse
import urllib.request


ROOT = Path(__file__).resolve().parents[2]
PATCHWORK = "https://patchwork.kernel.org/api/1.2"
AUTHOR = "nicholas.johnson-opensource@outlook.com.au"
FIRST_SERIES = 1148921
FIRST_DATE = "2026-08-20"
MAX_RESPONSE = 16 * 1024 * 1024


def read_source_lock():
    values = {}
    for line in (ROOT / "driver/upstream.lock").read_text().splitlines():
        if line and not line.startswith("#"):
            key, value = line.split("=", 1)
            values[key] = value
    return values


def download(url, token=None):
    headers = {"User-Agent": "quantum-rfc-release/1.0"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=60) as response:
        payload = response.read(MAX_RESPONSE + 1)
    if len(payload) > MAX_RESPONSE:
        raise ValueError("Response exceeds the release input limit")
    return payload


def get_json(url, token=None):
    return json.loads(download(url, token))


def series_version(series):
    series_id = int(series["id"])
    version = int(series["version"])
    date = datetime.datetime.fromisoformat(series["date"]).strftime("%Y%m%d")
    if series_id < FIRST_SERIES or version < 1:
        raise ValueError("Series predates the original Quantum RFC")
    return f"{date}.rfc{version}.s{series_id}"


def validate_series(series):
    if series["project"]["link_name"] != "alsa-devel":
        raise ValueError("Series is not from the ALSA project")
    if series["submitter"]["email"].lower() != AUTHOR:
        raise ValueError("Series author is not Nicholas Johnson")
    if not re.search(r"\bquantum\b", series["name"], re.IGNORECASE):
        raise ValueError("Series is not a Quantum submission")
    patches = series["patches"]
    if not series["received_all"] or len(patches) != series["total"] or not patches:
        raise ValueError("RFC series is incomplete")
    if not any(re.search(r"\bRFC\b", patch["name"], re.IGNORECASE) for patch in patches):
        raise ValueError("Submission is not labeled RFC")
    for patch in patches:
        if not re.fullmatch(r"[A-Za-z0-9_.+@-]+", patch["msgid"].strip("<>")):
            raise ValueError("Unexpected message ID syntax")
    return series_version(series)


def discover(repository):
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
        raise ValueError("Expected owner/repository")
    candidates = {}
    page = 1
    while True:
        query = urllib.parse.urlencode({
            "project": "alsa-devel", "q": "quantum", "since": FIRST_DATE,
            "order": "date", "per_page": 100, "page": page,
        })
        try:
            patches = get_json(f"{PATCHWORK}/patches/?{query}")
        except urllib.error.HTTPError as error:
            if error.code == 404 and page > 1:
                break
            raise
        for patch in patches:
            if patch["submitter"]["email"].lower() != AUTHOR:
                continue
            if not re.search(r"\bRFC\b", patch["name"], re.IGNORECASE):
                continue
            for summary in patch["series"]:
                series_id = int(summary["id"])
                if series_id >= FIRST_SERIES:
                    candidates[series_id] = summary
        if len(patches) < 100:
            break
        page += 1

    # Process the oldest unpublished series first; outages never silently skip RFCs.
    for summary in sorted(candidates.values(), key=lambda item: (item["date"], item["id"])):
        series = get_json(f"{PATCHWORK}/series/{int(summary['id'])}/")
        if not series["received_all"]:
            continue
        version = validate_series(series)
        tag = f"rfc-{version}"
        release_url = f"https://api.github.com/repos/{repository}/releases/tags/{tag}"
        try:
            release = get_json(release_url, os.environ.get("GH_TOKEN"))
        except urllib.error.HTTPError as error:
            if error.code != 404:
                raise
        else:
            if not release["draft"]:
                continue
        return int(series["id"])
    return None


def source_hash(source):
    entries = []
    for path in sorted(source.rglob("*")):
        if path.is_symlink():
            raise ValueError("RFC source must not contain symlinks")
        if path.is_file():
            if path.suffix not in {".c", ".h"} and path.name not in {"Makefile", "Kconfig"}:
                raise ValueError(f"Unexpected upstream source file: {path.name}")
            relative = "sound/pci/quantum/" + path.relative_to(source).as_posix()
            entries.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {relative}\n")
    return hashlib.sha256("".join(entries).encode()).hexdigest()


def decode_patch(payload):
    if payload.startswith(b"diff --git "):
        return payload
    message = email.message_from_bytes(payload, policy=email.policy.default)
    parts = list(message.walk()) if message.is_multipart() else [message]
    for part in parts:
        if part.get_content_type() in {"text/plain", "text/x-patch", "text/x-diff"}:
            decoded = part.get_payload(decode=True)
            if decoded and b"diff --git " in decoded:
                return decoded
    raise ValueError("RFC did not contain a decodable patch")


def extract_series(series, output):
    source_root = output / "extracted"
    source_root.mkdir()
    records = []
    for patch in series["patches"]:
        message_id = patch["msgid"].strip("<>")
        url = f"https://patchwork.kernel.org/project/alsa-devel/patch/{message_id}/raw/"
        raw = download(url)
        decoded = decode_patch(raw)
        subprocess.run(
            ["git", "apply", "--include=sound/pci/quantum/*", "--"],
            cwd=source_root, input=decoded, check=True,
        )
        patch_name = f"{int(patch['id'])}.patch"
        (output / patch_name).write_bytes(raw)
        records.append({
            "message_id": message_id, "url": url, "file": patch_name,
            "sha256": hashlib.sha256(raw).hexdigest(),
            "decoded_sha256": hashlib.sha256(decoded).hexdigest(),
        })
    source = source_root / "sound/pci/quantum"
    if not (source / "quantum_main.c").is_file():
        raise ValueError("RFC must reconstruct the complete Quantum driver in an empty tree")
    tree_hash = source_hash(source)
    lock = read_source_lock()
    if int(series["id"]) == int(lock["UPSTREAM_SERIES_ID"]):
        if tree_hash != lock["UPSTREAM_SOURCE_TREE_SHA256"]:
            raise ValueError("Pinned RFC source differs from the repository lock")
        if records[0]["sha256"] != lock["UPSTREAM_PATCH_SHA256"]:
            raise ValueError("Pinned RFC patch differs from the repository lock")
    return source, records, tree_hash


def make_archive(directory, destination, timestamp):
    with destination.open("wb") as archive_file:
        with gzip.GzipFile(filename="", mode="wb", fileobj=archive_file, mtime=timestamp) as compressed:
            with tarfile.open(fileobj=compressed, mode="w") as archive:
                for path in [directory, *sorted(directory.rglob("*"))]:
                    name = directory.name + "/" + path.relative_to(directory).as_posix()
                    info = archive.gettarinfo(str(path), arcname=name)
                    info.uid = info.gid = 0
                    info.uname = info.gname = "root"
                    info.mtime = timestamp
                    info.mode = 0o755 if path.is_dir() else 0o644
                    data = io.BytesIO(path.read_bytes()) if path.is_file() else None
                    archive.addfile(info, data)


def prepare(series_id, output):
    series = get_json(f"{PATCHWORK}/series/{series_id}/")
    version = validate_series(series)
    output.mkdir(parents=True, exist_ok=False)
    with tempfile.TemporaryDirectory(prefix="quantum-rfc-") as temporary:
        work = Path(temporary)
        source, records, tree_hash = extract_series(series, work)
        package = work / f"quantum-{version}"
        module = package / "module"
        module.mkdir(parents=True)
        for source_file in sorted(source.iterdir()):
            if source_file.is_dir():
                raise ValueError("New source layout requires a packaging update")
            target_name = "Kbuild" if source_file.name == "Makefile" else source_file.name
            shutil.copyfile(source_file, module / target_name)
        kbuild = (module / "Kbuild").read_text()
        if "CONFIG_SND_QUANTUM" not in kbuild or "snd-quantum.o" not in kbuild:
            raise ValueError("RFC changed the module build contract")
        shutil.copyfile(ROOT / "packaging/Makefile", module / "Makefile")
        (module / "dkms.conf").write_text(
            'PACKAGE_NAME="quantum"\n'
            f'PACKAGE_VERSION="{version}"\n'
            'BUILT_MODULE_NAME[0]="snd-quantum"\n'
            'DEST_MODULE_LOCATION[0]="/updates/dkms"\n'
            'AUTOINSTALL="yes"\n'
            'MAKE[0]="make KDIR=/lib/modules/${kernelver}/build"\n'
            'CLEAN="make KDIR=/lib/modules/${kernelver}/build clean"\n'
        )
        (package / "VERSION").write_text(version + "\n")
        shutil.copytree(ROOT / "alsa/ucm2", package / "alsa/ucm2")
        (package / "alsa/wireplumber").mkdir(parents=True)
        for name in ("51-quantum2626.lua", "51-quantum2626.conf"):
            shutil.copyfile(ROOT / "alsa/wireplumber" / name, package / "alsa/wireplumber" / name)
        for original, target in (
            ("packaging/install.sh", "install.sh"),
            ("driver/scripts/host-tools.sh", "host-tools.sh"),
            ("driver/modprobe.d/quantum2626-upstream.conf", "quantum2626-backend.conf"),
            ("docs/RELEASES.md", "README.md"),
            ("LICENSE", "LICENSE.repository"),
            ("packaging/GPL-2.0.txt", "module/COPYING"),
        ):
            shutil.copyfile(ROOT / original, package / target)
        (package / "patches").mkdir()
        for record in records:
            shutil.copyfile(work / record["file"], package / "patches" / record["file"])
        manifest = {
            "version": version, "tag": f"rfc-{version}", "author": "Nicholas Johnson",
            "series_id": series_id, "series_url": f"https://patchwork.kernel.org/series/{series_id}/",
            "lore_url": "https://lore.kernel.org/all/" + records[0]["message_id"] + "/",
            "source_tree_sha256": tree_hash, "patches": records,
            "packaging_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
            "packaging_dirty": bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT)),
            "hardware_tested": False,
        }
        manifest_text = json.dumps(manifest, indent=2) + "\n"
        (package / "manifest.json").write_text(manifest_text)
        (output / "manifest.json").write_text(manifest_text)
        timestamp = int(datetime.datetime.fromisoformat(series["date"]).replace(
            tzinfo=datetime.timezone.utc).timestamp())
        archive = output / f"quantum-{version}.tar.gz"
        make_archive(package, archive, timestamp)
        (output / "SHA256SUMS").write_text(
            f"{hashlib.sha256(archive.read_bytes()).hexdigest()}  {archive.name}\n"
        )
        (output / "release-notes.md").write_text(
            f"Experimental Quantum RFC {version}\n\n"
            f"Driver by Nicholas Johnson: {manifest['lore_url']}\n\n"
            "Source-only DKMS bundle with ALSA UCM and WirePlumber 0.4/0.5 policy. "
            "See the included README for distro dependencies and installation. "
            "The CI evidence asset records the exact distro kernels used for compilation "
            "and staged installation. These checks do not validate physical audio, "
            "Thunderbolt, reboot binding, or Secure Boot enrollment.\n\n"
            "This is an unmerged RFC snapshot, not a mainline kernel release. "
            "Known DMA/rate-transition failures remain documented in the repository's "
            "notes/CURRENT_STATUS.md.\n\n"
            f"Source SHA-256: `{tree_hash}`\n"
        )
    print(json.dumps(manifest))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("pinned-series")
    discovery = commands.add_parser("discover")
    discovery.add_argument("--repository", required=True)
    preparation = commands.add_parser("prepare")
    preparation.add_argument("--series", type=int, required=True)
    preparation.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    if arguments.command == "pinned-series":
        print(int(read_source_lock()["UPSTREAM_SERIES_ID"]))
    elif arguments.command == "discover":
        candidate = discover(arguments.repository)
        print(candidate if candidate else "")
    else:
        prepare(arguments.series, arguments.output)


if __name__ == "__main__":
    main()
