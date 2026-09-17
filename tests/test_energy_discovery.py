"""Tests for M0 energy dashboard discovery."""

import json
from pathlib import Path

from homeassistant.components.energy.data import async_get_manager
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

from custom_components.solar_payback.energy_discovery import async_discover_energy

FIXTURES = Path(__file__).parent / "fixtures"


async def _seed_energy_prefs(hass: HomeAssistant, fixture_name: str) -> None:
    await async_setup_component(hass, "energy", {})
    prefs = json.loads((FIXTURES / fixture_name).read_text())
    manager = await async_get_manager(hass)
    await manager.async_update(prefs)


async def test_discovers_seeded_solar_grid_battery(hass: HomeAssistant) -> None:
    await _seed_energy_prefs(hass, "energy_prefs_seeded.json")

    discovery = await async_discover_energy(hass)

    assert [s.statistic_id for s in discovery.solar] == [
        "solar_payback_test:solar_production"
    ]

    assert [b.statistic_from for b in discovery.battery] == [
        "solar_payback_test:battery_discharge"
    ]
    assert [b.statistic_to for b in discovery.battery] == [
        "solar_payback_test:battery_charge"
    ]

    assert discovery.grid is not None
    assert len(discovery.grid.imports) == 1
    assert discovery.grid.imports[0].statistic_id == "solar_payback_test:grid_import"
    assert discovery.grid.imports[0].fixed_price == 0.28
    assert discovery.grid.imports[0].entity_price is None
    assert len(discovery.grid.exports) == 1
    assert discovery.grid.exports[0].statistic_id == "solar_payback_test:grid_export"
    assert discovery.grid.exports[0].fixed_price == 0.09

    assert discovery.devices == []


async def test_discovers_nothing_when_energy_dashboard_unconfigured(
    hass: HomeAssistant,
) -> None:
    await async_setup_component(hass, "energy", {})

    discovery = await async_discover_energy(hass)

    assert discovery.solar == []
    assert discovery.battery == []
    assert discovery.grid is None
    assert discovery.devices == []
