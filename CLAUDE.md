# Running the test harness

Disposable Docker HA instance with the integration mounted and a synthetic
solar/grid/battery scenario seeded into the Energy dashboard.

## Start

```
uv run python harness/up.py
```

This starts the container, waits for HA to be ready, seeds the scenario,
and opens `http://localhost:8123` (login `test` / `test-password12`).

## Tear down

```
cd harness
docker compose down -v
rm -rf config
```

The `rm -rf config` step is needed for a fully clean slate on the next run
— `harness/config` is gitignored and holds all HA state.
