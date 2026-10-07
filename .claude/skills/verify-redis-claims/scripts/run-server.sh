#!/usr/bin/env bash
# Start / stop a throwaway redis-server from a build-tree.sh build.
#
#   run-server.sh start <build-dir> [--gdb FILE.gdb | --strace 'SPEC'] [-- redis-server args...]
#   run-server.sh stop  <run-dir>
#   run-server.sh stop-all <build-dir>
#
# start picks a free port, runs in a fresh run dir (dump.rdb, logs land there),
# waits until PING answers, then prints shell-sourceable lines:
#   PORT=...  RUNDIR=...  CLI="<redis-cli> -p PORT"
# --gdb   runs the server under `gdb -batch -x FILE`; gdb output -> $RUNDIR/gdb.out.
#         The gdb file must end with `run` (plus anything after); don't `quit` early.
# --strace runs it under `strace -f -tt -o $RUNDIR/strace.out -e SPEC`.
# Everything runs in its own process group so stop kills gdb/strace too.
set -euo pipefail

cmd=${1:?usage: run-server.sh start|stop|stop-all ...}; shift

stop_one() {
  local rd=$1
  [ -f "$rd/pgid" ] || return 0
  local pg; pg=$(cat "$rd/pgid")
  kill -TERM -- "-$pg" 2>/dev/null || true
  for _ in $(seq 20); do kill -0 -- "-$pg" 2>/dev/null || break; sleep 0.1; done
  kill -KILL -- "-$pg" 2>/dev/null || true
  rm -f "$rd/pgid"
  echo "stopped $rd" >&2
}

case $cmd in
stop) stop_one "${1:?run dir}"; exit 0 ;;
stop-all)
  for rd in "${1:?build dir}"/runs/*/; do stop_one "${rd%/}"; done; exit 0 ;;
start) ;;
*) echo "unknown command $cmd" >&2; exit 2 ;;
esac

BUILD=$(cd "${1:?build dir}" && pwd); shift
WRAP=(); MODE=plain
while [ $# -gt 0 ]; do
  case $1 in
    --gdb) MODE=gdb; GDBFILE=$(realpath "$2"); shift 2 ;;
    --strace) MODE=strace; SPEC=$2; shift 2 ;;
    --) shift; break ;;
    *) break ;;
  esac
done

PORT=$(python3 -c 'import socket; s=socket.socket(); s.bind(("127.0.0.1",0)); print(s.getsockname()[1])')
RUNDIR="$BUILD/runs/$PORT"; mkdir -p "$RUNDIR"
SRV="$BUILD/src/redis-server"; CLI="$BUILD/src/redis-cli"
ARGS=(--port "$PORT" --bind 127.0.0.1 --dir "$RUNDIR" --logfile "$RUNDIR/redis.log" --save "" --appendonly no "$@")

case $MODE in
  plain)  WRAP=() ;;
  gdb)    WRAP=(gdb -q -batch -x "$GDBFILE" --args) ;;
  strace) WRAP=(strace -f -tt -o "$RUNDIR/strace.out" -e "$SPEC") ;;
esac

# setsid => new process group whose id is the child's pid.
(cd "$RUNDIR" && exec setsid "${WRAP[@]}" "$SRV" "${ARGS[@]}" >"$RUNDIR/$MODE.out" 2>&1) &
echo $! > "$RUNDIR/pgid"

# gdb under -O0 can be slow to reach main; give it time.
for _ in $(seq 300); do
  if "$CLI" -p "$PORT" PING 2>/dev/null | grep -q PONG; then break; fi
  if ! kill -0 "$(cat "$RUNDIR/pgid")" 2>/dev/null; then
    echo "server exited early; see $RUNDIR/$MODE.out and $RUNDIR/redis.log" >&2
    tail -20 "$RUNDIR/$MODE.out" "$RUNDIR/redis.log" 2>/dev/null >&2; exit 1
  fi
  sleep 0.1
done
# A server stopped at a gdb breakpoint before accepting won't answer PING; that's fine.
"$CLI" -p "$PORT" PING >/dev/null 2>&1 || echo "note: server not answering PING yet (stopped in gdb? still loading?)" >&2

echo "PORT=$PORT"
echo "RUNDIR=$RUNDIR"
echo "CLI=\"$CLI -p $PORT\""
