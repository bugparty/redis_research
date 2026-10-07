---
name: verify-redis-claims
description: Check claims about Redis internals against the actual code and a running server — resolve code citations, read the source, build a debug redis-server, and gather runtime evidence with gdb, strace and raw RESP. Use this whenever you fact-check, review or proofread a note under research/, and whenever you write or extend a note and are about to state how Redis behaves (call order, which function handles what, limits, defaults, error replies, when data hits disk, what happens on the wire). Also use it when someone asks "is this right?", "does Redis really…", or wants a claim about Redis 7.0+ confirmed rather than recalled, even if they don't mention gdb or building.
---

# Verify Redis claims

Notes in `research/` explain Redis internals and cite code by line. Two things
go wrong with them: a citation drifts from what it claims, and a sentence that
reads right is only true under conditions it doesn't state (a config default, a
connection type, RESP2 vs RESP3, master vs normal client, 7.0 vs later). Reading
the code catches the first; the second is usually caught only by running the
server and watching it. This skill is the routine for both, so the work doesn't
get reinvented each time.

Scope: Redis 7.0 and newer. That means the annotated `redis7.0-chinese-annotated`
tree (7.0.5) and upstream `redis` (pinned unstable commit, or any release tag).
The 2.x/3.0 trees don't build cleanly with a modern GCC; for those, read source
only and say so.

Scripts are in `scripts/` next to this file (call it `$S` below). Run them from
the repo root. Set `REDIS_BUILD_ROOT` to your scratch directory if you have one;
otherwise builds go to `/tmp/redis-research-build`.

## 0. Preconditions

```bash
git submodule status            # a leading '-' means not checked out
git submodule update --init --depth 1   # only if needed
```

Submodules are shallow and carry no tags. Anything that needs history
(`git log -L`, `git show 7.2.0:...`) must fetch first:
`git -C redis fetch --depth 1 origin tag 7.2.0`. If a note's own instructions
assume tags, that's an environment gap, not a doc error — don't report it as one.

## 1. Pin down what the note claims

Read the note (and `research/README.md` for conventions). Work out which tree
and version it describes — the `<!-- code-base: ... -->` marker usually says.
Every finding is relative to that version; if later versions differ, that's
worth a note but it isn't an error.

List every citation alongside the code it points at:

```bash
$S/resolve-cites.py research/architecture/event-loop.md        # add -C 3 for context
python3 scripts/permalink.py --check                            # link formatting
```

`resolve-cites.py` only puts the code in front of you. For each cite, check the
line really is what the sentence says it is — the function *definition* versus
the *call* is the most common off-by-a-few slip (`ae.c:572` is `aeMain`'s
signature; the `while` is at 576).

## 2. Turn sentences into checkable claims

Go sentence by sentence and pull out each factual claim: an ordering, a
condition, a number, a default, a "only/always/never". The absolutes are where
errors hide — for each one, ask which config option, client type, connection
type or protocol version would make it false, and grep for it. Read the
surrounding code, not just the cited line; conditions usually live a few lines
above.

Decide per claim how to settle it:

| Claim kind | Best evidence |
|---|---|
| "X is defined / called at line N" | source (step 1) |
| call order, who calls whom, which path runs | gdb `dprintf` or breakpoint + `bt` |
| syscalls, ordering vs. disk/network (fsync before reply, accept flags, socket options) | strace |
| replies, error text, limits, protocol parsing, disconnects | `rawsend.py` / `redis-cli` against a live server |
| defaults | `CONFIG GET` on the live server **and** `config.c` |
| command semantics / complexity | `src/commands/*.json` and redis.io docs |

**Run the server only when source can't settle it.** Most claims are settled
by reading: a cite, a constant, an `if` whose condition is in plain sight, a
flag that is never set anywhere (`grep` proves a negative across the tree).
Building and tracing costs minutes per claim, so go dynamic only when:

- the answer depends on runtime state, timing or interleaving (which event
  fires first, whether a reply can overtake the AOF write);
- it depends on an effective default (config file, `dynamic-hz`, `ulimit`
  lowering `maxclients`) rather than a literal in the code;
- you are about to call a claim **wrong** and a short reproduction would make
  the verdict undeniable — one per wrong finding is enough.

Stop once the evidence settles the claim. One clean reproduction beats an
elaborate harness: if a counterexample needs SIGSTOP choreography or fault
injection to show, write it up as source-backed and say what a reproduction
would need, unless the user asked for it to be reproduced.

## 3. Build and run

```bash
B=$($S/build-tree.sh redis7.0-chinese-annotated | tail -1)   # 7.0.5 annotated
B=$($S/build-tree.sh redis | tail -1)                        # upstream, pinned commit
B=$($S/build-tree.sh redis 7.4.2 | tail -1)                  # upstream release tag
```

Builds are `-O0 -g`, `MALLOC=libc`, no TLS, outside the submodule, and reused.
libc malloc avoids the bundled jemalloc build (the usual failure); rebuild with
jemalloc by hand only if the claim is about allocator behaviour. No TLS means
TLS-path claims are source-only unless you build with `BUILD_TLS=yes`.

```bash
eval "$($S/run-server.sh start $B -- --appendonly yes --appendfsync always)"
$CLI SET k v                       # $PORT, $RUNDIR, $CLI are now set
$S/rawsend.py $PORT '*1\r\n$4\r\nPI' 'NG\r\n'
$S/run-server.sh stop $RUNDIR
```

- Defaults applied by `run-server.sh`: random free port, bind 127.0.0.1,
  `--save ""`, `--appendonly no`, dir/log in `$RUNDIR`. Override after `--`.
  Remember these when the claim is about defaults: test with the setting you
  mean, and say which one you used.
- `--gdb FILE` runs under `gdb -batch -x FILE` (output in `$RUNDIR/gdb.out`);
  `--strace 'trace=…'` writes `$RUNDIR/strace.out`. Recipes:
  `references/dynamic-recipes.md`.
- `run-server.sh` polls with `PING` until the server answers, so the first few
  `readQueryFromClient`/`processCommand PING` hits in a trace are the script,
  not your test.
- The 7.0 annotated tree prints ~80k lines of rax debug output to stdout at
  startup (an annotator's change). It goes to `$RUNDIR/plain.out`; read
  `redis.log` instead.
- Always stop what you start: `run-server.sh stop $RUNDIR`, or
  `run-server.sh stop-all $B` at the end. Leave servers you didn't start alone.
- Most claims need only one build. Build a second version only when the
  difference between versions is the point.

## 4. Report

Use the format in `references/report-format.md`: findings first, ranked by
severity, each with the note's file:line, the claim, what is actually true, and
evidence you can paste (source path:line, command + output). Then a short list
of what you checked and found correct — that tells the reader how far to trust
the rest of the note.

Separate what you observed from what you infer. If you couldn't verify
something (no TLS build, 5.0 source not available, network blocked), say so
rather than guessing.

## Writing a new note

The same steps apply in reverse: before writing a behavioral sentence, get the
evidence, and put the condition in the sentence ("with `appendfsync always`",
"in RESP2", "for non-master clients"). Cite the line that does the thing, not
the function signature. Per `research/README.md`, mark your own interpretation
as such.

Write citations as plain `` `file.c:123` `` and let `scripts/permalink.py` turn
them into links — don't hand-write GitHub URLs. Declare the tree once at the
top of the note:

```markdown
<!-- code-base: redis7.0-chinese-annotated/src -->   <!-- the pinned 7.0.5 tree -->
<!-- code-base: redis/src @ 7.4.2 -->                <!-- upstream at a release tag -->
```

With `@ <tag>` the links point at that tag's commit (fetched on demand) and
each line is checked against it, so build the same tag with `build-tree.sh
redis 7.4.2` and the line numbers you read in gdb match the ones you cite.
Then run `python3 scripts/permalink.py <note>` and `$S/resolve-cites.py <note>`
to confirm every cited line says what the sentence claims.

When editing an existing note to fix a finding, change only what the evidence
supports, keep the original structure, and re-run `resolve-cites.py` and
`permalink.py --check` afterwards.
