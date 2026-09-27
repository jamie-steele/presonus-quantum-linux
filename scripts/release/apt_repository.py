#!/usr/bin/env python3
"""Build a signed experimental APT snapshot from native release packages."""

import argparse
import datetime
import gzip
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
from urllib.parse import urlparse


def run(arguments, **kwargs):
    return subprocess.check_output(arguments, **kwargs)


def download_packages(repository, destination):
    """Only complete, published native revisions are eligible for the feed."""
    pages = json.loads(run([
        "gh", "api", "--paginate", "--slurp", f"repos/{repository}/releases?per_page=100",
    ]))
    for release in (release for page in pages for release in page):
        tag = release["tag_name"]
        if release["draft"] or not re.fullmatch(r"rfc-[0-9]{8}\.rfc[0-9]+\.s[0-9]+", tag):
            continue
        names = {asset["name"] for asset in release["assets"]}
        for name in sorted(names):
            match = re.fullmatch(r"native-([1-9][0-9]*)-SHA256SUMS", name)
            if not match:
                continue
            revision = match[1]
            if f"native-{revision}-build-evidence.tar.gz" not in names:
                continue
            package_name = f"quantum-dkms_{tag[4:]}-{revision}_amd64.deb"
            if package_name not in names:
                raise ValueError(f"Incomplete native release: {tag}/{name}")
            download = destination / tag / revision
            download.mkdir(parents=True)
            subprocess.run([
                "gh", "release", "download", tag, "--repo", repository,
                "--pattern", name, "--pattern", package_name, "--dir", str(download),
            ], check=True)
            expected = None
            for line in (download / name).read_text().splitlines():
                digest, filename = line.split(maxsplit=1)
                if filename == package_name:
                    expected = digest
            package = download / package_name
            if hashlib.sha256(package.read_bytes()).hexdigest() != expected:
                raise ValueError(f"Package checksum mismatch: {tag}/{package_name}")


def build(packages, output, fingerprint, base_url):
    if not re.fullmatch(r"[A-Fa-f0-9]{40}", fingerprint):
        raise ValueError("Use the full 40-character signing-key fingerprint")
    url = urlparse(base_url)
    if url.scheme != "https" or not url.netloc or url.query or url.fragment:
        raise ValueError("APT base URL must be an HTTPS URL without query or fragment")
    output.mkdir(parents=True, exist_ok=False)
    pool = output / "pool/main/q/quantum-dkms"
    pool.mkdir(parents=True)
    candidates = sorted(packages.rglob("*.deb"))
    if not candidates:
        raise ValueError("No tested native packages available for the APT repository")
    for package in candidates:
        if not re.fullmatch(r"quantum-dkms_[0-9]{8}\.rfc[0-9]+\.s[0-9]+-[1-9][0-9]*_amd64.deb", package.name):
            raise ValueError(f"Unexpected package name: {package.name}")
        fields = run(["dpkg-deb", "-f", str(package), "Package", "Architecture"], text=True)
        if fields != "Package: quantum-dkms\nArchitecture: amd64\n":
            raise ValueError(f"Unexpected package metadata: {package.name}")
        target = pool / package.name
        if target.exists() and target.read_bytes() != package.read_bytes():
            raise ValueError(f"Conflicting package identity: {package.name}")
        shutil.copyfile(package, target)
    distribution = output / "dists/experimental"
    index = distribution / "main/binary-amd64"
    index.mkdir(parents=True)
    metadata = run(["apt-ftparchive", "packages", "pool"], cwd=output)
    (index / "Packages").write_bytes(metadata)
    (index / "Packages.gz").write_bytes(gzip.compress(metadata, mtime=0))
    # By-hash indices avoid metadata/index races during a Pages deployment.
    for path in (index / "Packages", index / "Packages.gz"):
        for algorithm in ("sha256", "sha512"):
            digest = hashlib.new(algorithm, path.read_bytes()).hexdigest()
            hashed = index / "by-hash" / algorithm.upper() / digest
            hashed.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, hashed)
    expiry = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=14)
    options = {
        "Origin": "PreSonus Quantum Linux",
        "Label": "Quantum experimental RFC drivers",
        "Suite": "experimental",
        "Codename": "experimental",
        "Architectures": "amd64",
        "Components": "main",
        "NotAutomatic": "yes",
        "ButAutomaticUpgrades": "yes",
        "Acquire-By-Hash": "yes",
    }
    command = ["apt-ftparchive"]
    for key, value in options.items():
        command.extend(["-o", f"APT::FTPArchive::Release::{key}={value}"])
    release = distribution / "Release"
    metadata = run(command + ["release", "dists/experimental"], cwd=output)
    # Older apt-ftparchive accepts unknown options but omits Valid-Until.
    expiry_field = "Valid-Until: " + expiry.strftime("%a, %d %b %Y %H:%M:%S +0000") + "\n"
    release.write_bytes(expiry_field.encode("ascii") + metadata)
    for mode, filename in (("--clearsign", "InRelease"), ("--detach-sign", "Release.gpg")):
        subprocess.run([
            "gpg", "--batch", "--yes", "--local-user", fingerprint, "--armor",
            "--output", str(distribution / filename), mode, str(release),
        ], check=True)
    public_key = run(["gpg", "--batch", "--export", fingerprint])
    if not public_key:
        raise ValueError("Signing public key was not exported")
    (output / "quantum-archive-keyring.gpg").write_bytes(public_key)
    (output / "SIGNING-KEY-FINGERPRINT").write_text(fingerprint.upper() + "\n")
    (output / "quantum.sources").write_text(
        f"Types: deb\nURIs: {base_url.rstrip('/')}\nSuites: experimental\n"
        "Components: main\nArchitectures: amd64\n"
        "Signed-By: /etc/apt/keyrings/quantum-archive-keyring.gpg\n"
    )
    (output / ".nojekyll").touch()
    (output / "index.html").write_text(
        "<!doctype html><html lang=\"en\"><meta charset=\"utf-8\">"
        "<title>Quantum experimental packages</title><h1>Quantum experimental packages</h1>"
        "<p>Unmerged RFC driver by Nicholas Johnson. Quantum 2626, amd64 only.</p>"
        '<p><a href="https://github.com/jamie-steele/presonus-quantum-linux/blob/master/docs/RELEASES.md">'
        "Installation, signing-key verification, and known limitations</a></p></html>\n"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    download = commands.add_parser("download")
    download.add_argument("repository")
    download.add_argument("destination", type=Path)
    generate = commands.add_parser("build")
    generate.add_argument("packages", type=Path)
    generate.add_argument("output", type=Path)
    generate.add_argument("--fingerprint", required=True)
    generate.add_argument("--base-url", required=True)
    arguments = parser.parse_args()
    if arguments.command == "download":
        download_packages(arguments.repository, arguments.destination)
    else:
        build(arguments.packages.resolve(), arguments.output.resolve(),
              arguments.fingerprint, arguments.base_url)
