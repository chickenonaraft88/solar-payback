"""Discover the Home Assistant Energy dashboard configuration."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.energy.data import async_get_manager
from homeassistant.core import HomeAssistant


@dataclass
class SolarSource:
    statistic_id: str


@dataclass
class BatterySource:
    statistic_from: str
    statistic_to: str


@dataclass
class GridFlow:
    statistic_id: str
    entity_price: str | None
    fixed_price: float | None


@dataclass
class GridSource:
    imports: list[GridFlow]
    exports: list[GridFlow]


@dataclass
class DeviceSource:
    statistic_id: str
    name: str | None


@dataclass
class EnergyDiscovery:
    solar: list[SolarSource]
    battery: list[BatterySource]
    grid: GridSource | None
    devices: list[DeviceSource]


async def async_discover_energy(hass: HomeAssistant) -> EnergyDiscovery:
    """Read the Energy dashboard's configured sources directly from its manager."""
    manager = await async_get_manager(hass)
    prefs = manager.data or manager.default_preferences()

    solar: list[SolarSource] = []
    battery: list[BatterySource] = []
    grid: GridSource | None = None

    for source in prefs["energy_sources"]:
        if source["type"] == "solar":
            solar.append(SolarSource(statistic_id=source["stat_energy_from"]))
        elif source["type"] == "battery":
            battery.append(
                BatterySource(
                    statistic_from=source["stat_energy_from"],
                    statistic_to=source["stat_energy_to"],
                )
            )
        elif source["type"] == "grid":
            grid = GridSource(
                imports=[
                    GridFlow(
                        statistic_id=flow["stat_energy_from"],
                        entity_price=flow["entity_energy_price"],
                        fixed_price=flow["number_energy_price"],
                    )
                    for flow in source["flow_from"]
                ],
                exports=[
                    GridFlow(
                        statistic_id=flow["stat_energy_to"],
                        entity_price=flow["entity_energy_price"],
                        fixed_price=flow["number_energy_price"],
                    )
                    for flow in source["flow_to"]
                ],
            )

    devices = [
        DeviceSource(statistic_id=device["stat_consumption"], name=device.get("name"))
        for device in prefs["device_consumption"]
    ]

    return EnergyDiscovery(solar=solar, battery=battery, grid=grid, devices=devices)
