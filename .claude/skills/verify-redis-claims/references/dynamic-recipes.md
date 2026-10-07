# Dynamic recipes

Copy-paste starting points. All assume `$S`, `$B` from SKILL.md and a server
started with `run-server.sh`.

## gdb

gdb files end with `run`. With `-batch`, gdb exits when the server does, so
stop the server with `run-server.sh stop` (or `$CLI SHUTDOWN NOSAVE`) and then
read `$RUNDIR/gdb.out`.

**Call order across one event-loop iteration** — `dprintf` prints and continues,
so the server keeps running at near-normal speed:

```gdb
set pagination off
set breakpoint pending on
dprintf aeProcessEvents,"aeProcessEvents\n"
dprintf beforeSleep,"beforeSleep\n"
dprintf aeApiPoll,"aeApiPoll\n"
dprintf afterSleep,"afterSleep\n"
dprintf processTimeEvents,"processTimeEvents\n"
dprintf serverCron,"serverCron\n"
run
```

**Who calls X** — breakpoint with a short backtrace, then continue:

```gdb
set pagination off
set breakpoint pending on
break ACLUpdateDefaultUserPassword
commands
  silent
  bt 6
  cont
end
run
```

If the function is never hit, the claim that it runs on this path is wrong —
that's evidence too; say "breakpoint never hit during <scenario>".

**Print locals at a line** (build is -O0, so locals are available):

```gdb
break networking.c:2837
commands
  silent
  printf "nread=%d readlen=%lu qblen=%lu\n", nread, readlen, sdslen(c->querybuf)
  cont
end
run
```

Use line numbers from the tree you built — they differ between 7.0.5 and
upstream. Check with `resolve-cites.py <tree>/src/file.c:N` first.

**Startup order** — break on each stage and print `bt 2`; the server will be
slow to answer the first PING, which `run-server.sh` waits for (30 s max).

**Conditional / counted stops:** `break processTimeEvents if ++$n == 3` with
`set $n = 0` before it.

## strace

```bash
eval "$($S/run-server.sh start $B --strace 'trace=read,write,fdatasync,fsync' -- --appendonly yes --appendfsync always)"
$CLI SET k v; $S/run-server.sh stop $RUNDIR
grep -nE 'read\(|write\(|fdatasync' $RUNDIR/strace.out | tail -20
```

Useful sets:

| Question | `-e` spec |
|---|---|
| reply vs. AOF write/fsync ordering | `trace=read,write,fdatasync,fsync` |
| listen/accept, socket flags | `trace=socket,bind,listen,accept4,setsockopt,epoll_ctl` |
| idle wakeups / poll timeout | `trace=epoll_wait` |
| fork for BGSAVE / rewrite | `trace=clone,clone3,fork,wait4` (`-f` is already on) |

Each line has a timestamp (`-tt`) and a pid; with io-threads or bio threads,
check which thread made the call.

## Raw protocol

`redis-cli` hides framing; use `rawsend.py` when the claim is about parsing,
partial reads, limits or disconnects.

```bash
$S/rawsend.py $PORT 'PING\r\n'                                 # inline
$S/rawsend.py $PORT '*2\r\n$3\r\nGET\r\n$1\r\nk\r\n'           # multibulk
$S/rawsend.py $PORT '*3\r\n$3\r\nSET\r\n$1\r\nk\r\n$3\r\nb' 'ar\r\n'   # split across two sends
$S/rawsend.py $PORT --repeat A 70000                           # oversized inline, no newline
$S/rawsend.py $PORT '*1\r\n$600000000\r\n'                     # bulk length over proto-max-bulk-len
```

The trailing `<open>` / `<EOF>` / `<RST>` tells you whether the server kept the
connection, closed it after replying, or reset it.

**Holding connections open** (maxclients, blocking commands) — keep a socket in
the background:

```bash
(exec 3<>/dev/tcp/127.0.0.1/$PORT; sleep 2) &
$S/rawsend.py $PORT 'PING\r\n'      # with --maxclients 1: -ERR max number of clients reached
wait
```

**RESP3:** `$S/rawsend.py $PORT --max 2000 'HELLO 3\r\n' 'SUBSCRIBE ch\r\n' 'GET k\r\n'` (the HELLO map is long; raise `--max`).

## Live-server checks that are often enough

```bash
$CLI CONFIG GET hz dynamic-hz maxclients client-query-buffer-limit proto-max-bulk-len
$CLI INFO stats | grep -E 'rejected|total_connections'
$CLI CONFIG SET key-load-delay 100                         # slow down loading to observe -LOADING
$CLI COMMAND DOCS <cmd>                                     # 7.0+: complexity, since, arguments
```

`DEBUG` is off by default from 7.0 on (`enable-debug-command no`, immutable at
runtime); start with `-- --enable-debug-command yes` if you need `DEBUG SLEEP`,
`DEBUG RELOAD`, `DEBUG OBJECT` etc.
