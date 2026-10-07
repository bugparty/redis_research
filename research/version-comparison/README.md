# Version comparison

Compare the same subsystem across the annotated trees: what the code does in
each version, and how each annotator explains it.

## Trees

| Short name | Path | Version | Comment encoding |
|---|---|---|---|
| 2.6 | `annotated_redis_source/` | 2.6 era (`version.h`: 2.9.7) | UTF-8 |
| 2.8 | `annotated-redis-2.8.2/` | 2.8.2 | **GBK** (23 of 84 `src/` files) |
| 3.0 | `redis-3.0-annotated/` | 3.0 pre-release (`version.h`: 2.9.11) | UTF-8 |
| 5.0 | `redis-internals/` | 5.0.5. Articles only, no source; based on `388efbf` = `5.0.5-3-g388efbf8b` | UTF-8 |
| 7.0 | `redis7.0-chinese-annotated/` | 7.0.5 | UTF-8 |
| upstream | `redis/` | Every release tag (`2.6.0` … `8.10.2`); English comments only | UTF-8 |

## How to diff across trees

The trees are separate repositories with unrelated histories, so use plain
`diff` instead of `git diff`:

```sh
# same file, two versions
diff -u redis-3.0-annotated/src/dict.c redis7.0-chinese-annotated/src/dict.c

# 2.8.2 files must be converted to UTF-8 first
diff -u <(iconv -f GBK -t UTF-8 annotated-redis-2.8.2/src/dict.c) \
        redis-3.0-annotated/src/dict.c
```

To compare **code only**, without the annotations, use the upstream submodule.
Its tags give exact release code, and it also covers versions that have no
annotated tree:

```sh
# code change between two releases
git -C redis diff 3.0.0 7.0.5 -- src/dict.c

# what an annotator changed beyond comments (7.0.5 example)
diff -u <(git -C redis show 7.0.5:src/acl.c) redis7.0-chinese-annotated/src/acl.c

# when and why a line changed
git -C redis log -L '/^int dictRehash/,+40:src/dict.c' 3.0.0..7.0.5
```

Tag names to use: `2.6.0`, `2.8.2`, `3.0.0`, `5.0.5`, `7.0.5`. The 2.6 and 3.0
annotated trees were cut from `unstable` (2.9.7 and 2.9.11), not from a
release, so they won't match any tag exactly.

## Source file presence

Notable files under `src/` (Y = present). It shows where a subsystem lives
in each version. The 5.0.5 column comes from upstream `git ls-tree 5.0.5`.
"Upstream first" is the first major release (x.y.0) that contains the file.

| File | 2.6 | 2.8 | 3.0 | 5.0.5 | 7.0 | Upstream first | Note |
|---|:-:|:-:|:-:|:-:|:-:|---|---|
| `redis.c` / `redis.h` | Y | Y | Y | - | - | 2.6.0 | Renamed `server.c` / `server.h` in 3.2.0 |
| `scripting.c` | Y | Y | Y | Y | - | 2.6.0 | Last in 6.2; 7.0 splits it into `eval.c`, `script.c`, `script_lua.c`, `function_lua.c`, `functions.c` |
| `redis-check-dump.c` | Y | Y | Y | - | - | 2.6.0 | Replaced by `redis-check-rdb.c` in 3.2.0 |
| `ziplist.c` | Y | Y | Y | Y | Y | | Still in 7.0 (needed to load old RDB files); listpack is the in-memory encoding |
| `zipmap.c` | Y | Y | Y | Y | Y | | |
| `migrate.c` | - | Y | - | - | - | 2.6.0 | In the 2.6.0 and 2.8.0 releases, but not in the 2.6 annotated tree (cut from `unstable`) |
| `notify.c` | - | Y | Y | Y | Y | 2.8.0 | |
| `cluster.c` | Y | - | Y | Y | Y | 3.0.0 | Already present in the 2.6 annotated tree because `unstable` had early cluster code |
| `blocked.c`, `hyperloglog.c` | - | - | Y | Y | Y | 3.0.0 | |
| `latency.c` | - | - | - | Y | Y | 3.0.0 | In the 3.0.0 release, but not in the 3.0 annotated tree (2.9.11) |
| `quicklist.c`, `geo.c` | - | - | - | Y | Y | 3.2.0 | |
| `rax.c`, `module.c`, `expire.c`, `evict.c`, `lazyfree.c`, `defrag.c` | - | - | - | Y | Y | 4.0.0 | |
| `listpack.c`, `t_stream.c` | - | - | - | Y | Y | 5.0.0 | |
| `acl.c`, `connection.c`, `tls.c`, `tracking.c` | - | - | - | - | Y | 6.0.0 | |

Count of `.c/.h` files in `src/`: 2.6 = 82, 2.8 = 84, 3.0 = 88, 5.0.5 = 122, 7.0 = 158.

## Known deviations from upstream

The annotated trees are supposed to change only comments and whitespace.
Exceptions we have found:

- **7.0, `src/acl.c:1441-1443`**: `ACLGetCommandID()` calls
  `serverLogRaw(...)` and `raxShow(commandId)` every time it inserts a
  command. These calls came in with commit `1e196cef` ("rax 源码注释 (#113)",
  i.e. "rax source comments"), apparently left over from debugging. The effect
  is that even `redis-server --version` prints about 82k lines. Ignore these
  lines when reading the code, and remove them from your build copy.
- **2.8, file modes**: every file is mode `100644`, including
  `src/mkreleasehdr.sh` and `deps/jemalloc/configure`, so a plain `make` fails.

## Topic ideas

- [ ] `dict`: rehashing, incremental rehash, and the `dictScan` reverse-binary cursor (2.8 onward)
- [ ] List encodings: ziplist + linkedlist (2.6/3.0), then quicklist of ziplists (5.0), then quicklist of listpacks (7.0)
- [ ] `sds` header layout: one `sdshdr` (≤3.0), then `sdshdr5/8/16/32/64` (later)
- [ ] Expiry: active vs. lazy expiry, and how `expire.c` was split out of `redis.c`
- [ ] Persistence: AOF rewrite (3.0), multi-part AOF (7.0), RDB format changes
- [ ] Scripting: `scripting.c` (Lua EVAL) vs. Redis 7 functions
- [ ] Annotation quality: the same function as explained by huangz (2.6/3.0), xkeyideal (2.8) and CN-annotation-team (7.0)
