# Running the unit tests

`pytest-homeassistant-custom-component` doesn't support native Windows (its
socket-blocking is incompatible with how `asyncio` sets up its event loop
there — same as upstream Home Assistant core, which also isn't tested on
Windows). Run tests under WSL instead:

```
wsl.exe -e bash -lc "cd /mnt/c/dev/solar-payback && uv run pytest tests/ -q"
```

WSL keeps its own `.venv` (Linux wheels differ from the Windows one); `uv`
manages it automatically on first run.

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
