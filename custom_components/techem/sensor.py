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
from homeassistant.util import slugify
from .const import DOMAIN, CONF_COUNTRY, CONF_OBJECT_ID, UNIT_HCA
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

    # Create coordinator for KPI data (rooms, meters, comparisons)
    kpi_coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name="techem_kpi",
        update_method=lambda: hass.async_add_executor_job(api.get_kpi_data, 30),
        update_interval=SCAN_INTERVAL,
    )

    # Fetch initial data
    await yearly_coordinator.async_config_entry_first_refresh()
    await weekly_coordinator.async_config_entry_first_refresh()
    await kpi_coordinator.async_config_entry_first_refresh()

    object_id = entry.data[CONF_OBJECT_ID]

    sensors = [
        # Base yearly sensors (4)
        TechemBaseSensor(yearly_coordinator, "energy", "Energy This Year", UnitOfEnergy.KILO_WATT_HOUR, 0, object_id, "yearly"),
        TechemBaseSensor(yearly_coordinator, "water", "Water This Year", UnitOfVolume.CUBIC_METERS, 1, object_id, "yearly"),
        TechemComparisonSensor(yearly_coordinator, "energy", "Energy Compared to Last Year", PERCENTAGE, 0, object_id, "yearly"),
        TechemComparisonSensor(yearly_coordinator, "water", "Water Compared to Last Year", PERCENTAGE, 1, object_id, "yearly"),
        
        # Base weekly sensors (6)
        TechemBaseSensor(weekly_coordinator, "energy", "Energy This Week", UnitOfEnergy.KILO_WATT_HOUR, 0, object_id, "weekly"),
        TechemBaseSensor(weekly_coordinator, "water", "Water This Week", UnitOfVolume.CUBIC_METERS, 1, object_id, "weekly"),
        TechemDailyAverageSensor(weekly_coordinator, "energy", "Energy Daily Average Last 7 Days", UnitOfEnergy.KILO_WATT_HOUR, 0, object_id),
        TechemDailyAverageSensor(weekly_coordinator, "water", "Water Daily Average Last 7 Days", UnitOfVolume.CUBIC_METERS, 1, object_id),
        TechemComparisonSensor(weekly_coordinator, "energy", "Energy Compared to Previous Week", PERCENTAGE, 0, object_id, "weekly"),
        TechemComparisonSensor(weekly_coordinator, "water", "Water Compared to Previous Week", PERCENTAGE, 1, object_id, "weekly"),
    ]

    # Add KPI-based sensors if data is available
    if kpi_coordinator.data:
        # Total heat sensor
        sensors.append(
            TechemTotalHeatSensor(kpi_coordinator, object_id)
        )
        
        # Property comparison sensors
        sensors.extend([
            TechemPropertyComparisonSensor(kpi_coordinator, "previous_period", "Heat vs Previous Period", object_id),
            TechemPropertyComparisonSensor(kpi_coordinator, "previous_year", "Heat vs Previous Year", object_id),
            TechemPropertyComparisonSensor(kpi_coordinator, "property", "Heat vs Property Average", object_id),
        ])
        
        # Dynamic room sensors
        rooms = kpi_coordinator.data.get("rooms", [])
        for room in rooms:
            sensors.append(
                TechemRoomSensor(kpi_coordinator, room["label"], object_id)
            )
        
        # Dynamic meter sensors
        meters = kpi_coordinator.data.get("meters", [])
        for meter in meters:
            meter_number = meter["object"]["group"]["meter"]["number"]
            room_name = meter["object"]["group"]["meter"]["roomName"]
            sensors.append(
                TechemMeterSensor(kpi_coordinator, meter_number, room_name, object_id)
            )

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


class TechemTotalHeatSensor(CoordinatorEntity, SensorEntity):
    """Techem total heat consumption sensor."""

    def __init__(self, coordinator, object_id: str):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_name = "Techem Heat Total"
        self._attr_unique_id = f"techem_{object_id}_heat_total"
        self._attr_native_unit_of_measurement = UNIT_HCA
        self._attr_state_class = SensorStateClass.TOTAL_INCREASING
        self._attr_icon = "mdi:radiator"

    @property
    def native_value(self):
        """Return the total heat consumption."""
        if self.coordinator.data:
            return round(self.coordinator.data.get("total", 0), 1)
        return None


class TechemPropertyComparisonSensor(CoordinatorEntity, SensorEntity):
    """Techem property comparison sensor."""

    def __init__(self, coordinator, comparison_type: str, name: str, object_id: str):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._comparison_type = comparison_type
        self._attr_name = f"Techem {name}"
        self._attr_unique_id = f"techem_{object_id}_comparison_{comparison_type}"
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_icon = "mdi:percent"

    @property
    def native_value(self):
        """Return the comparison percentage."""
        if not self.coordinator.data:
            return None
            
        total = self.coordinator.data.get("total", 0)
        if total == 0:
            return None
            
        if self._comparison_type == "previous_period":
            compare_value = self.coordinator.data.get("previousPeriod", 0)
        elif self._comparison_type == "previous_year":
            compare_value = self.coordinator.data.get("previousYear", 0)
        elif self._comparison_type == "property":
            compare_value = self.coordinator.data.get("propertyComparison", 0)
        else:
            return None
            
        if compare_value and compare_value > 0:
            diff = total - compare_value
            percent = (diff / compare_value) * 100
            return round(percent, 0)
        return None


class TechemRoomSensor(CoordinatorEntity, SensorEntity):
    """Techem room consumption sensor."""

    def __init__(self, coordinator, room_label: str, object_id: str):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._room_label = room_label
        self._attr_name = f"Techem Heat {room_label}"
        self._attr_unique_id = f"techem_{object_id}_room_{slugify(room_label)}"
        self._attr_native_unit_of_measurement = UNIT_HCA
        self._attr_state_class = SensorStateClass.TOTAL_INCREASING
        self._attr_icon = "mdi:home-thermometer"

    @property
    def native_value(self):
        """Return the room consumption."""
        if self.coordinator.data and "rooms" in self.coordinator.data:
            for room in self.coordinator.data["rooms"]:
                if room["label"] == self._room_label:
                    return round(room["value"], 1)
        return None


class TechemMeterSensor(CoordinatorEntity, SensorEntity):
    """Techem individual meter sensor."""

    def __init__(self, coordinator, meter_number: str, room_name: str, object_id: str):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._meter_number = meter_number
        self._room_name = room_name
        self._attr_name = f"Techem Meter {room_name}"
        self._attr_unique_id = f"techem_{object_id}_meter_{meter_number}"
        self._attr_native_unit_of_measurement = UNIT_HCA
        self._attr_state_class = SensorStateClass.TOTAL_INCREASING
        self._attr_icon = "mdi:gauge"

    @property
    def native_value(self):
        """Return the meter reading."""
        if self.coordinator.data and "meters" in self.coordinator.data:
            for meter in self.coordinator.data["meters"]:
                if meter["object"]["group"]["meter"]["number"] == self._meter_number:
                    return round(meter["value"], 1)
        return None

    @property
    def extra_state_attributes(self):
        """Return meter details."""
        return {
            "meter_number": self._meter_number,
            "room": self._room_name
        }