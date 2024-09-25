# Copyright IBM Corp. 2023
# Copyright Hewlett Packard Enterprise Development LP 2024
# This software is available to you under a BSD 3-Clause License. 
# The full license terms are available here: https://github.com/OpenFabrics/sunfish_library_reference/blob/main/LICENSE
import json
import logging
import os
import warnings
import shutil
from uuid import uuid4
import pdb

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
        connection_method_name = connectionMethodId.split('/')[-1]
        connection_method_name = connectionMethodId[:-len(connection_method_name)]
        event_handler.core.create_object(connection_method_name, response)

        connection_method_template = {
            "@odata.type": "#AggregationSource.v1_2_.AggregationSource",
            "HostName": hostname,
            "Links": {
                "ConnectionMethod": {
                    "@odata.id": connectionMethodId
                },
                "ResourcesAccessed": []
            }
        }

        try:
            resp_post = event_handler.core.create_object(
                os.path.join(event_handler.core.conf["redfish_root"], "AggregationService/AggregationSources"),
                connection_method_template)
        except Exception:
            raise Exception()

        aggregation_source_id = resp_post['@odata.id']
        agent_subscription_context = {"Context": aggregation_source_id.split('/')[-1]}

        resp_patch = requests.patch(f"{hostname}/redfish/v1/EventService/Subscriptions/SunfishServer",
                                    json=agent_subscription_context)

        return resp_patch

    @classmethod
    def ResourceCreated(cls, event_handler: EventHandlerInterface, event: dict, context: str):
        # incoming context (an aggregation_source ID) comes from event sender
        if context == "":
            raise PropertyNotFound("Missing agent context in ResourceCreated event")

        logger.info("New resource created")

        id = event['OriginOfCondition']['@odata.id']  # ex:  /redfish/v1/Fabrics/CXL
        logger.info(f"aggregation_source's redfish URI: {id}")
        #  must have an aggregation_source object to assign as owner of new resource
        aggregation_source = event_handler.core.storage_backend.read(
            os.path.join(event_handler.core.conf["redfish_root"],
            "AggregationService", "AggregationSources", context)
        )
        hostname = aggregation_source["HostName"]
        response = requests.get(f"{hostname}/{id}")

        if response.status_code != 200:
            raise Exception("Cannot find new resource at aggregation_source")
        response = response.json()
        print(f"new resource is \n")
        print(json.dumps(response, indent=4))

        # add_aggregation_source_reference(response, aggregation_source)
        # here we are assuming that we are getting a fully populated redfish
        # object from the agent.
        if "@odata.id" not in response:
            logger.warning(f"Resource {id} did not have @odata.id set when retrieved from Agent. Initializing its value with {id}")
            response["odata.id"] = id

        # shouldn't be writing the new object before 'inspecting it'
        #event_handler.core.storage_backend.write(response)
        #event_handler.core.create_object(id, response)

        RedfishEventHandler.bfsInspection(event_handler.core, response, aggregation_source)

        event_handler.core.storage_backend.patch(id, aggregation_source)

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
        #file_path = os.path.join(self.conf['redfish_root'], file_to_send)
        hostname = event['MessageArgs'][1]  # target address
        destination = hostname + "/EventListener" # may match a Subscription object's 'Destination' property
        logger.debug(f"path of file_to_send is {file_to_send}")
        try:
            if os.path.exists(file_to_send):
                with open(file_to_send, 'r') as data_json:
                    event_to_send = json.load(data_json)
                    data_json.close()

                logger.debug("found the event file")

                if event_to_send["Context"] == "":
                    logger.debug("no context in template event")
                    # don't fill it in, send the NULL
                    pass
                elif event_to_send["Context"] == "None":
                    logger.debug("template event uses subscriber assigned Context")
                    # check if the Destination for this event is a registered subscriber
                    # use as "Context" of this the event_to_send, or use NULL if not found
                    event_to_send["Context"] = RedfishEventHandler.find_subscriber_context(event_handler.core, destination)
                    pass

                logger.debug(f"event_to_send\n {event_to_send}" ) 
                try:
                    # send the event as a POST to the EventListener
                    response = requests.post(destination,json=event_to_send)
                    if response.status_code != 200:
                        logger.debug(f"Destination returned code {response.status_code}")
                        return response
                    else: 
                        logger.info(f"TriggerEvents Succeeded: code {response.status_code}")
                        return response
                except Exception:
                    raise Exception(f"Event forwarding to destination {destination} failed.")
                    response = 500
                    return response

            else:
                logger.error(f"file not found: {file_to_send} ")
                response = 404
                return response
        except Exception:
            raise Exception("TriggerEvents Failed")
            resp = 500
            return resp


    

class RedfishEventHandler(EventHandlerInterface):
    dispatch_table = {
        "AggregationSourceDiscovered": RedfishEventHandlersTable.AggregationSourceDiscovered,
        "ResourceCreated": RedfishEventHandlersTable.ResourceCreated,
        "TriggerEvent": RedfishEventHandlersTable.TriggerEvent
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
        self.backend = core.storage_backend
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
            data = self.core.get_object(path)
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
                data = self.core.get_object(path)
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

    def find_subscriber_context(self, destination):
        # look up the subscriber's "Context" for the given event Destination
        pdb.set_trace()
        context = ""
        try:
            #subscribers_list = event_handler.core.storage_backend.read(
            #subscribers_list = self.core.storage_backend.read(
            subscribers_list = self.storage_backend.read(
                    os.path.join(self.conf["redfish_root"],
                    "EventService", "Subscriptions")
                    )
            logger.debug(f"subscribers: {subscribers_list}")
            for member in subscribers_list['Members']:
                logger.debug(f"checking {member}")
                subscriber = self.storage_backend.read(member["@odata.id"])
                if subscriber['Destination'] == destination:
                    context=subscriber['Context']
                    logger.info(f"Found matching Destination in {member}")

        except Exception:
            logger.info(f"failed to find a matching Destination")

        return context


    def bfsInspection(self, node, aggregation_source):
        queue = []
        visited = []
        fetched = []
        notfound = []
        uploaded = []
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
                        print(f"found URL to Redfish obj {value}")
                        RedfishEventHandler.handleEntryIfNotVisited(self, value, visited, queue)
                    elif key != "Sunfish_RM" and (type(value) == list or type(value) == dict):
                        handleNestedObject(self, value) # need to ignore Sunfish_RM paths; they are wrong namespace

        while queue:
            queue = sorted(queue)
            print(f"sorted queue:  \n{queue}")
            id = queue.pop(0)
            redfish_obj = RedfishEventHandler.fetchResourceAndTree(self, id, aggregation_source, visited, queue, fetched)

            if redfish_obj is None:  # we failed to locate it in aggregation_source
                notfound.append(id)
            if redfish_obj is None or type(redfish_obj) != dict:
                logger.info(f"Resource - {id} - not available")
                continue

            for key, val in redfish_obj.items():
                if key == '@odata.id':
                    RedfishEventHandler.handleEntryIfNotVisited(self, val, visited, queue)
                    print(f"found URL to Redfish obj {val}")
                    pass
                #elif key == 'Links':
                #    if type(val)==dict or type(val)==list:
                #        handleNestedObject(self, val)
                #
                #  keep extracting nested @odata.id references from the currently fetched object
                elif type(val) == list or type(val) == dict:
                    handleNestedObject(self, val)
        print("\n\nattempted to fetch the following URIs:\n")
        print(json.dumps(sorted(fetched),indent = 4))
        print("\n\nAgent did not return objects for the following URIs:\n")
        print(json.dumps(sorted(notfound),indent = 4))
        return visited  #why not the 'fetched' list?

    def create_uploaded_object(self, path: str, payload: dict):
        # before to add the ID and to call the methods there should be the json validation

        # generate unique uuid if is not present
        if '@odata.id' not in payload and 'Id' not in payload:
            pass
            #id = str(uuid.uuid4())
            #to_add = {
                #'Id': id,
                #'@odata.id': os.path.join(path, id)
            #}
            #payload.update(to_add)
            raise exception(f"create_uploaded_object: no Redfish ID (@odata.id) found")

        #object_type = self._get_type(payload)
        # we assume agents can upload collections, just not the root level collections
        # we will check for uploaded collections later
        #if "Collection" in object_type:
            #raise CollectionNotSupported()

        payload_to_write = payload

        try:
            # 1. check the path target of the operation exists
            # self.storage_backend.read(path)
            # 2. we don't check the manager; we assume uploading agent is the manager unless it says otherwise
            #agent_response = self.objects_manager.forward_to_manager(SunfishRequestType.CREATE, path, payload=payload)
            #if agent_response:
                #payload_to_write = agent_response
            # 3. should be no custom handler, this is not a POST, we upload the objects directly into the Redfish database
            #self.objects_handler.dispatch(object_type, path, SunfishRequestType.CREATE, payload=payload)
            pass
        except ResourceNotFound:
            logger.error("The collection where the resource is to be created does not exist.")
        except AgentForwardingFailure as e:
            raise e
        except AttributeError:
            # The object does not have a handler.
            logger.debug(f"The object {object_type} does not have a custom handler")
            pass
        # 4. persist change in Sunfish tree
        return self.storage_backend.write(payload_to_write)

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
        print(f"fetchResourceAndTree path_nodes {path_nodes}")
        for node_position in range(4, len(path_nodes) - 1):
            redfish_path = f'/redfish/v1/{"/".join(path_nodes[3:node_position + 1])}'
            logger.info(f"Checking redfish path: {redfish_path}")
            print(f"visit path {redfish_path} ?")
            if redfish_path not in visited:  
                need_parent_prefetch = True
                logger.info(f"Inspect redfish path: {redfish_path}")
                print(f"adding redfish path to queue: {redfish_path}")
                queue.append(redfish_path)
                visited.append(redfish_path)
        if need_parent_prefetch:  # requeue this id and return 'None'
            queue.append(id)
        else:  # all grand-parent objects have been visited
            # go get this object from the aggregation_source
            redfish_obj = RedfishEventHandler.fetchResource(self, id, aggregation_source)
            fetched.append(id)
            return redfish_obj
    
    def fetchResource(self, obj_id, aggregation_source):
        # only called if all grand-parent objects have been put in queue, sorted, inspected, and already fetched.
        # The parent object, if not a collection, will also have already been fetched
        resource_endpoint = aggregation_source["HostName"] + obj_id
        logger.info(f"fetch: {resource_endpoint}")
        response = requests.get(resource_endpoint)

        if response.status_code == 200: # Agent must have returned this object
            redfish_obj = response.json()

            # now copy object into Sunfish inventory
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
        logger.debug(f"try creating object: {file_path}")

        '''
        if 'Collection' not in redfish_obj['@odata.type']:
            #  re-write this to explicitly check for object's existence in Sunfish!
            try:
                if self.get_object(file_path) == redfish_obj:
                    pass
                elif self.get_object(file_path) != redfish_obj:
                    warnings.warn('Resource state changed')
            except ResourceNotFound:
                add_aggregation_source_reference(redfish_obj, aggregation_source)
                # do we change the following to a simple FS write?
                print(f"creating object: {file_path}")
                self.create_object(file_path, redfish_obj)
        else:
            logger.debug("This is a collection")
        '''
        if 'Collection' in redfish_obj['@odata.type']:
            logger.debug("This is a collection, ignore it until we need it")
            pass
        else:
            fs_full_path = os.path.join(os.getcwd(), self.conf["backend_conf"]["fs_root"], obj_path, 'index.json')
            if os.path.exists(fs_full_path):
                # check if existing Sunfish object is same as that being fetched from aggregation_source
                # we have more work to do disambiguate duplicate names from different agents
                # for now we will just check to be sure we are uploading an actual identical object
                # (which shouldn't happen since we are adding in the Sunfish_RM details)
                if self.get_object(file_path) == redfish_obj:
                    warnings.warn('Duplicate Resource found, ignored')
                    pass
                elif self.get_object(file_path) != redfish_obj:
                    warnings.warn('Resource state changed')
                    # put object change checks and updates here

            else:   # assume new object, create it and its parent collection if needed
                add_aggregation_source_reference(redfish_obj, aggregation_source)
                print(f"creating object: {file_path}")
                RedfishEventHandler.create_uploaded_object(self, file_path, redfish_obj)
    

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

