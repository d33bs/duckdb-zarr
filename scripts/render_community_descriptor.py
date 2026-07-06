#!/usr/bin/env python3
"""Render description.yml for duckdb/community-extensions submission."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def first_match(pattern: str, text: str, label: str) -> str:
    match = re.search(pattern, text, re.MULTILINE)
    if match is None:
        raise ValueError(f"could not find {label}")
    return match.group(1)


def project_versions() -> dict[str, str]:
    return {
        "Cargo.toml": first_match(
            r'^version\s*=\s*"([^"]+)"',
            read("Cargo.toml"),
            "Cargo.toml package version",
        ),
        "pyproject.toml": first_match(
            r'^version\s*=\s*"([^"]+)"',
            read("pyproject.toml"),
            "pyproject.toml project version",
        ),
        "description.yml": first_match(
            r"^\s*version:\s*([^\s]+)\s*$",
            read("description.yml"),
            "description.yml extension version",
        ),
    }


def validate_ref(ref: str, version: str) -> None:
    if re.fullmatch(r"[0-9a-f]{40}", ref):
        return
    if re.fullmatch(r"v\d+\.\d+\.\d+", ref) and ref == f"v{version}":
        return
    raise ValueError(
        f"release ref must be a 40-character commit hash or v{version}; got {ref!r}"
    )


def render(ref: str, version: str) -> str:
    text = read("description.yml")

    text = re.sub(
        r"^(\s*version:\s*)[^\s]+(\s*)$",
        rf"\g<1>{version}\2",
        text,
        count=1,
        flags=re.MULTILINE,
    )
    text = re.sub(
        r"^(\s*)# Update ref to the tagged release commit before submitting the PR to duckdb/community-extensions\.\n",
        "",
        text,
        count=1,
        flags=re.MULTILINE,
    )
    text = re.sub(
        r"^(\s*ref:\s*)[^\s#]+.*$",
        rf"\g<1>{ref}",
        text,
        count=1,
        flags=re.MULTILINE,
    )
    return text


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ref", required=True, help="release tag or commit hash")
    parser.add_argument(
        "--out",
        required=True,
        help="output descriptor path, relative to the repository root",
    )
    args = parser.parse_args()

    versions = project_versions()
    unique_versions = set(versions.values())
    if len(unique_versions) != 1:
        details = ", ".join(f"{path}={version}" for path, version in versions.items())
        raise SystemExit(f"project versions differ: {details}")

    version = unique_versions.pop()
    try:
        validate_ref(args.ref, version)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    out = ROOT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render(args.ref, version), encoding="utf-8")
    print(f"wrote {out.relative_to(ROOT)} for zarr {version} at {args.ref}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
