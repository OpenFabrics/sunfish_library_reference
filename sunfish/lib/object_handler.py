# Copyright IBM Corp. 2023
# This software is available to you under a BSD 3-Clause License. 
# The full license terms are available here: https://github.com/OpenFabrics/sunfish_library_reference/blob/main/LICENSE
import logging

import sunfish.lib.core
from sunfish.models.types import *

logger = logging.getLogger("RedfishObjectHandler")


class RedfishObjectHandlersTable:
    @classmethod
    def ComputerSystem(cls, core: 'sunfish.lib.core.Core', path: str, operation: SunfishRequestType, payload: dict):
        return "ObjectHandler ComputerSystem"

    @classmethod
    def EventDestination(cls, core: 'sunfish.lib.core.Core', path: str, operation: SunfishRequestType, payload: dict):
        if operation == SunfishRequestType.CREATE:
            core.subscription_handler.new_subscription(payload)
        elif operation == SunfishRequestType.REPLACE or operation == SunfishRequestType.PATCH:
            core.subscription_handler.delete_subscription(payload)
            core.subscription_handler.new_subscription(payload)
        elif operation == SunfishRequestType.DELETE:
            core.subscription_handler.delete_subscription(path)


class RedfishObjectHandler:
    dispatch_table = {
        "ComputerSystem": RedfishObjectHandlersTable.ComputerSystem,
        "EventDestination": RedfishObjectHandlersTable.EventDestination
    }
    @classmethod
    def dispatch(cls, core: 'sunfish.lib.core.Core', object_type: str, path: str,
                 operation: SunfishRequestType, payload: dict = None):
        if object_type in cls.dispatch_table:
            return cls.dispatch_table[object_type](core, path, operation, payload)
        logger.debug(f"Object type '{object_type}' does not have a custom handler")

