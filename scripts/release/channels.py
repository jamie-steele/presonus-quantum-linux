#!/usr/bin/env python3
"""Release-channel identities shared by packaging and APT publication."""

import argparse
from pathlib import Path
import re


REVISION_PATTERN = r"[1-9][0-9]*(?:~staging\.[1-9][0-9]*)?"


def channel_for_revision(revision):
    if not re.fullmatch(REVISION_PATTERN, revision):
        raise ValueError("Expected a positive revision or N~staging.BUILD")
    return "staging" if "~staging." in revision else "master"


def revision_for_branch(branch, revision, build):
    if not re.fullmatch(r"[1-9][0-9]*", revision):
        raise ValueError("Base revision must be a positive integer")
    if branch == "master":
        return revision
    if branch in ("dev", "staging", "preview"):
        if not re.fullmatch(r"[1-9][0-9]*", build):
            raise ValueError("Staging build must be a positive integer")
        return f"{revision}~staging.{build}"
    raise ValueError("Only dev/staging/master or preview branches may build channels")


def pinned_tag(path):
    values = dict(line.split("=", 1) for line in path.read_text().splitlines()
                  if line and not line.startswith("#"))
    match = re.fullmatch(r"([0-9]{8})-rfc-v([1-9][0-9]*)", values["UPSTREAM_REVISION"])
    series = values["UPSTREAM_SERIES_ID"]
    if not match or not re.fullmatch(r"[1-9][0-9]*", series):
        raise ValueError("Invalid pinned source identity")
    return f"rfc-{match[1]}.rfc{match[2]}.s{series}"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    version = commands.add_parser("revision")
    version.add_argument("branch")
    version.add_argument("revision")
    version.add_argument("build")
    tag = commands.add_parser("pinned-tag")
    tag.add_argument("lock", type=Path)
    arguments = parser.parse_args()
    if arguments.command == "revision":
        print(revision_for_branch(arguments.branch, arguments.revision, arguments.build))
    else:
        print(pinned_tag(arguments.lock))
