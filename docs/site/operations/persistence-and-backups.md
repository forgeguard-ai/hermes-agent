---
title: Persistence and backups
description: Understand the /opt/data state volume in ForgeGuard runtime deployments and how to back up, restore, and migrate durable Hermes state.
order: 31
status: stable
---

# Persistence and backups

The ForgeGuard runtime image separates an immutable install tree from mutable
state:

- **`/opt/hermes`** — the install tree, baked into the image and read-only at
  runtime. It contains no user data.
- **`/opt/data`** — all durable state: config, `.env` secrets, sessions, memory,
  skills, profiles, and logs. It is declared as a Docker `VOLUME` and is where
  `HERMES_HOME` points inside the container.

Because state lives entirely on the volume, upgrading is just recreating the
container from a newer image tag — see [Releases and upgrades](./releases-and-upgrades.md).

## Prerequisites

- A [runtime deployment](../deployment/runtime-images.md) with `-v ~/.hermes:/opt/data`.
- For the CLI/distrobox image, state lives in your host `~/.hermes` directly
  (the home directory is shared), so the same backup approach applies to that
  directory.

## What to back up

Back up the **entire** host directory bound to `/opt/data` (this guide uses
`~/.hermes`). It contains secrets (`~/.hermes/.env`) and everything the agent has
learned. Treat the backup as sensitive.

## Back up

Stop the container for a consistent snapshot, archive the directory, then start
it again:

```bash
docker stop hermes
tar czf hermes-state-$(date +%Y%m%d).tgz -C ~ .hermes
docker start hermes
```

For a running backup without downtime, archive from inside the container's
volume mount instead, accepting that state may be mid-write.

## Restore

Restore into the same host directory before starting the container:

```bash
docker stop hermes || true
tar xzf hermes-state-YYYYMMDD.tgz -C ~
docker start hermes
```

If you restore onto a host with different UID/GID ownership, pass matching
`HERMES_UID` / `HERMES_GID` so the in-container user owns the files.

## Verify

After a restore, confirm the agent sees its state:

```bash
docker exec -it hermes hermes doctor
curl --fail http://localhost:9119/api/status
```

Your profiles, sessions, and configuration should be present in the dashboard.

## Backup implications for upgrades and rollback

Because the image is immutable and state is external, a backup taken before an
upgrade is also your rollback path: if a newer tag misbehaves, recreate the
container from the previous immutable tag against the same (or a restored)
`~/.hermes`. See [Releases and upgrades](./releases-and-upgrades.md#roll-back).

## Related

- [Runtime images](../deployment/runtime-images.md)
- [Releases and upgrades](./releases-and-upgrades.md)
- [Dashboard authentication](./dashboard-authentication.md)
