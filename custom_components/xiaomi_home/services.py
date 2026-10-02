# -*- coding: utf-8 -*-
"""Response-capable Xiaomi Home services."""
from __future__ import annotations

from functools import partial

import voluptuous as vol

from homeassistant.core import (
    EntityServiceResponse, HomeAssistant, ServiceCall, SupportsResponse)
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.service import batched_entity_service_call

from .miot.const import DATA_ACTION_ENTITIES, DOMAIN
from .miot.miot_device import MIoTActionEntity

SERVICE_EXECUTE_ACTION = 'execute_action'
ATTR_PARAMS = 'params'

SERVICE_EXECUTE_ACTION_SCHEMA = cv.make_entity_service_schema({
    vol.Optional(ATTR_PARAMS, default=[]): list,
})


def _get_loaded_action_entities(hass: HomeAssistant) -> dict[str, Entity]:
    """Return loaded Xiaomi Home MIoT action entities."""
    return hass.data[DOMAIN][DATA_ACTION_ENTITIES]


async def _async_execute_action(
    entities: list[Entity], call: ServiceCall
) -> EntityServiceResponse:
    """Execute exactly one loaded MIoT action entity."""
    if len(entities) != 1:
        raise ServiceValidationError(
            'exactly one Xiaomi Home action entity must be targeted')

    entity = entities[0]
    if not isinstance(entity, MIoTActionEntity):
        raise ServiceValidationError(
            'target is not a Xiaomi Home MIoT action entity')

    try:
        raw_output = await entity.async_execute(call.data[ATTR_PARAMS])
    except ValueError as err:
        raise ServiceValidationError(str(err)) from err
    except RuntimeError as err:
        raise HomeAssistantError(str(err)) from err

    raw_output = raw_output or []
    if not call.return_response:
        return {}

    return {
        entity.entity_id: {
            'output': [
                {
                    'piid': prop.iid,
                    'name': prop.name,
                    'format': prop.format_.__name__,
                    'value': (
                        raw_output[index]
                        if index < len(raw_output) else None),
                }
                for index, prop in enumerate(entity.spec.out)
            ],
            'raw_output': raw_output,
        }
    }


def async_setup_services(hass: HomeAssistant) -> None:
    """Set up Xiaomi Home services."""
    hass.services.async_register(
        DOMAIN,
        SERVICE_EXECUTE_ACTION,
        partial(
            batched_entity_service_call,
            hass,
            partial(_get_loaded_action_entities, hass),
            _async_execute_action),
        schema=SERVICE_EXECUTE_ACTION_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL)
