"""Sensor platform for Techem integration."""
from __future__ import annotations
from datetime import timedelta
import logging
from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD, UnitOfEnergy, UnitOfVolume, PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, CoordinatorEntity
from .const import DOMAIN, CONF_COUNTRY, CONF_OBJECT_ID
from .techem_api import TechemAPI

_LOGGER = logging.getLogger(__name__)
SCAN_INTERVAL = timedelta(hours=1)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Techem sensors."""
    api = TechemAPI(
        entry.data[CONF_EMAIL],
        entry.data[CONF_PASSWORD],
        entry.data[CONF_OBJECT_ID],
        entry.data[CONF_COUNTRY]
    )

    # Create coordinators for yearly and weekly data
    yearly_coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name="techem_yearly",
        update_method=lambda: hass.async_add_executor_job(api.get_data, True),
        update_interval=SCAN_INTERVAL,
    )

    weekly_coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name="techem_weekly",
        update_method=lambda: hass.async_add_executor_job(api.get_data, False),
        update_interval=SCAN_INTERVAL,
    )

    # Fetch initial data
    await yearly_coordinator.async_config_entry_first_refresh()
    await weekly_coordinator.async_config_entry_first_refresh()

    object_id = entry.data[CONF_OBJECT_ID]

    sensors = [
        # Base yearly sensors
        TechemBaseSensor(yearly_coordinator, "energy", "Energy This Year", UnitOfEnergy.KILO_WATT_HOUR, 0, object_id, "yearly"),
        TechemBaseSensor(yearly_coordinator, "water", "Water This Year", UnitOfVolume.CUBIC_METERS, 1, object_id, "yearly"),
        
        # Base weekly sensors
        TechemBaseSensor(weekly_coordinator, "energy", "Energy This Week", UnitOfEnergy.KILO_WATT_HOUR, 0, object_id, "weekly"),
        TechemBaseSensor(weekly_coordinator, "water", "Water This Week", UnitOfVolume.CUBIC_METERS, 1, object_id, "weekly"),
        
        # Yearly comparison sensors
        TechemComparisonSensor(yearly_coordinator, "energy", "Energy Compared to Last Year", PERCENTAGE, 0, object_id, "yearly"),
        TechemComparisonSensor(yearly_coordinator, "water", "Water Compared to Last Year", PERCENTAGE, 1, object_id, "yearly"),
        
        # Weekly daily average sensors
        TechemDailyAverageSensor(weekly_coordinator, "energy", "Energy Daily Average Last 7 Days", UnitOfEnergy.KILO_WATT_HOUR, 0, object_id),
        TechemDailyAverageSensor(weekly_coordinator, "water", "Water Daily Average Last 7 Days", UnitOfVolume.CUBIC_METERS, 1, object_id),
        
        # Weekly comparison sensors
        TechemComparisonSensor(weekly_coordinator, "energy", "Energy Compared to Previous Week", PERCENTAGE, 0, object_id, "weekly"),
        TechemComparisonSensor(weekly_coordinator, "water", "Water Compared to Previous Week", PERCENTAGE, 1, object_id, "weekly"),
    ]

    async_add_entities(sensors)


class TechemBaseSensor(CoordinatorEntity, SensorEntity):
    """Techem base sensor showing current period value."""

    def __init__(self, coordinator, sensor_type: str, name: str, unit: str, index: int, object_id: str, period: str):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._sensor_type = sensor_type
        self._index = index
        self._attr_name = f"Techem {name}"
        self._attr_unique_id = f"techem_{object_id}_{sensor_type}_{period}"
        self._attr_native_unit_of_measurement = unit
        self._attr_state_class = SensorStateClass.TOTAL_INCREASING

    @property
    def native_value(self):
        """Return the state of the sensor."""
        if self.coordinator.data and "values" in self.coordinator.data:
            raw_value = self.coordinator.data["values"][self._index]
            if self._sensor_type == "water":
                return round(raw_value, 3)
            return round(raw_value, 1)
        return None

    @property
    def extra_state_attributes(self):
        """Return extra attributes."""
        if self.coordinator.data and "comparisonValues" in self.coordinator.data:
            comp_value = self.coordinator.data["comparisonValues"][self._index]
            if self._sensor_type == "water":
                comp = round(comp_value, 3)
            else:
                comp = round(comp_value, 1)
            return {"comparison": comp}
        return {}


class TechemComparisonSensor(CoordinatorEntity, SensorEntity):
    """Techem comparison sensor showing percentage change."""

    def __init__(self, coordinator, sensor_type: str, name: str, unit: str, index: int, object_id: str, period: str):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._sensor_type = sensor_type
        self._index = index
        self._attr_name = f"Techem {name}"
        self._attr_unique_id = f"techem_{object_id}_{sensor_type}_comparison_{period}"
        self._attr_native_unit_of_measurement = unit
        self._attr_icon = "mdi:percent"

    @property
    def native_value(self):
        """Return the percentage change."""
        if self.coordinator.data and "values" in self.coordinator.data and "comparisonValues" in self.coordinator.data:
            current = self.coordinator.data["values"][self._index]
            last = self.coordinator.data["comparisonValues"][self._index]
            
            if last and last > 0:
                diff = current - last
                percent = (diff / last) * 100
                return round(percent, 0)
        return None


class TechemDailyAverageSensor(CoordinatorEntity, SensorEntity):
    """Techem daily average sensor for weekly data."""

    def __init__(self, coordinator, sensor_type: str, name: str, unit: str, index: int, object_id: str):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._sensor_type = sensor_type
        self._index = index
        self._attr_name = f"Techem {name}"
        self._attr_unique_id = f"techem_{object_id}_{sensor_type}_daily_average"
        self._attr_native_unit_of_measurement = unit
        self._attr_icon = "mdi:calendar-today"

    @property
    def native_value(self):
        """Return the daily average."""
        if self.coordinator.data and "values" in self.coordinator.data:
            weekly_value = self.coordinator.data["values"][self._index]
            daily_avg = weekly_value / 7
            
            if self._sensor_type == "water":
                return round(daily_avg, 3)
            return round(daily_avg, 1)
        return None