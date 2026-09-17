"""Seed a fresh HA test instance with a synthetic solar+grid+battery scenario.

Backfills three days of hourly external statistics (no live entities needed)
and points the Energy dashboard at them, so the harness reproduces the same
scenario every time regardless of what the `demo` integration ships.
"""

from __future__ import annotations

import json
import math
from datetime import datetime, timedelta, timezone

from ha_client import HAClient

BASE_URL = "http://localhost:8123"
SOURCE_DOMAIN = "solar_payback_test"
HOURS = 24 * 3
SERIES_START = datetime(2026, 9, 1, tzinfo=timezone.utc)


def solar_kwh(hour: int) -> float:
    if 6 <= hour <= 19:
        return max(0.0, 3.0 * math.sin(math.pi * (hour - 6) / 13))
    return 0.0


def consumption_kwh(hour: int) -> float:
    return 0.6 if 9 <= hour <= 21 else 0.3


def battery_charge_kwh(hour: int) -> float:
    return min(1.0, max(0.0, solar_kwh(hour) - consumption_kwh(hour)))


def battery_discharge_kwh(hour: int) -> float:
    return 0.5 if 18 <= hour <= 22 else 0.0


def grid_import_kwh(hour: int) -> float:
    return max(
        0.0, consumption_kwh(hour) - solar_kwh(hour) - battery_discharge_kwh(hour)
    )


def grid_export_kwh(hour: int) -> float:
    return max(0.0, solar_kwh(hour) - consumption_kwh(hour) - battery_charge_kwh(hour))


SERIES = {
    f"{SOURCE_DOMAIN}:solar_production": ("Solar production", solar_kwh),
    f"{SOURCE_DOMAIN}:grid_import": ("Grid import", grid_import_kwh),
    f"{SOURCE_DOMAIN}:grid_export": ("Grid export", grid_export_kwh),
    f"{SOURCE_DOMAIN}:battery_charge": ("Battery charge", battery_charge_kwh),
    f"{SOURCE_DOMAIN}:battery_discharge": ("Battery discharge", battery_discharge_kwh),
}


def hourly_series(hourly_kwh) -> list[dict]:
    cumulative = 0.0
    stats = []
    for hour in range(HOURS):
        cumulative += hourly_kwh(hour % 24)
        stats.append(
            {
                "start": (SERIES_START + timedelta(hours=hour)).isoformat(),
                "sum": round(cumulative, 3),
            }
        )
    return stats


def main() -> None:
    client = HAClient.onboard(
        BASE_URL, name="Test", username="test", password="test-password12"
    )

    for statistic_id, (name, hourly_kwh) in SERIES.items():
        client.call(
            type="recorder/import_statistics",
            metadata={
                "has_mean": False,
                "has_sum": True,
                "name": name,
                "source": SOURCE_DOMAIN,
                "statistic_id": statistic_id,
                "unit_of_measurement": "kWh",
            },
            stats=hourly_series(hourly_kwh),
        )

    client.call(
        type="energy/save_prefs",
        energy_sources=[
            {
                "type": "solar",
                "stat_energy_from": f"{SOURCE_DOMAIN}:solar_production",
                "config_entry_solar_forecast": None,
            },
            {
                "type": "grid",
                "flow_from": [
                    {
                        "stat_energy_from": f"{SOURCE_DOMAIN}:grid_import",
                        "stat_cost": None,
                        "entity_energy_price": None,
                        "number_energy_price": 0.28,
                    }
                ],
                "flow_to": [
                    {
                        "stat_energy_to": f"{SOURCE_DOMAIN}:grid_export",
                        "stat_compensation": None,
                        "entity_energy_price": None,
                        "number_energy_price": 0.09,
                    }
                ],
                "cost_adjustment_day": 0.0,
            },
            {
                "type": "battery",
                "stat_energy_from": f"{SOURCE_DOMAIN}:battery_discharge",
                "stat_energy_to": f"{SOURCE_DOMAIN}:battery_charge",
            },
        ],
        device_consumption=[],
    )

    prefs = client.call(type="energy/get_prefs")
    print(json.dumps(prefs["result"], indent=2))
    client.close()


if __name__ == "__main__":
    main()
