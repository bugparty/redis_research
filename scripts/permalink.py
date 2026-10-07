#!/usr/bin/env python3
"""Turn `file.c:123` code references in Markdown notes into GitHub permalinks.

A reference is an inline-code span of the form `path:LINE` or `path:START-END`:

    `server.c:6836`                                  -> resolved against the note's code base
    `redis7.0-chinese-annotated/src/acl.c:1441-1443` -> fully qualified, works anywhere

Bare paths are resolved against a base directory declared once per note:

    <!-- code-base: redis7.0-chinese-annotated/src -->

Each link points at the commit the superproject has pinned for that submodule,
so it keeps matching the local checkout. Every line is checked against the file
at that commit before a link is written.

Fenced code blocks (Mermaid included) are left alone: links don't render there.
References that are already links are skipped, so running this again is a no-op.
To quote a reference literally, use a double-backtick span: `` server.c:1 ``.

Usage:
    scripts/permalink.py              # rewrite every .md under research/
    scripts/permalink.py FILE...      # rewrite only these files
    scripts/permalink.py --check      # report only, exit 1 if anything would change
"""

import argparse
import re
import subprocess
import sys
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Only a marker on a line of its own counts, not one quoted in prose.
BASE_RE = re.compile(r"^\s*<!--\s*code-base:\s*(\S+?)\s*-->\s*$", re.M)
FENCE_RE = re.compile(r"^\s*(```|~~~)")
# `path:12` or `path:12-34`, not already the text of a link ("[`...`](").
REF_RE = re.compile(r"(?<!\[)`(?P<path>[\w./-]+\.\w+):(?P<start>\d+)(?:-(?P<end>\d+))?`(?!\]\()")


def git(*args, cwd=ROOT):
    return subprocess.run(["git", *args], cwd=cwd, check=True,
                          capture_output=True, text=True).stdout


@lru_cache(maxsize=None)
def submodules():
    """Map submodule path -> (https repo url, pinned commit)."""
    out = {}
    cfg = git("config", "-f", ".gitmodules", "--get-regexp", r"^submodule\..*\.path$")
    for line in cfg.splitlines():
        key, path = line.split(" ", 1)
        name = key[len("submodule."):-len(".path")]
        url = git("config", "-f", ".gitmodules", f"submodule.{name}.url").strip()
        url = re.sub(r"\.git$", "", url)
        url = re.sub(r"^git@github\.com:", "https://github.com/", url)
        # The commit recorded in the superproject's index, not whatever is checked out.
        entry = git("ls-files", "-s", "--", path).split()
        if not entry or entry[0] != "160000":
            continue
        out[path] = (url, entry[1])
    return out


@lru_cache(maxsize=None)
def line_count(sub, sha, path):
    try:
        blob = git("show", f"{sha}:{path}", cwd=ROOT / sub)
    except subprocess.CalledProcessError:
        return None
    return blob.count("\n") + (0 if blob.endswith("\n") else 1)


def resolve(ref_path, base):
    """Return (submodule, path inside it) or None."""
    full = ref_path if base is None else f"{base}/{ref_path}"
    for candidate in (ref_path, full):
        for sub in submodules():
            if candidate.startswith(sub + "/"):
                return sub, candidate[len(sub) + 1:]
    return None


def convert(text, note):
    m = BASE_RE.search(text)
    base = m.group(1).rstrip("/") if m else None
    problems, changed, in_fence, out = [], 0, False, []

    for lineno, line in enumerate(text.splitlines(keepends=True), 1):
        if FENCE_RE.match(line):
            in_fence = not in_fence
        if in_fence or FENCE_RE.match(line):
            out.append(line)
            continue

        def repl(m):
            nonlocal changed
            where = f"{note}:{lineno}: `{m.group(0)[1:-1]}`"
            hit = resolve(m.group("path"), base)
            if hit is None:
                problems.append(f"{where}: not under a submodule (missing code-base marker?)")
                return m.group(0)
            sub, path = hit
            url, sha = submodules()[sub]
            n = line_count(sub, sha, path)
            start, end = int(m.group("start")), int(m.group("end") or m.group("start"))
            if n is None:
                problems.append(f"{where}: {path} does not exist in {sub}@{sha[:7]}")
                return m.group(0)
            if not 1 <= start <= end <= n:
                problems.append(f"{where}: lines out of range ({path} has {n} lines)")
                return m.group(0)
            anchor = f"#L{start}" + (f"-L{end}" if end != start else "")
            changed += 1
            return f"[{m.group(0)}]({url}/blob/{sha}/{path}{anchor})"

        out.append(REF_RE.sub(repl, line))
    return "".join(out), changed, problems


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("files", nargs="*", type=Path)
    ap.add_argument("--check", action="store_true", help="don't write; exit 1 if anything would change")
    args = ap.parse_args()

    files = args.files or sorted((ROOT / "research").rglob("*.md"))
    total, all_problems = 0, []
    for f in files:
        f = f.resolve()
        note = f.relative_to(ROOT)
        old = f.read_text(encoding="utf-8")
        new, changed, problems = convert(old, note)
        all_problems += problems
        if changed:
            total += changed
            print(f"{note}: {changed} reference(s) {'to convert' if args.check else 'converted'}")
            if not args.check:
                f.write_text(new, encoding="utf-8")

    for p in all_problems:
        print(f"warning: {p}", file=sys.stderr)
    if args.check and (total or all_problems):
        sys.exit(1)


if __name__ == "__main__":
    main()
