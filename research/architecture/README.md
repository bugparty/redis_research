# Architecture

How Redis is put together: its subsystems, how they connect, and the design
choices behind them. Notes should name the version they describe. Use 3.0
for the classic single-threaded design, and 7.0 when a newer mechanism
(threaded I/O, ACL, modules, functions) is the point.

## Suggested notes

Each item is a future note in this folder. The list is in roughly the order
a request flows through the server.

- [ ] `overview.md`: process model, main data structures (`redisServer`, `redisClient` / `client`, `redisDb`), startup in `main()`
- [ ] `event-loop.md`: `ae` reactor, file vs. time events, `beforeSleep`, `serverCron`
- [ ] `request-lifecycle.md`: accept, read query, parse RESP, `processCommand`, `call`, reply buffers, write
- [ ] `object-system.md`: `robj`, encodings, reference counting, shared objects, LRU/LFU fields
- [ ] `keyspace.md`: `redisDb`, expires dict, lazy and active expiry, eviction
- [ ] `persistence.md`: RDB fork + copy-on-write, AOF write/fsync policies, AOF rewrite
- [ ] `replication.md`: full vs. partial resync, replication backlog, PSYNC
- [ ] `sentinel.md`: monitoring, quorum, leader election, failover
- [ ] `cluster.md`: hash slots, gossip bus, MOVED/ASK redirection, failover
- [ ] `threading.md`: bio background threads, lazyfree, threaded I/O in 6.0+
- [ ] `memory.md`: `zmalloc`, jemalloc, compact encodings, active defrag

## Where to look

| Topic | 3.0 file(s) | 7.0 file(s) | Article in `redis-internals` |
|---|---|---|---|
| Server lifecycle | `redis.c`, `redis.h` | `server.c`, `server.h` | — |
| Event loop | `ae.c`, `ae_epoll.c` | `ae.c`, `ae_epoll.c` | — |
| Networking | `networking.c`, `anet.c` | `networking.c`, `anet.c`, `connection.c` | — |
| Persistence | `rdb.c`, `aof.c`, `rio.c` | `rdb.c`, `aof.c`, `rio.c` | `Server/persistence` |
| Pub/Sub | `pubsub.c` | `pubsub.c` | `Server/pubsub` |
| Replication | `replication.c` | `replication.c` | `Server/replica` (unfinished) |
| Cluster | `cluster.c` | `cluster.c` | `Server/cluster` |
