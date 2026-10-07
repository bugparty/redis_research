#!/usr/bin/env python3
"""List every code citation in research notes next to the source it points at.

    resolve-cites.py research/architecture/event-loop.md      # all cites in a note
    resolve-cites.py -C 3 research/commands.md                # with 3 lines of context
    resolve-cites.py 'redis7.0-chinese-annotated/src/ae.c:572' # one plain reference

Handles both forms the repo uses:
  * GitHub permalinks written by scripts/permalink.py
    ([`ae.c:572`](https://github.com/<owner>/<repo>/blob/<sha>/src/ae.c#L572))
  * plain `path:LINE` / `path:A-B` references, resolved against the note's
    <!-- code-base: ... --> marker.

Source is read with `git show <sha>:<path>` from the submodule, so it is
exactly the commit the link names. A link whose sha isn't the pinned commit
is flagged unless it is the ref the note declares (`code-base: redis/src @ 7.4.2`).
Output per cite:  note:LINE  label  ->  tree/path:A-B, then the code.
Reading the code is still your job: this only puts it in front of you.
"""
import argparse, re, signal, subprocess, sys
signal.signal(signal.SIGPIPE, signal.SIG_DFL)
from pathlib import Path

ROOT = Path(subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=Path(__file__).parent,
                           capture_output=True, text=True, check=True).stdout.strip())
LINK_RE = re.compile(r"\[`(?P<label>[^`]+)`\]\((?P<url>https://github\.com/(?P<repo>[^/]+/[^/]+)/blob/"
                     r"(?P<sha>[0-9a-f]{7,40})/(?P<path>[^#)]+)#L(?P<a>\d+)(?:-L(?P<b>\d+))?)\)")
PLAIN_RE = re.compile(r"(?<!\[)`(?P<path>[\w./-]+\.\w+):(?P<a>\d+)(?:-(?P<b>\d+))?`(?!\]\()")
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / "scripts"))
from permalink import BASE_RE, commit_for  # same marker syntax, same ref resolution


def git(*a, cwd=ROOT):
    return subprocess.run(["git", *a], cwd=cwd, capture_output=True, text=True)


def submodules():
    out = {}
    cfg = git("config", "-f", ".gitmodules", "--get-regexp", r"^submodule\..*\.path$").stdout
    for line in cfg.splitlines():
        key, path = line.split(" ", 1)
        name = key[len("submodule."):-len(".path")]
        url = git("config", "-f", ".gitmodules", f"submodule.{name}.url").stdout.strip()
        repo = re.sub(r"(\.git)?$", "", re.sub(r"^.*github\.com[:/]", "", url)).lower()
        pinned = git("ls-files", "-s", "--", path).stdout.split()[1]
        out[path] = (repo, pinned)
    return out


SUBS = submodules()
BY_REPO = {repo: (path, pinned) for path, (repo, pinned) in SUBS.items()}
# Renamed GitHub owners still redirect; map the old names too.
BY_REPO.setdefault("huangz1990/redis-3.0-annotated", BY_REPO.get("huangzworks/redis-3.0-annotated"))


def show(tree, sha, path, a, b, ctx):
    r = git("show", f"{sha}:{path}", cwd=ROOT / tree)
    if r.returncode:
        # Shallow submodules don't have other commits (e.g. a release tag's).
        return None, (r.stderr.strip().splitlines() or ["git show failed"])[-1] + \
            f"  (commit not local? try: git -C {tree} fetch --depth 1 origin {sha})"

    lines = r.stdout.splitlines()
    if b > len(lines):
        return None, f"line {b} past end of file ({len(lines)} lines)"
    lo, hi = max(1, a - ctx), min(len(lines), b + ctx)
    body = []
    for n in range(lo, hi + 1):
        mark = ">" if a <= n <= b else " "
        body.append(f"    {mark}{n:6} {lines[n-1]}")
    return "\n".join(body), None


def split_tree(full):
    for tree in sorted(SUBS, key=len, reverse=True):
        if full.startswith(tree + "/"):
            return tree, full[len(tree) + 1:]
    return None, full


def cites_in(note):
    text = note.read_text(encoding="utf-8")
    m = BASE_RE.search(text)
    base = m.group(1).rstrip("/") if m else None
    ref_tree, ref_sha = None, None
    if m and m.group(2):
        ref_tree = split_tree(base + "/x")[0]
        if ref_tree:
            ref_sha = commit_for(ref_tree, m.group(2))
    fence = False
    for no, line in enumerate(text.splitlines(), 1):
        if re.match(r"^\s*(```|~~~)", line):
            fence = not fence; continue
        if fence:
            continue
        for m in LINK_RE.finditer(line):
            hit = BY_REPO.get(m["repo"].lower())
            if not hit:
                yield no, m["label"], None, None, m["path"], 0, 0, f"unknown repo {m['repo']}"; continue
            tree, pinned = hit
            ok = pinned.startswith(m["sha"]) or (tree == ref_tree and ref_sha.startswith(m["sha"]))
            note_ = None if ok else f"sha {m['sha'][:12]} is neither the pinned {pinned[:12]} nor the note's declared ref"
            a = int(m["a"]); b = int(m["b"] or a)
            yield no, m["label"], tree, m["sha"], m["path"], a, b, note_
        for m in PLAIN_RE.finditer(line):
            full = m["path"] if "/" in m["path"] and split_tree(m["path"])[0] else (f"{base}/{m['path']}" if base else m["path"])
            tree, path = split_tree(full)
            a = int(m["a"]); b = int(m["b"] or a)
            if not tree:
                yield no, m[0], None, None, full, a, b, "plain ref with no resolvable tree (no code-base marker?)"; continue
            sha = ref_sha if tree == ref_tree else SUBS[tree][1]
            yield no, m[0], tree, sha, path, a, b, "plain ref (not yet a permalink)"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("targets", nargs="+")
    ap.add_argument("-C", type=int, default=0, help="context lines around the cited range")
    args = ap.parse_args()
    bad = 0
    for t in args.targets:
        p = Path(t)
        if p.suffix == ".md" and (p.exists() or (ROOT / p).exists()):
            note = p if p.exists() else ROOT / p
            items = list(cites_in(note))
            try:
                src = str(note.resolve().relative_to(ROOT))
            except ValueError:  # a draft outside the repo
                src = str(note)
        else:
            m = re.fullmatch(r"([\w./-]+):(\d+)(?:-(\d+))?", t)
            if not m:
                print(f"can't parse {t}", file=sys.stderr); bad += 1; continue
            tree, path = split_tree(m[1])
            a = int(m[2]); b = int(m[3] or a)
            items = [(0, t, tree, SUBS[tree][1] if tree else None, path, a, b, None if tree else "unknown tree")]
            src = "arg"
        for no, label, tree, sha, path, a, b, note_ in items:
            loc = f"{tree}/{path}:{a}" + (f"-{b}" if b != a else "") if tree else path
            print(f"{src}:{no}  {label}  ->  {loc}" + (f"   [!] {note_}" if note_ else ""))
            if tree and sha:
                body, err = show(tree, sha, path, a, b, args.C)
                if err:
                    print(f"    [!] {err}"); bad += 1
                else:
                    print(body)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
