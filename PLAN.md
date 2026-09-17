# Solar Payback Tracker — Plan

## What this is

A Home Assistant addon that tracks the real payback progress of a home solar +
battery installation, using actual production/consumption/tariff data rather
than the static assumptions generic online payback calculators use.

## Why build it (vs. existing options)

Existing HACS options already cover a basic version: flat buy/sell price,
one blended payback number, linear projection from current data. This
project's differentiation:

- **Component-level split** — panels vs. battery vs. inverter tracked (and
  paid back) separately, since battery payback is usually much longer than
  panels-only and blending hides that.
- **Tariff realism** — tiered / time-of-use pricing, not a flat rate.
- **Degradation-aware projection** — forward projection accounts for
  capacity fade instead of a naive straight-line extrapolation.
- **Cold-start handling** — correctly handles the case where the solar/
  battery system predates when Home Assistant started monitoring it (see
  "Cold start" below).

Explicitly *not* trying to replace EMHASS or Predbat (battery dispatch
optimization against tariffs/solar forecast) — this is a savings/ROI tracker,
not a dispatch controller. If a dispatch-optimization need comes up later,
prefer integrating with one of those rather than rebuilding it.

## Key design decisions

- **Ship as a custom integration, not a Supervisor add-on.** HA offers two
  shapes for this kind of project: a Supervisor add-on (separate Docker
  container, talks to HA only over the websocket/REST API with a
  Supervisor-issued token) or a custom integration (Python code loaded
  in-process by HA core, HACS-installable). This project reads Energy
  dashboard config, reads recorder statistics, and needs to expose new
  sensor entities — all things an in-process integration gets for free via
  direct calls to the energy manager, `recorder.statistics`, and the entity
  registry, with no websocket hop or token needed. Comparable community
  projects are built this way for the same reason. Despite the doc title,
  "addon" throughout this plan means "custom integration" unless stated
  otherwise.

- **Data source: HA's Energy dashboard config, not manual entity picking.**
  Home Assistant stores Energy dashboard configuration centrally. As an
  in-process integration this is read via the energy component's manager
  directly (the same data the `energy/get_prefs` websocket command
  exposes to remote/frontend clients) — solar production entities, grid
  import/export entities with their cost settings (fixed rate or a dynamic
  price entity), battery in/out entities, and any individual devices added
  to the dashboard. Auto-discover from this instead of asking the user to
  re-pick entity IDs.

- **Cold start / pre-HA history.** HA's own recorder history only goes back
  to whenever HA started monitoring, which is usually well after system
  install. Fix: seed the payback baseline from the inverter/BMS's own onboard
  **lifetime cumulative sensor** (confirmed available in this setup — a
  "total since install" sensor), not from HA's recorder history. Where a
  lifetime sensor genuinely isn't available, fall back to a manual anchor:
  user enters install date + a known lifetime total (e.g. from the inverter's
  own app/portal) or a rough bill-based estimate, explicitly tagged as
  "estimated" vs. "measured" going forward.

- **Capital cost input is manual, split by component** (panels / battery /
  inverter), since the Energy dashboard has no concept of capital cost or
  component ownership — it only tracks flows.

## Milestones (each independently testable)

- **M0a — Test harness** (do this first, before touching real HA)
  - Unit tests run against fixture JSON (captured `energy/get_prefs` output,
    fixture statistics) — zero HA instance needed for 90% of iteration.
  - A disposable Docker HA instance, separate from the real home instance,
    seeded via the built-in `demo` integration (fake solar/grid/battery
    entities) plus `recorder/import_statistics` websocket calls to backfill
    synthetic long-term history — this is also how cold-start scenarios
    (M1) get constructed and tested deliberately.
  - *Test:* destroying and recreating the Docker instance reproduces the
    same test scenario every time.

- **M0 — Data discovery**
  - From within the integration, read the energy component's manager
    in-process to auto-discover solar/grid/battery/device entities and
    their configured pricing (no websocket call, no token — direct access
    since the integration runs inside HA core).
  - *Test:* returns correct entity types and cost config against the test
    harness's seeded instance, no manual entity list required.

- **M1 — Anchor & cost input**
  - Config for capital cost (split by component), install date, and a
    one-time baseline snapshot from the lifetime total sensor.
  - *Test:* restarting the addon doesn't reset or drift the baseline.

- **M2 — Flat-rate savings engine**
  - Cumulative savings since the anchor: self-consumption × buy price +
    export × sell price.
  - *Test:* hand-calculated savings for one real day matches the addon's
    output.

- **M3 — Payback sensors/dashboard**
  - Expose entities: cumulative savings, % of capital recovered, naive
    linear-projected payback date.
  - *Test:* sensors appear in HA, update on schedule, values are sane.

- **M4 — Tariff realism (TOU/tiers)**
  - Replace flat buy/sell price with the actual tariff schedule.
  - *Test:* run against a past billing period, compare to the real utility
    bill for that period.

- **M5 — Component-level split**
  - Separate payback tracking for panels-only vs. battery's incremental
    contribution.
  - *Test:* component paybacks sum to the same total as M3; battery's
    payback timeline is visibly longer than panels'.

- **M6 — Degradation-aware projection** (stretch)
  - Factor derated future output into the projected payback date instead
    of straight-line extrapolation.
  - *Test:* feeding a synthetic degradation curve measurably shifts the
    projected payback date.

- **M7 — Package as a real addon**
  - Docker container + addon config schema, installable via the addon
    store on a test HA instance.
  - *Test:* clean install, survives a restart, config persists.

## Open questions / things to confirm early

- Does the inverter integration expose cycle count or pack temperature
  alongside the lifetime total sensor and SOH? (Relevant if degradation
  tracking (M6) gets pulled in — was considered as an idea, deferred, but
  the lifetime-total sensor decision was made partly with this in mind.)
- Confirm the exact entity ID / integration providing the lifetime total
  sensor, and its behavior across HA restarts and inverter firmware updates
  (does it ever reset?).
