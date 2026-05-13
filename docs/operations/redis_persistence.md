# Redis Persistence Runbook

Redis is used for cache, rate-limit counters, queue coordination, and session-adjacent state. Production Redis must run with AOF enabled and `appendfsync everysec` so a restart does not silently clear operational state.

## Required runtime settings

The production Compose service starts Redis with:

```bash
redis-server --appendonly yes --appendfsync everysec
```

The `/ready` endpoint checks Redis with `REDIS_PERSISTENCE_ENABLED=true`. If Redis is reachable but AOF is off or `appendfsync` is not `everysec`, readiness remains HTTP 200 and reports `checks.redis=warning` with a `warnings.redis` explanation.

## Backup

Run the backup from a host or container that can read the Redis data volume:

```bash
python backend/scripts/redis_backup_restore.py --backup --redis-data-dir /data --output-dir /backups/redis
```

The script copies `dump.rdb`, `appendonly.aof`, and Redis 7 `appendonlydir` when present, then writes `manifest.json`.

## Restore

Stop Redis before restore, or restore into a new volume and swap it in during maintenance.

```bash
python backend/scripts/redis_backup_restore.py --restore --redis-data-dir /data --input-dir /backups/redis/redis-YYYYMMDDTHHMMSSZ --force
```

After restore, start Redis and verify `/ready` returns either `ok` or an expected `warning` while the node is being reconfigured.

## Disaster recovery notes

- Prefer filesystem snapshots or volume snapshots for point-in-time recovery.
- Keep RDB snapshots and AOF artifacts together; restoring only one can lose recent writes.
- Document the Redis image tag and Compose command with each backup batch.