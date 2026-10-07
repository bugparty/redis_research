# redis_research

A workspace for studying Redis internals. It pulls in several community-annotated
Redis source trees (comments mostly in Chinese) plus one illustrated notes repo
as git submodules, and keeps our own research in [`research/`](research/).

## Sources

| Directory | Redis version | Author | What is annotated | Upstream |
|---|---|---|---|---|
| [`annotated_redis_source/`](annotated_redis_source/) | 2.6 era (`version.h`: 2.9.7) | huangz (黄健宏) | Nearly every single-server module. **Not** annotated: Sentinel, replication, cluster, a few small helpers. | [huangzworks/annotated_redis_source](https://github.com/huangzworks/annotated_redis_source) |
| [`annotated-redis-2.8.2/`](annotated-redis-2.8.2/) | 2.8.2 | xkeyideal | Core data structures (adlist, dict, sds, ziplist, skiplist, intset), the string/list/hash/set/zset commands, event loop, AOF, networking. **Not** annotated: Sentinel, replication, RDB, helpers. | [xkeyideal/annotated-redis-2.8.2](https://github.com/xkeyideal/annotated-redis-2.8.2) |
| [`redis-3.0-annotated/`](redis-3.0-annotated/) | 3.0 pre-release (`version.h`: 2.9.11) | huangz (黄健宏) | Everything covered by the book *Redis 设计与实现* (*The Design and Implementation of Redis*). The best one to read alongside the book. | [huangz1990/redis-3.0-annotated](https://github.com/huangz1990/redis-3.0-annotated) |
| [`redis-internals/`](redis-internals/) | 5.0.5 | zpoint | **Not annotated source.** Illustrated articles in English and Chinese covering sds, hash, list (quicklist), set (intset), zset (skiplist), hyperloglog, streams (rax, listpack), geohash, persistence, pubsub, and cluster (reshard, gossip, failover). The replica article is unfinished. | [zpoint/redis-internals](https://github.com/zpoint/redis-internals) |
| [`redis7.0-chinese-annotated/`](redis7.0-chinese-annotated/) | 7.0.5 | CN-annotation-team | Community effort, still in progress. Per its README: 36 files done, 5 more than half done, 14 less than half done (including networking.c, rdb.c, replication.c, cluster.c, sentinel.c, listpack.c). | [CN-annotation-team/redis7.0-chinese-annotated](https://github.com/CN-annotation-team/redis7.0-chinese-annotated) |
| [`redis/`](redis/) | `unstable` (all release tags available) | Redis | **Official upstream, no Chinese annotations.** Full history with 395 version tags. Use it to read any version's original code, compare code without the annotation noise, and run `git log` / `git blame`. | [redis/redis](https://github.com/redis/redis) |

> **No annotated 5.0 source.** We couldn't find a Chinese-annotated Redis 5.x
> source tree, so 5.0 is covered by the `redis-internals` articles plus the
> upstream code. The articles are based on commit `388efbf`, three commits after
> the `5.0.5` tag on the 5.0 branch (`git describe`: `5.0.5-3-g388efbf8b`).
> Those three commits only touch module context flags, so reading tag `5.0.5`
> is close enough.

### Reading any version from upstream

Don't check out tags inside `redis/`, because that moves the submodule pointer.
Read files straight from the tag, or create a separate worktree:

```sh
git -C redis show 5.0.5:src/t_stream.c | less          # one file at one version
git -C redis diff 3.0.0 5.0.5 -- src/dict.c            # code change between releases
git -C redis worktree add /tmp/redis-5.0.5 5.0.5       # full tree, outside this repo
```

### Which one to read

- **Starting out:** `redis-3.0-annotated` together with the book. The comments are thorough and the code base is still small (88 `.c/.h` files in `src/`).
- **Modern Redis** (listpack, quicklist, rax/streams, threaded I/O, ACL, functions, modules): `redis7.0-chinese-annotated`. It has 158 files in `src/`, and coverage is uneven, so expect to read some files with only the upstream English comments.
- **Explanations in English with diagrams:** `redis-internals`. Read an article first, then look up the matching code in 3.0 or 7.0.
- **Code without the comments, or any other version** (3.2, 4.0, 6.x, 7.2, 8.x): upstream `redis/`.
- **The smallest cores:** `annotated_redis_source` (2.6) and `annotated-redis-2.8.2`. Use them as a second opinion when a comment in 3.0 is unclear.

A reading order that works for any version:

1. Data structures: `sds`, `adlist`, `dict`, `intset`, `ziplist` / `listpack`, `quicklist`, skiplist (in `t_zset.c`), `rax`
2. Object system: `object.c` and the `t_*.c` type implementations
3. Database layer: `db.c`, expiry, eviction
4. Event loop and networking: `ae*.c`, `anet.c`, `networking.c`
5. Server lifecycle: `redis.c` (renamed `server.c` in later versions)
6. Persistence: `rdb.c`, `aof.c`, `rio.c`
7. Distribution: `replication.c`, `sentinel.c`, `cluster.c`

## Getting the code

```sh
git clone --recurse-submodules <this-repo-url>

# already cloned without submodules
git submodule update --init

# pull the latest upstream commit of every submodule
git submodule update --remote
```

The submodules are pinned to specific commits. After `--remote`, commit the
updated pointers if you want to keep them.

## Building (optional)

Tested on Fedora 44 with GCC 16.2. Build in a scratch copy so the submodules
stay clean:

```sh
git -C redis-3.0-annotated archive --prefix=r30/ HEAD | tar -x -C /tmp
make -C /tmp/r30 -j8
```

| Version | Result |
|---|---|
| 2.6 | `make` works |
| 2.8.2 | `chmod +x src/mkreleasehdr.sh`, then `make MALLOC=libc`. The executable bits were lost in this repo, so the bundled jemalloc `configure` cannot run. |
| 3.0 | `make` works |
| 7.0.5 | `make MALLOC=libc`. The bundled jemalloc fails to compile with GCC 16. This build also logs a large `raxShow` dump on startup; see [research/version-comparison](research/version-comparison/README.md#known-deviations-from-upstream). |

## Reading tips

- 23 files under `annotated-redis-2.8.2/src/` (and its README) are **GBK**-encoded,
  not UTF-8. View them with `iconv -f GBK -t UTF-8 <file>` or set your editor's
  encoding to GBK.
- The annotated trees are supposed to change only comments and whitespace, but
  that is not guaranteed. Check `git log` in a submodule before trusting the
  code itself.

## Research

Our own work lives in [`research/`](research/README.md):

- [`research/version-comparison/`](research/version-comparison/README.md): how the same code and its comments changed across versions
- [`research/architecture/`](research/architecture/README.md): how Redis is put together

## Credits and licenses

The annotations and notes belong to their authors: huangz, xkeyideal,
zpoint and the CN-annotation-team contributors. Redis itself in these versions
(all before 7.4) is BSD-3-Clause; see `COPYING` in each tree. `redis-internals`
is licensed CC BY-NC-SA 4.0. Upstream `redis/` releases up to 7.2 are BSD-3-Clause.
7.4 is dual-licensed (RSALv2 / SSPLv1), and 8.0 onward is tri-licensed
(RSALv2 / SSPLv1 / AGPLv3); see `redis/LICENSE.txt`. Our content in `research/` is separate from
all of the above.
