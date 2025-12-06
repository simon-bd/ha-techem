"""Config flow for Techem integration."""
from __future__ import annotations
import logging
from typing import Any
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.data_entry_flow import FlowResult
from .const import DOMAIN, CONF_COUNTRY, CONF_OBJECT_ID, COUNTRIES
from .techem_api import TechemAPI

_LOGGER = logging.getLogger(__name__)

class TechemConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Techem."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            # Validate credentials
            api = TechemAPI(
                user_input[CONF_EMAIL],
                user_input[CONF_PASSWORD],
                user_input[CONF_OBJECT_ID],
                user_input[CONF_COUNTRY]
            )
            
            token = await self.hass.async_add_executor_job(api.get_token)
            
            if token:
                await self.async_set_unique_id(user_input[CONF_OBJECT_ID])
                self._abort_if_unique_id_configured()
                
                return self.async_create_entry(
                    title=f"Techem ({user_input[CONF_EMAIL]})",
                    data=user_input
                )
            else:
                errors["base"] = "invalid_auth"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_EMAIL): str,
                vol.Required(CONF_PASSWORD): str,
                vol.Required(CONF_OBJECT_ID): str,
                vol.Required(CONF_COUNTRY, default="dk"): vol.In({
                    code: country["name"] for code, country in COUNTRIES.items()
                })
            }),
            errors=errors
        )
