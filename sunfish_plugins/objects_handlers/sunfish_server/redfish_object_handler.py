# Copyright IBM Corp. 2023
# This software is available to you under a BSD 3-Clause License. 
# The full license terms are available here: https://github.com/OpenFabrics/sunfish_library_reference/blob/main/LICENSE
import logging
import string
from typing import Optional

import sunfish.lib.core
from sunfish.lib.agents_management import Agent
from sunfish.lib.exceptions import AgentForwardingFailure
from sunfish.lib.object_handler_interface import ObjectHandlerInterface
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


class RedfishObjectHandler(ObjectHandlerInterface):
    dispatch_table = {
        "ComputerSystem": RedfishObjectHandlersTable.ComputerSystem,
        "EventDestination": RedfishObjectHandlersTable.EventDestination
    }

    def __init__(self, core: 'sunfish.lib.core.Core'):
        self.core = core

    def dispatch(self, object_type: str, path: str,
                 operation: SunfishRequestType, payload: dict = None):
        if object_type in self.dispatch_table:
            return self.dispatch_table[object_type](self.core, path, operation, payload)
        logger.debug(f"Object type '{object_type}' does not have a custom handler")

    def forward_to_manager(self, request_type: 'sunfish.models.types.SunfishRequestType', path: string, payload: dict = None) -> Optional[dict]:
        agent_response = None
        path_to_check = path
        if request_type == SunfishRequestType.CREATE:
            # When creating an object, the request must be done on the Collection. Since collections are generally not
            # marked with the managing agent we check whether the parent of the collection, that must be a single entity
            # is managed by an agent.
            # Example create a Fabric connections on a fabric named CXL would be issued against
            #  /redfish/v1/Fabrics/CXL/Connections
            # The connections collection does not have an agent but the parent CXL fabric does and that's what we are
            # going to use.
            # The only place where this might not be working is if the collection we post to is a top level one like:
            #  /redfish/v1/Systems
            # in this case there would be no parent to inherit the agent from. Here this creation request should be
            # rejected because in Sunfish only agents can create elements in the top level directories and this is done
            # via events.
            path_elems = path.split("/")[1:-1]
            path_to_check = "".join(f"/{e}" for e in path_elems)
            # get the parent path
        logger.debug(f"Checking managing agent for path: {path_to_check}")
        agent = Agent.is_agent_managed(self.core, path_to_check)
        if agent:
            logger.debug(f"{path} is managed by an agent, forwarding the request")
            try:
                agent_response = agent.forward_request(request_type, path, payload=payload)
            except AgentForwardingFailure as e:
                raise e

            if request_type == SunfishRequestType.CREATE:
                # mark the resource with the managing agent
                oem = {
                    "@odata.type": "#SunfishExtensions.v1_0_0.ResourceExtensions",
                    "ManagingAgent": {
                        "@odata.id": agent.get_id()
                    }
                }
                if "Oem" not in agent_response:
                    agent_response["Oem"] = {}
                    agent_response["Oem"]["Sunfish_RM"] = oem
        else:
            logger.debug(f"{path} is not managed by an agent")
        return agent_response
