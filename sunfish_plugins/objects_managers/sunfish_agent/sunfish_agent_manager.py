# Copyright IBM Corp. 2023
# This software is available to you under a BSD 3-Clause License. 
# The full license terms are available here: https://github.com/OpenFabrics/sunfish_library_reference/blob/main/LICENSE
import logging
import string
from typing import Optional
import pdb

import sunfish.lib.core
from sunfish_plugins.objects_managers.sunfish_agent.agents_management import Agent
from sunfish.lib.exceptions import AgentForwardingFailure
from sunfish.lib.object_manager_interface import ObjectManagerInterface
from sunfish.models.types import *

logger = logging.getLogger("RedfishObjectHandler")


class SunfishAgentManager(ObjectManagerInterface):

    def __init__(self, core: 'sunfish.lib.core.Core'):
        self.core = core

    def forward_to_manager(self, request_type: 'sunfish.models.types.SunfishRequestType', path: string, payload: dict = None) -> Optional[dict]:
        agent_response = None
        path_to_check = path
        if request_type == SunfishRequestType.CREATE:
            # When creating an object, the request must be done on the collection. Since collections are generally not
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
        #pdb.set_trace()
        agent = Agent.is_agent_managed(self.core, path_to_check)
        if agent:
            logger.debug(f"{path} is managed by an agent, forwarding the request")
            #agent_json = sunfish_core.storage_backend.read(agent)
            #agent_uri = agent_json["Hostname"]
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
                    agent_response["Oem"] = {"Sunfish_RM": oem}
                elif "Sunfish_RM" not in agent_response["Oem"]:
                    agent_response["Oem"]["Sunfish_RM"] = oem
                else:
                    if "ManagingAgent" in agent_response["Oem"]["Sunfish_RM"]:
                        # We should not be here because the object we are asking the agent to create is obviously not
                        # existing. Hence, there should be no managing agent data in the object returned by the agent.
                        # What we are going to do for the time being is to rewrite the field with the current agent
                        # and generate a warning for the user.
                        logger.warning(f"""The object returned by agent {agent.get_id()} while creating {path} contains already
                                            managing agent ({agent_response['Oem']['Sunfish_RM']['ManagingAgent']['@odata.id']}) 
                                            and this should not be happening""")
                    agent_response["Oem"]["Sunfish_RM"]["ManagingAgent"] = {
                        "@odata.id": agent.get_id()
                    }

        else:
            logger.debug(f"{path} is not managed by an agent")
        return agent_response
