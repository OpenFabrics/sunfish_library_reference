# Copyright IBM Corp. 2023
# Copyright Hewlett Packard Enterprise Development LP 2024
# This software is available to you under a BSD 3-Clause License. 
# The full license terms are available here: https://github.com/OpenFabrics/sunfish_library_reference/blob/main/LICENSE
import json
import logging
import os
import uuid
import warnings
import shutil
from uuid import uuid4


import requests
from sunfish.events.event_handler_interface import EventHandlerInterface
from sunfish.events.redfish_subscription_handler import subscriptions
from sunfish.lib.exceptions import *

logger = logging.getLogger("RedfishEventHandler")
logging.basicConfig(level=logging.DEBUG)


class RedfishEventHandlersTable:
    @classmethod
    def AggregationSourceDiscovered(cls, event_handler: EventHandlerInterface, event: dict, context: str):
        ###
        # Fabric Agents are modelled as AggregationSource objects (RedFish v2023.1 at the time of writing this comment)
        # Registration will happen with the OFMF receiving a and event with MessageId: AggregationSourceDiscovered
        # The arguments of the event message are:
        #   - Arg0: "Redfish"
        #   - Arg1: "agent_ip:port"
        # I am also assuming that the agent name to be used is contained in the OriginOfCondifiton field of the event as in the below example:
        # {
        #    "OriginOfCondition: [
        #           "@odata.id" : "/redfish/v1/AggregationService/AggregationSource/AgentName"
        #    ]"
        # }
        logger.info("AggregationSourceDiscovered method called")

        connectionMethodId = event['OriginOfCondition']['@odata.id']
        hostname = event['MessageArgs'][1]  # Agent address

        response = requests.get(f"{hostname}/{connectionMethodId}")
        if response.status_code != 200:
            raise Exception("Cannot find ConnectionMethod")
        response = response.json()

        ### Save agent registration
        # connection_method_name = connectionMethodId.split('/')[-1]
        # connection_method_name = connectionMethodId[:-len(connection_method_name)]
        event_handler.core.storage_backend.write(response)

        aggregation_source_id = str(uuid.uuid4())
        aggregation_source_template = {
            "@odata.type": "#AggregationSource.v1_2_.AggregationSource",
            "@odata.id": f"{event_handler.core.conf['redfish_root']}/AggregationService/AggregationSources/{aggregation_source_id}",
            "HostName": hostname,
            "Id": aggregation_source_id,
            "Links": {
                "ConnectionMethod": {
                    "@odata.id": connectionMethodId
                },
                "ResourcesAccessed": []
            }
        }
        try:
            event_handler.core.storage_backend.write(aggregation_source_template)
        except Exception:
            raise Exception()

        agent_subscription_context = {"Context": aggregation_source_id.split('/')[-1]}

        resp_patch = requests.patch(f"{hostname}/redfish/v1/EventService/Subscriptions/SunfishServer",
                                    json=agent_subscription_context)

        return resp_patch

    @classmethod
    def ResourceCreated(cls, event_handler: EventHandlerInterface, event: dict, context: str):
        if context == "":
            raise PropertyNotFound("Missing agent context in ResourceCreated event")

        logger.info("New resource created")

        id = event['OriginOfCondition']['@odata.id']  # /redfish/v1/Fabrics/CXL
        aggregation_source = event_handler.core.storage_backend.read(
            os.path.join(event_handler.core.conf["redfish_root"],
            "AggregationService", "AggregationSources", context)
        )
        hostname = aggregation_source["HostName"]

        response = requests.get(f"{hostname}/{id}")
        if response.status_code != 200:
            raise Exception("Cannot find ConnectionMethod")
        response = response.json()

        add_aggregation_source_reference(response, aggregation_source)

        # here we are assuming that we are getting a fully populated redfish
        # object from the agent.
        if "@odata.id" not in response:
            logger.warning(f"Resource {id} did not have @odata.id set when retrieved from Agent. Initializing its value with {id}")
            response["odata.id"] = id

        event_handler.core.storage_backend.write(response)

        RedfishEventHandler.bfsInspection(event_handler.core, response, aggregation_source)

        event_handler.core.storage_backend.patch(id, aggregation_source)


    @classmethod
    def ClearResources(cls, event_handler: EventHandlerInterface, event: dict, context: str):
        ###
        # Receipt of this event will cause the core library to remove the entire Resources tree, and reload a clean initial tree
        # This will happen upon the Core receiving an event with MessageId: ClearResources
        # The arguments of the event message are:
        #   - Arg0: "<relative path_to_clean_resource_directory>
        # there is no protection on the receipt of this event
		# This event will not work if the backend file system is not the host's filesystem!
		#
        logger.info("ClearResources method called")
        resource_path = event['MessageArgs'][0]  # relative Resource Path
        logger.info(f"ClearResources path is {resource_path}")
        try:
            if os.path.exists('Resources'):
                shutil.rmtree('Resources')

            shutil.copytree(resource_path, 'Resources')
            resp = 204
        except Exception:
            raise Exception("ClearResources Failed")
            resp = 500
        return resp


    @classmethod
    def TriggerEvent(cls, event_handler: EventHandlerInterface, event: dict, context: str):
        ###
        # Receipt of this event will cause the core library to retrieve and send a specific event to a specific target
        # This will happen upon the API receiving an event with MessageId: TriggerEvent
        # The arguments of the event message are:
        #   - Arg0: "EventDescriptor"  --relative OS Filesystem path from core library application home directory
        #   - Arg1: "target_IP:port"
        # there is no protection on the inadvertant receipt of this event
		#
        logger.info("TriggerEvent method called")
        file_to_send = event['MessageArgs'][0]  # relative Resource Path
        hostname = event['MessageArgs'][1]  # Agent address
        initiator = event['OriginOfCondition']['@odata.id']
        logger.info(f"file_to_send path is {file_to_send}")
        try:
            if os.path.exists('file_to_send'):
                #shutil.rmtree('Resources')
                print("found the event file")
                # event_to_send = contents of file_to_send

        # these lines are not yet correct!!
        # send the event as a POST to the EventListener
        #response = requests.post(f"{hostname}/EventListener",event_to_send)
        #if response.status_code != 200:
        #    raise Exception("Cannot find ConnectionMethod")
        #response = response.json()

            resp = 204
        except Exception:
            raise Exception("TriggerEvents Failed")
            resp = 500
        return resp




class RedfishEventHandler(EventHandlerInterface):
    dispatch_table = {
        "AggregationSourceDiscovered": RedfishEventHandlersTable.AggregationSourceDiscovered,
        "ResourceCreated": RedfishEventHandlersTable.ResourceCreated,
        "TriggerEvent": RedfishEventHandlersTable.TriggerEvent,
		"ClearResources" : RedfishEventHandlersTable.ClearResources
    }

    def __init__(self, core):
        """init that sets the conf and calls the load subcriptions method

        Args:
            conf (dict): dictionary where are specified the storage implementation type and the specific backend configuration.
        """
        self.core = core
        self.redfish_root = core.conf["redfish_root"]
        self.fs_root = core.conf["backend_conf"]["fs_root"]
        self.subscribers_root = core.conf["backend_conf"]["subscribers_root"]
    @classmethod
    def dispatch(cls, message_id: str, event_handler: EventHandlerInterface, event: dict, context: str):
        if message_id in cls.dispatch_table:
            return cls.dispatch_table[message_id](event_handler, event, context)
        else:
            logger.debug(f"Message id '{message_id}' does not have a custom handler")

    def new_event(self, payload):
        """Compares event's information with the subsribtions data structure to find the Ids of the subscribers for that event.
        
        Args:
            payload (dict): event received.
        """
        for event in payload["Events"]:
            prefix = event["MessageId"].split('.')[0]
            messageId = event["MessageId"]
            origin = 'not_specified'

            to_forward = []
            to_exclude = []

            if prefix in subscriptions["RegistryPrefixes"]:
                for id in subscriptions["RegistryPrefixes"][prefix]["exclude"]:
                    to_exclude.extend(id)
            if messageId in subscriptions["MessageIds"]:
                for id in subscriptions["MessageIds"][messageId]["exclude"]:
                    to_exclude.append(id)
            
            """ ResourceTypes, OriginResources and SubordinateResources are checked only if the event
                contains OriginOfConditions because they refer to @odata.id
            """
            if "OriginOfCondition" in event:
                origin = event["OriginOfCondition"]["@odata.id"]
                try:
                    type = self.check_data_type(origin)
                except ResourceNotFound as e:
                    raise ResourceNotFound(e.resource_id)
                if type in subscriptions["ResourceTypes"]:
                    to_forward.extend(subscriptions["ResourceTypes"][type])
                if origin in subscriptions["OriginResources"]:
                    to_forward.extend(subscriptions["OriginResources"][origin])
                sub = self.check_subdirs(origin)
                to_forward.extend(sub)

            if prefix in subscriptions["RegistryPrefixes"]:
                for id in subscriptions["RegistryPrefixes"][prefix]["to_send"]:
                    to_forward.append(id)
            if messageId in subscriptions["MessageIds"]:
                for id in subscriptions["MessageIds"][messageId]["to_send"]:
                    to_forward.append(id)
            
            set1 = set(to_forward)
            set2 = set(to_exclude)
            to_forward = list(set1 - set2)

            return self.forward_event(to_forward, payload)
        
    def check_data_type(self, origin):
        length = len(self.redfish_root)
        resource = origin[length:]
        path = os.path.join(self.redfish_root, resource)
        try:
            data = self.core.storage_backend.read(path)
        except ResourceNotFound as e:
            raise ResourceNotFound(path) 
        type = data["@odata.type"].split('.')[0]
        return type.replace("#","") # #Évent -> Event 
          
    def forward_event(self, list, payload):
        """ Get Destination from the list of the subscribers' Ids and forwards the event.
            If the destination is not reachable, the Id is deleted from the list.
        Args:
            list (_type_): list of the subscribers Ids interested in that event
            payload (_type_): event details

        Raises:
            ResourceNotFound: if it is not possible to get the subscription's details.

        Returns:
            list: list of all the reachable subcribers for the event.
        """
        # resp = 400
        
        for id in list:
            path = os.path.join(self.redfish_root, 'EventService', 'Subscriptions', id)
            try:
                data = self.core.storage_backend.read(path)
                # print('send to: ', data["Id"])
                resp = requests.post(data['Destination'], json=payload)
                resp.raise_for_status()
            except (requests.exceptions.ConnectionError, requests.exceptions.HTTPError) as e:
                logger.warning(f"Unable to contact event destination {id} for event , skipping.")
                logger.warning(f"Event log: \n{json.dumps(payload, indent=2)}")
                list.remove(id)
            except ResourceNotFound:
                raise ResourceNotFound(path)

        # if forwarding status is okay it returns the list of subscribers to whom the event was forwarded
        return list

    def check_subdirs(self, origin):
        keylist = list(subscriptions["OriginResources"].keys())
        to_forward = []
        for el in keylist:
            if '/*' in el:
                base_origin = el.replace("/*", "")
                if base_origin in origin:
                        for id in subscriptions["OriginResources"][el]:
                            to_forward.append(id)
        
        return to_forward

    def bfsInspection(self, node, aggregation_source):
        queue = []
        visited = []
        fetched = []
        visited.append(node['@odata.id'])
        queue.append(node['@odata.id'])

        def handleNestedObject(self, obj):
            if type(obj) == list:
                for entry in obj:
                    if type(entry) == list or type(entry) == dict:
                        handleNestedObject(self, entry)
            if type(obj) == dict:
                for key,value in obj.items():
                    if key == '@odata.id':
                        RedfishEventHandler.handleEntryIfNotVisited(self, value, visited, queue)
                    elif type(value) == list or type(value) == dict:
                        handleNestedObject(self, value)

        while queue:
            queue = sorted(queue)
            id = queue.pop(0)
            redfish_obj = RedfishEventHandler.fetchResourceAndTree(self, id, aggregation_source, visited, queue, fetched)

            if redfish_obj is None or type(redfish_obj) != dict:
                logger.info(f"Resource - {id} - not available")
                continue

            for key, val in redfish_obj.items():
                if key == 'Links':
                    if type(val)==dict or type(val)==list:
                        handleNestedObject(self, val)
                if key == '@odata.id':
                    RedfishEventHandler.handleEntryIfNotVisited(self, val, visited, queue)
                    pass
                if type(val) == list or type(val) == dict:
                    handleNestedObject(self, val)
        return visited

    def get_aggregation_source(self, aggregation_source):
        try:
            path = os.path.join(self.conf["redfish_root"], "AggregationService", "AggregationSources")
            response = self.get_object(path)
        except ResourceNotFound:
            return ResourceNotFound(path)
        
        for member in response["Members"]:
            try:
                response = self.get_object(member["@odata.id"])
            except ResourceNotFound:
                raise ResourceNotFound(path)
            if aggregation_source in response["Links"]["ResourcesAccessed"]:
                return response
        return
    
    def handleEntryIfNotVisited(self,entry, visited, queue):
        if entry not in visited:
            visited.append(entry)
            queue.append(entry)

    def fetchResourceAndTree(self, id, aggregation_source, visited, queue, fetched): # if have no parent dirs
        path_nodes = id.split("/")
        need_parent_prefetch = False
        for node_position in range(4, len(path_nodes) - 1):
            redfish_path = f'/redfish/v1/{"/".join(path_nodes[3:node_position + 1])}'
            logger.info(f"Checking redfish path: {redfish_path}")
            if redfish_path not in visited:
                need_parent_prefetch = True
                logger.info(f"Inspect redfish path: {redfish_path}")
                queue.append(redfish_path)
                visited.append(redfish_path)
        if need_parent_prefetch:  # requeue
            queue.append(id)
        else:
            redfish_obj = RedfishEventHandler.fetchResource(self, id, aggregation_source)
            fetched.append(id)
            return redfish_obj
    
    def fetchResource(self, obj_id, aggregation_source):
        resource_endpoint = aggregation_source["HostName"] + obj_id
        logger.info(f"fetch: {resource_endpoint}")
        response = requests.get(resource_endpoint)

        if response.status_code == 200:
            redfish_obj = response.json()

            RedfishEventHandler.createInspectedObject(self,redfish_obj, aggregation_source)
            if redfish_obj['@odata.id'] not in aggregation_source["Links"]["ResourcesAccessed"]:
                aggregation_source["Links"]["ResourcesAccessed"].append(redfish_obj['@odata.id'])
            return redfish_obj
        
    def createInspectedObject(self,redfish_obj, aggregation_source):
        if '@odata.id' in redfish_obj:
            obj_path = os.path.relpath(redfish_obj['@odata.id'], self.conf['redfish_root'])
        else:
            raise PropertyNotFound(f"missing @odata.id in \n {json.dumps(redfish_obj, indent=2)}")

        file_path = os.path.join(self.conf['redfish_root'], obj_path)

        if 'Collection' not in redfish_obj['@odata.type']:
            try:
                if self.get_object(file_path) == redfish_obj:
                    pass
                elif self.get_object(file_path) != redfish_obj:
                    warnings.warn('Resource state changed')
            except ResourceNotFound:
                add_aggregation_source_reference(redfish_obj, aggregation_source)
                self.create_object(file_path, redfish_obj)
        else:
            logger.debug("This is a collection")

def add_aggregation_source_reference(redfish_obj, aggregation_source):
    #  BoundaryComponent = ["true", "false", "unknown"]
    oem = {
        "@odata.type": "#SunfishExtensions.v1_0_0.ResourceExtensions",
        "ManagingAgent": {
            "@odata.id": aggregation_source["@odata.id"]
        },
        "BoundaryComponent": "unknown"
    }
    if "Oem" not in redfish_obj:
        redfish_obj["Oem"] = {"Sunfish_RM": oem}
    elif "Sunfish_RM" not in redfish_obj["Oem"]:
        redfish_obj["Oem"]["Sunfish_RM"] = oem
    else:
        if "ManagingAgent" in redfish_obj["Oem"]["Sunfish_RM"]:
            # We should not be here because the object we are just visiting while adding the agent should not have a
            # managing agent reference in its fields. The one reason why we end-up here could be
            # that the agent has populated a field that it is none of its business.
            # What we are going to do for the time being is to rewrite the field with the current agent and generate a
            # warning for the user.
            # TODO: In the future we might want to check whether this is happening because the agent had failed and it
            #       is restarting under a new identity. Still, the agent should not have any business with this specific
            #       field because it is only generated and handled by sunfish.
            logger.warning(f"""The object {redfish_obj["@odata.id"]} returned while registering agent {aggregation_source["@odata.id"]} contains already a managing agent ({redfish_obj['Oem']['Sunfish_RM']['ManagingAgent']['@odata.id']}) 
                           and this should not be happening""")

        # the expected case is there is no ManagingAgent before this event handler creates the object, for now even if the Agent has 
        # set this value, we will over write.
        redfish_obj["Oem"]["Sunfish_RM"]["ManagingAgent"] = {
            "@odata.id": aggregation_source["@odata.id"]
        }
        if "BoundaryComponent" not in redfish_obj["Oem"]["Sunfish_RM"]:
                    redfish_obj["Oem"]["Sunfish_RM"]["BoundaryComponent"] = oem["BoundaryComponent"]
