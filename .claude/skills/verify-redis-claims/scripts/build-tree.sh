#!/usr/bin/env bash
# Build a debug (-O0 -g) redis-server from one of the repo's source trees,
# outside the submodule so the checkout stays clean.
#
#   build-tree.sh redis7.0-chinese-annotated        # the pinned 7.0.5 annotated tree
#   build-tree.sh redis                             # upstream at the pinned commit (unstable)
#   build-tree.sh redis 7.2.5                       # upstream at a release tag (fetched on demand)
#
# Prints the build directory on the last line of stdout; redis-server and
# redis-cli are in <dir>/src. A finished build is reused.
# Build root: $REDIS_BUILD_ROOT, else /tmp/redis-research-build.
set -euo pipefail

ROOT=$(git -C "$(dirname "$0")" rev-parse --show-toplevel)
TREE=${1:?usage: build-tree.sh <tree> [upstream-tag]}
REF=${2:-}
TREE=${TREE%/}
BUILD_ROOT=${REDIS_BUILD_ROOT:-/tmp/redis-research-build}

[ -d "$ROOT/$TREE/src" ] || { echo "no such source tree: $ROOT/$TREE (submodules initialised?)" >&2; exit 1; }

if [ -n "$REF" ]; then
  # Submodules are usually shallow with no tags; fetch just the one we need.
  if ! git -C "$ROOT/$TREE" rev-parse -q --verify "refs/tags/$REF" >/dev/null; then
    echo "fetching tag $REF ..." >&2
    git -C "$ROOT/$TREE" fetch -q --depth 1 origin tag "$REF" >&2
  fi
  COMMIT=$(git -C "$ROOT/$TREE" rev-parse "$REF^{commit}")
else
  COMMIT=$(git -C "$ROOT/$TREE" rev-parse HEAD)
fi

DIR="$BUILD_ROOT/$TREE-${REF:-${COMMIT:0:12}}"
if [ -x "$DIR/src/redis-server" ] && [ -f "$DIR/.built" ]; then
  echo "reusing $DIR" >&2
  echo "$DIR"; exit 0
fi

rm -rf "$DIR"; mkdir -p "$DIR"
git -C "$ROOT/$TREE" archive "$COMMIT" | tar -x -C "$DIR"
echo "$COMMIT" > "$DIR/.commit"

# MALLOC=libc: jemalloc's bundled build is the usual failure point (and races
# under -j). It doesn't matter for control-flow questions; build with jemalloc
# only when the claim is about memory/allocator behaviour.
# OPTIMIZATION=-O0: keeps locals and line numbers usable in gdb.
echo "building $TREE@${REF:-${COMMIT:0:12}} in $DIR (log: $DIR/build.log) ..." >&2
if ! make -C "$DIR" -j"$(nproc)" MALLOC=libc OPTIMIZATION=-O0 BUILD_TLS=no >"$DIR/build.log" 2>&1; then
  tail -30 "$DIR/build.log" >&2
  echo "build failed; full log: $DIR/build.log" >&2
  exit 1
fi
touch "$DIR/.built"
"$DIR/src/redis-server" --version 2>/dev/null | tail -1 >&2
echo "$DIR"
