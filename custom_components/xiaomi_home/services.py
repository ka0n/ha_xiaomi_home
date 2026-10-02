# -*- coding: utf-8 -*-
"""Response-capable Xiaomi Home services."""
from __future__ import annotations

import voluptuous as vol

from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import (
    HomeAssistant, ServiceCall, ServiceResponse, SupportsResponse)
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import config_validation as cv, entity_registry

from .miot.const import DOMAIN
from .miot.miot_device import MIoTDevice, format_action_params
from .miot.miot_error import MIoTClientError
from .miot.miot_spec import MIoTSpecAction

SERVICE_EXECUTE_ACTION = 'execute_action'
ATTR_PARAMS = 'params'

SERVICE_EXECUTE_ACTION_SCHEMA = vol.Schema({
    vol.Required(ATTR_ENTITY_ID): cv.entity_id,
    vol.Optional(ATTR_PARAMS, default=[]): list,
})


def _find_standalone_action(
    hass: HomeAssistant, entity_id: str
) -> tuple[MIoTDevice, MIoTSpecAction]:
    """Resolve a standalone Xiaomi Home MIoT action entity."""
    registry_entry = entity_registry.async_get(hass).async_get(entity_id)
    if registry_entry is None or registry_entry.platform != DOMAIN:
        raise ServiceValidationError(
            f'{entity_id} is not a Xiaomi Home entity')
    if registry_entry.config_entry_id is None:
        raise ServiceValidationError(
            f'{entity_id} has no Xiaomi Home config entry')

    devices: list[MIoTDevice] | None = hass.data[DOMAIN]['devices'].get(
        registry_entry.config_entry_id)
    if not devices:
        raise ServiceValidationError(
            f'Xiaomi Home config entry for {entity_id} is not loaded')

    for device in devices:
        for actions in device.action_list.values():
            for action in actions:
                unique_id = device.gen_action_entity_id(
                    ha_domain=DOMAIN,
                    spec_name=action.name,
                    siid=action.service.iid,
                    aiid=action.iid)
                if unique_id == registry_entry.unique_id:
                    return device, action

    raise ServiceValidationError(
        f'{entity_id} is not a standalone MIoT action entity')


async def _async_execute_action(
    hass: HomeAssistant, call: ServiceCall
) -> ServiceResponse | None:
    """Execute a standalone MIoT action and optionally return its response."""
    device, action = _find_standalone_action(
        hass, call.data[ATTR_ENTITY_ID])

    try:
        in_list = format_action_params(action, call.data[ATTR_PARAMS])
    except ValueError as err:
        raise ServiceValidationError(str(err)) from err

    try:
        raw_output = await device.action_async(
            siid=action.service.iid,
            aiid=action.iid,
            in_list=in_list)
    except MIoTClientError as err:
        raise HomeAssistantError(str(err)) from err

    if not call.return_response:
        return None

    raw_output = raw_output or []
    return {
        'output': [
            {
                'piid': prop.iid,
                'name': prop.name,
                'format': prop.format_.__name__,
                'value': raw_output[index] if index < len(raw_output) else None,
            }
            for index, prop in enumerate(action.out)
        ],
        'raw_output': raw_output,
    }


def async_setup_services(hass: HomeAssistant) -> None:
    """Set up Xiaomi Home services."""
    async def async_execute_action(
        call: ServiceCall
    ) -> ServiceResponse | None:
        return await _async_execute_action(hass, call)

    hass.services.async_register(
        DOMAIN,
        SERVICE_EXECUTE_ACTION,
        async_execute_action,
        schema=SERVICE_EXECUTE_ACTION_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL)
