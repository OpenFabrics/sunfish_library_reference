# Copyright IBM Corp. 2023
# This software is available to you under a BSD 3-Clause License. 
# The full license terms are available here: https://github.com/OpenFabrics/sunfish_library_reference/blob/main/LICENSE
import logging
import string
from typing import Optional
import pdb
import os
import json

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
        uri_aliasDB = {}
        agent_response = None
        object_modified = False
        path_to_check = path
        print(f"!!obj path to foward is {path}")
        print(f"!!request_type is {request_type}")
        #pdb.set_trace()
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
        agent = Agent.is_agent_managed(self.core, path_to_check)
        print(f"managing agent is {agent}")
        if agent:
            logger.debug(f"{path} is managed by an agent, forwarding the request")
            obj_modified = self.xlateToAgentURIs(payload)
            # extract restored name from payload
            restored_path = payload["@odata.id"]
            try:
                agent_response = agent.forward_request(request_type, restored_path, payload=payload)
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
            # anything un-aliased for agent has to be undone
            # anything added by agent may need translated
            obj_modified = self.xlateToSunfishURIs(agent_response)

        else:
            logger.debug(f"{path} is not managed by an agent")

        return agent_response

    def xlateToAgentURIs(self, sunfish_obj ):

        def findNestedURIs(self, URI_to_match, URI_to_sub, obj, path_to_nested_URI):
            nestedPaths = []
            if type(obj) == list:
                i = 0;
                for entry in obj:
                    if type(entry) == list or type(entry) == dict:
                        nestedPaths.extend( findNestedURIs(self, URI_to_match, URI_to_sub, entry, path_to_nested_URI+"["+str(i)+"]"))
                    else:
                        i=i+1
            if type(obj) == dict:
                for key,value in obj.items():
                    if key == '@odata.id'and path_to_nested_URI != "":
                        # check @odata.id: value for an alias
                        if value == URI_to_match:
                            print(f"---- modifying {value} to {URI_to_sub}")
                            obj[key] = URI_to_sub
                            nestedPaths.append(path_to_nested_URI)
                    elif key != "Sunfish_RM" and (type(value) == list or type(value) == dict):
                        nestedPaths.extend(findNestedURIs(self, URI_to_match, URI_to_sub, value, path_to_nested_URI+"["+key+"]" ))
            return nestedPaths


        try:
            uri_alias_file = os.path.join(os.getcwd(), self.core.conf["backend_conf"]["fs_private"], 'URI_aliases.json')
            if os.path.exists(uri_alias_file):
                print(f"reading alias file {uri_alias_file}")
                with open(uri_alias_file, 'r') as data_json:
                    uri_aliasDB = json.load(data_json)
                    data_json.close()
            else:
                print(f"alias file {uri_alias_file} not found")
                raise Exception

        except:
            raise Exception


        try:
            sunfish_aliases = uri_aliasDB["Sunfish_xref_URIs"]["aliases"]
            pdb.set_trace()
            object_URI = sunfish_obj["@odata.id"]
            aliasedNestedPaths=[]
            obj_modified = False
            # check the obj ID and initial @odata.id
            if  object_URI in sunfish_aliases:
                sunfish_obj["@odata.id"] = sunfish_aliases[object_URI][0]
                obj_modified = True
                if sunfish_obj["Id"] == object_URI.split("/")[-1]:
                    sunfish_obj["Id"] = sunfish_aliases[object_URI][0].split("/")[-1]
            # now find the nested @odata.id URIs and check them
            for sunfish_URI, agent_URI in sunfish_aliases.items():
                # find all the references to the aliased sunfish_URI and replace it
                path_to_nested_URI=""
                # TODO agent_URI structure is a list, not a simple text string, v hence this index!
                aliasedNestedPaths= findNestedURIs(self, sunfish_URI, agent_URI[0], sunfish_obj, path_to_nested_URI )
                if aliasedNestedPaths:
                    obj_modified = True
                for path in aliasedNestedPaths:
                    print(f"---- replaced {sunfish_URI} with {agent_URI} at {path}")
            print(f"---- aliasedNestedPaths is {aliasedNestedPaths}")
            if obj_modified:
                logger.debug(f"---- object modified")
                print(f"---- final updated object")
                print(json.dumps(sunfish_obj, indent=2))
                pass

            if "Oem" in sunfish_obj and "Sunfish_RM" in sunfish_obj["Oem"] and \
                    "BoundaryComponent" in sunfish_obj["Oem"]["Sunfish_RM"]:
                if sunfish_obj["Oem"]["Sunfish_RM"]["BoundaryComponent"] == "BoundaryPort":
                    # need to check for boundary port redirected links
                    # TODO
                    print(f"------ checking for redirected boundary link")
                    pass

        except:
            logger.error(f"could not update links in object {object_URI}")

        #return sunfish_obj
        return obj_modified


    def xlateToSunfishURIs(self, agent_obj ):

        def findNestedURIs(self, URI_to_match, URI_to_sub, obj, path_to_nested_URI):
            nestedPaths = []
            if type(obj) == list:
                i = 0;
                for entry in obj:
                    if type(entry) == list or type(entry) == dict:
                        nestedPaths.extend( findNestedURIs(self, URI_to_match, URI_to_sub, entry, path_to_nested_URI+"["+str(i)+"]"))
                    else:
                        i=i+1
            if type(obj) == dict:
                for key,value in obj.items():
                    if key == '@odata.id'and path_to_nested_URI != "":
                        # check @odata.id: value for an alias
                        if value == URI_to_match:
                            print(f"---- modifying {value} to {URI_to_sub}")
                            obj[key] = URI_to_sub
                            nestedPaths.append(path_to_nested_URI)
                    elif key != "Sunfish_RM" and (type(value) == list or type(value) == dict):
                        nestedPaths.extend(findNestedURIs(self, URI_to_match, URI_to_sub, value, path_to_nested_URI+"["+key+"]" ))
            return nestedPaths


        try:
            uri_alias_file = os.path.join(os.getcwd(), self.core.conf["backend_conf"]["fs_private"], 'URI_aliases.json')
            if os.path.exists(uri_alias_file):
                print(f"reading alias file {uri_alias_file}")
                with open(uri_alias_file, 'r') as data_json:
                    uri_aliasDB = json.load(data_json)
                    data_json.close()
            else:
                print(f"alias file {uri_alias_file} not found")
                raise Exception

        except:
            raise Exception


        try:
            pdb.set_trace()
            owning_agent_id = agent_obj["Oem"]["Sunfish_RM"]["ManagingAgent"]["@odata.id"].split("/")[-1]
            agent_aliases = uri_aliasDB["Agents_xref_URIs"][owning_agent_id]["aliases"]
            object_URI = agent_obj["@odata.id"]
            aliasedNestedPaths=[]
            obj_modified = False
            # check the obj ID and initial @odata.id
            if  object_URI in agent_aliases:
                agent_obj["@odata.id"] = agent_aliases[object_URI]
                obj_modified = True
                if agent_obj["Id"] == object_URI.split("/")[-1]:
                    agent_obj["Id"] = agent_aliases[object_URI].split("/")[-1]
            # now find the nested @odata.id URIs and check them
            for agent_URI,sunfish_URI in agent_aliases.items():
                # find all the references to the aliased sunfish_URI and replace it
                path_to_nested_URI=""
                # TODO agent_URI structure is a list, not a simple text string, v hence this index!
                aliasedNestedPaths= findNestedURIs(self, agent_URI, sunfish_URI, agent_obj, path_to_nested_URI )
                if aliasedNestedPaths:
                    obj_modified = True
                for path in aliasedNestedPaths:
                    print(f"---- replaced {agent_URI } with {sunfish_URI} at {path}")
            if obj_modified:
                logger.debug(f"---- object modified")
                print(f"---- final updated object")
                print(json.dumps(agent_obj, indent=2))
                pass

            if "Oem" in agent_obj and "Sunfish_RM" in agent_obj["Oem"] and \
                    "BoundaryComponent" in agent_obj["Oem"]["Sunfish_RM"]:
                if agent_obj["Oem"]["Sunfish_RM"]["BoundaryComponent"] == "BoundaryPort":
                    # need to check for boundary port redirected links
                    # TODO
                    print(f"------ checking for redirected boundary link")
                    pass

        except:
            logger.error(f"could not update links in object {object_URI}")

        #return sunfish_obj
        return obj_modified


