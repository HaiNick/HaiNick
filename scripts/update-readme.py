#!/usr/bin/env python3
"""
Auto-regenerate the projects tree in README.md.

Fetches public repos on your account that carry the GitHub topic `shark-no`
and rewrites the block between the PROJECTS markers with a fresh tree.

Usage:
    python scripts/update-readme.py

Env:
    GH_TOKEN    optional, raises rate limit from 60/h to 1000/h

Add the `shark-no` topic to any repo you want listed. Remove it to hide.
"""

from __future__ import annotations

import json
import os
import re
import sys
import urllib.request
from urllib.error import HTTPError

USERNAME     = "HaiNick"
TOPIC        = "shark-no"
README_PATH  = "README.md"
START        = "<!-- PROJECTS:START -->"
END          = "<!-- PROJECTS:END -->"
MAX_REPOS    = 20
STRIP_PREFIX = "shark-no-"


def gh(path: str) -> dict:
    token = os.environ.get("GH_TOKEN")
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(f"https://api.github.com{path}", headers=headers)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def fetch_repos() -> list[dict]:
    q = f"user:{USERNAME}+topic:{TOPIC}+is:public+fork:false"
    data = gh(f"/search/repositories?q={q}&sort=updated&per_page={MAX_REPOS}")
    return data.get("items", [])


def format_tree(repos: list[dict]) -> str:
    if not repos:
        return "~/shark-no/\n└── (nothing tagged `shark-no` yet)"

    rows: list[tuple[str, str]] = []
    for r in repos:
        name = r["name"]
        short = name[len(STRIP_PREFIX):] if name.lower().startswith(STRIP_PREFIX) else name
        desc = (r.get("description") or "").strip()
        rows.append((short, desc))

    # sort alphabetically for stability
    rows.sort(key=lambda x: x[0].lower())

    width = max(len(n) for n, _ in rows)
    lines = ["~/shark-no/"]
    for i, (name, desc) in enumerate(rows):
        connector = "└──" if i == len(rows) - 1 else "├──"
        pad = " " * (width - len(name) + 2)
        lines.append(f"{connector} {name}{pad}{desc}".rstrip())
    lines.append("")
    lines.append("most private for now. public stuff pinned above.")
    return "\n".join(lines)


def rewrite(content: str, tree: str) -> str:
    pattern = re.compile(re.escape(START) + r".*?" + re.escape(END), flags=re.DOTALL)
    if not pattern.search(content):
        print(f"ERROR: markers {START} / {END} not found in {README_PATH}", file=sys.stderr)
        sys.exit(1)
    block = f"{START}\n```\n{tree}\n```\n{END}"
    return pattern.sub(block, content)


def main() -> None:
    try:
        repos = fetch_repos()
    except HTTPError as e:
        print(f"github api error: {e}", file=sys.stderr)
        sys.exit(1)

    with open(README_PATH) as f:
        before = f.read()

    after = rewrite(before, format_tree(repos))

    if after == before:
        print("no changes")
        return

    with open(README_PATH, "w") as f:
        f.write(after)
    print(f"updated with {len(repos)} repo(s)")


if __name__ == "__main__":
    main()
