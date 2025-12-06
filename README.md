# Techem Energy Monitor for Home Assistant

A Home Assistant integration for monitoring energy and water consumption from Techem heating cost allocators.

This integration provides near real-time access to your Techem consumption data, with updates approximately every hour (depending on Techem meter reporting).

<img width="1912" height="1207" alt="image" src="https://github.com/user-attachments/assets/01dc4e7a-66ff-4312-b51b-66d7f6f1d6b2" />

![Techem Dashboard Example](https://via.placeholder.com/800x400?text=Dashboard+Example)

## Features

- ✅ **Easy Setup**: Configure through Home Assistant UI - no YAML required
- ✅ **10 Sensors**: Access to your energy and water consumption as provided by Techem.
- ✅ **Multi-Country**: Supports Denmark (.dk) and Norway (.no)
- ✅ **Automatic Updates**: Data refreshes every hour
- ✅ **Comparison Data**: View consumption compared to previous periods based on Techem data.

## Sensors

The integration creates 10 sensors:

### Yearly Sensors (4)
- **Energy This Year**: Total kWh consumed this year
- **Water This Year**: Total m³ consumed this year  
- **Energy Compared to Last Year**: Percentage change vs. last year
- **Water Compared to Last Year**: Percentage change vs. last year

### Weekly Sensors (6)
- **Energy This Week**: Total kWh in the last 7 days
- **Water This Week**: Total m³ in the last 7 days
- **Energy Daily Average Last 7 Days**: Average kWh per day
- **Water Daily Average Last 7 Days**: Average m³ per day
- **Energy Compared to Previous Week**: Percentage change vs. previous 7 days
- **Water Compared to Previous Week**: Percentage change vs. previous 7 days

## Installation

### HACS (Recommended)

1. Open **HACS** in Home Assistant
2. Go to **Integrations**
3. Click the **⋮** menu (three dots) and select **Custom repositories**
4. Add this repository:
   - **Repository**: `https://github.com/simon-bd/ha-techem`
   - **Category**: Integration
5. Click **Download**
6. **Restart Home Assistant**
7. Go to **Settings → Devices & Services**
8. Click **+ Add Integration**
9. Search for "**Techem**"
10. Enter your credentials (see Configuration below)

### Manual Installation

1. Download this repository
2. Copy the `custom_components/techem` folder to your `config/custom_components/` directory
3. Restart Home Assistant
4. Go to **Settings → Devices & Services**
5. Click **+ Add Integration**
6. Search for "**Techem**"

## Configuration

When adding the integration, you'll need:

### 1. Email
Your TechemAdmin login email

### 2. Password
Your TechemAdmin password

**⚠️ Important**: Techem requires passwords with at least 12 characters, 1 number, 1 uppercase, 1 lowercase, and 1 special character. 

If your password contains special characters like `!`, `$`, `#`, `%`, etc., the integration handles this automatically - no need to escape or quote them.

### 3. Object ID
Your Techem object ID (approx. 20 characters, base64-encoded string)

**How to find your Object ID:**
1. Log in to [TechemAdmin](https://beboer.techemadmin.dk/) (or .no for Norway)
2. Open your browser's Developer Tools (F12)
3. Go to the **Network** tab
4. Refresh the page (F5)
5. Find a `graphql` request in the network list
6. Click on it and view the **Request** tab
7. Look for `objectId` - copy the value (e.g., `dGZ4eE1UZTdOLjYxX18yMzQ1Njc4`)

### 4. Country
Select your country:
- **Denmark** (uses techemadmin.dk)
- **Norway** (uses techemadmin.no)

## Usage Examples

### Simple Dashboard Card

```yaml
type: entities
title: Techem Energy
entities:
  - entity: sensor.techem_energy_this_year
  - entity: sensor.techem_energy_compared_to_last_year
  - entity: sensor.techem_energy_daily_average_last_7_days
```

### History Graph

```yaml
type: history-graph
title: Energy Usage
entities:
  - entity: sensor.techem_energy_this_week
  - entity: sensor.techem_water_this_week
hours_to_show: 168
```

### Automation Example

```yaml
automation:
  - alias: "High Energy Usage Alert"
    trigger:
      - platform: numeric_state
        entity_id: sensor.techem_energy_daily_average_last_7_days
        above: 50
    action:
      - service: notify.mobile_app
        data:
          message: "Energy usage is high: {{ states('sensor.techem_energy_daily_average_last_7_days') }} kWh/day"
```

## Troubleshooting

### "Invalid Auth" Error
- Double-check your email and password
- Verify you can log in at [TechemAdmin](https://beboer.techemadmin.dk/)
- Make sure you selected the correct country

### Sensors Show "Unknown"
- Wait up to 1 hour for the first data fetch
- Or manually update: **Settings → Devices & Services → Techem → ⋮ → Reload**
- Check Home Assistant logs for errors

### "Failed to Get Token" Error
- Verify your internet connection
- Check if TechemAdmin website is accessible
- Ensure your credentials are correct

### Enable Debug Logging

Add this to your `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.techem: debug
```

Then restart Home Assistant and check the logs.

## Credits

Original Python script by [@andreas-bertelsen](https://github.com/andreas-bertelsen/ha-techem)

Converted to HACS integration with UI configuration by [@simon-bd](https://github.com/simon-bd)

## License

This project is provided as-is without any warranty. Use at your own risk.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Support

If you find this integration helpful, consider:
- ⭐ Starring this repository
- 🐛 Reporting issues
- 💡 Suggesting new features

---
 
**Note**: This is an unofficial integration and is not affiliated with or endorsed by Techem.
