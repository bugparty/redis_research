#!/usr/bin/env python3
r"""Send raw bytes to a Redis port and show exactly what comes back.

    rawsend.py PORT 'PING\r\n'
    rawsend.py PORT '*3\r\n$3\r\nSET\r\n$1\r\nk\r\n$1\r\nv\r\n'
    rawsend.py PORT '*1\r\n$4\r\nPI' 'NG\r\n'          # each arg is a separate send()
    rawsend.py PORT --repeat 'x' 70000 --then '\r\n'    # big payloads without a huge argv
    rawsend.py PORT --wait 2 'BLPOP q 1\r\n'

Escapes (\r \n \xNN) in args are decoded. Prints the reply bytes (repr) and how
the connection ended: <open> (still connected after --wait), <EOF> (server
closed), <RST> (reset). redis-cli hides protocol errors and closes; use this when
the claim is about parsing, framing, partial reads, or when the server hangs up.
"""
import argparse, socket, sys, time


def dec(s):
    return s.encode("latin-1").decode("unicode_escape").encode("latin-1")


ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("port", type=int)
ap.add_argument("chunks", nargs="*")
ap.add_argument("--repeat", nargs=2, metavar=("BYTES", "N"), help="append BYTES*N as one chunk")
ap.add_argument("--then", action="append", default=[], help="chunk(s) sent after --repeat")
ap.add_argument("--wait", type=float, default=0.5, help="seconds to keep reading (default 0.5)")
ap.add_argument("--gap", type=float, default=0.05, help="pause between chunks")
ap.add_argument("--max", type=int, default=600, help="truncate printed reply to this many bytes")
a = ap.parse_args()

chunks = [dec(c) for c in a.chunks]
if a.repeat:
    chunks.append(dec(a.repeat[0]) * int(a.repeat[1]))
chunks += [dec(c) for c in a.then]

s = socket.create_connection(("127.0.0.1", a.port))
for i, c in enumerate(chunks):
    try:
        s.sendall(c)
    except (BrokenPipeError, ConnectionResetError) as e:
        print(f"send #{i} failed: {e}", file=sys.stderr); break
    time.sleep(a.gap)
s.settimeout(a.wait)
out, end = b"", "<open>"
deadline = time.time() + a.wait
try:
    while time.time() < deadline:
        d = s.recv(1 << 20)
        if not d:
            end = "<EOF>"; break
        out += d
except socket.timeout:
    pass
except ConnectionResetError:
    end = "<RST>"
s.close()
shown = repr(out[:a.max]) + (f" ... (+{len(out)-a.max} bytes)" if len(out) > a.max else "")
print(f"{shown} {end}  [{len(out)} bytes]")
