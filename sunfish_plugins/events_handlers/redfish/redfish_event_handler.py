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
        event_handler.core.storage_backend.write(response)

        aggregation_source_id = str(uuid.uuid4())
        aggregation_source_template = {
            "@odata.type": "#AggregationSource.v1_2_.AggregationSource",
            "@odata.id": f"{event_handler.core.conf['redfish_root']}AggregationService/AggregationSources/{aggregation_source_id}",
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
        # incoming context (an aggregation_source ID) comes from event sender
        #pdb.set_trace()
        if context == "":
            raise PropertyNotFound("Missing agent context in ResourceCreated event")
        # put the global definition and initial loading of sunfishAliasDB dictionary here
        # sunfishAliasDB contains renaming data, the alias xref array, the boundaryLink 
        # data, and assorted flags that are used during upload renaming and final merge of 
        # boundary components based on boundary links.
        #

        logger.info("New resource created")

        id = event['OriginOfCondition']['@odata.id']  # ex:  /redfish/v1/Fabrics/CXL
        logger.info(f"aggregation_source's redfish URI: {id}")
        #  must have an aggregation_source object to assign as owner of new resource
        agg_src_path = os.path.join(os.getcwd(), event_handler.core.conf["backend_conf"]["fs_root"], 
            "AggregationService", "AggregationSources", context)
        if os.path.exists(agg_src_path):
            aggregation_source = event_handler.core.storage_backend.read(agg_src_path)
        else:
            raise PropertyNotFound("Cannot find aggregation source; file does not exist")
        # fetch the actual resource to be created from agent
        hostname = aggregation_source["HostName"]
        response = requests.get(f"{hostname}/{id}")

        if response.status_code != 200:
            raise ResourceNotFound("Aggregation source read from Agent failed") 
        response = response.json()
        logger.info(f"new resource is \n")
        logger.info(json.dumps(response, indent=4))

        # here we are assuming that we are getting a fully populated redfish
        # object from the agent.  Add real tests here!
        if "@odata.id" not in response:
            # should never hit this!
            logger.warning(f"Resource {id} did not have @odata.id set when retrieved from Agent. Initializing its value with {id}")
            response["odata.id"] = id

        # New resource should not exist in Sunfish inventory
        length = len(event_handler.core.conf["redfish_root"])
        resource = response["@odata.id"][length:]
        fs_full_path = os.path.join(os.getcwd(), event_handler.core.conf["backend_conf"]["fs_root"], 
                resource, 'index.json')
        if not os.path.exists(fs_full_path):
            RedfishEventHandler.bfsInspection(event_handler.core, response, aggregation_source)
        else:  
            logger.warning(f"resource to create: {id} already exists.")
            # could be a second agent with naming conflicts, or same agent with duplicate
            # still run the inspection process on it to find cause of warning
            RedfishEventHandler.bfsInspection(event_handler.core, response, aggregation_source)
            

        # patch the aggregation_source object in storage with all the new resources found
        #pdb.set_trace()
        event_handler.core.storage_backend.patch(agg_src_path, aggregation_source)
        logger.debug(f"\n{json.dumps(aggregation_source, indent=4)}")
        return 200

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
        hostname = event['MessageArgs'][1]  # target address
        destination = hostname + "/EventListener" # may match a Subscription object's 'Destination' property
        logger.debug(f"path of file_to_send is {file_to_send}")
        #pdb.set_trace()
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
        self.fs_SunfishPrivate = core.conf["backend_conf"]["fs_private"]
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
        
        for id in list:
            path = os.path.join(self.redfish_root, 'EventService', 'Subscriptions', id)
            try:
                data = self.core.storage_backend.read(path)
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
        #pdb.set_trace()
        context = ""
        try:
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
                        RedfishEventHandler.handleEntryIfNotVisited(self, value, visited, queue)
                    elif key != "Sunfish_RM" and (type(value) == list or type(value) == dict):
                        handleNestedObject(self, value) # need to ignore Sunfish_RM paths; they are wrong namespace

        while queue:
            queue = sorted(queue)
            id = queue.pop(0)
            redfish_obj = RedfishEventHandler.fetchResourceAndTree(self, id, aggregation_source, \
                          visited, queue, fetched)

            if redfish_obj is None:  # we failed to locate it in aggregation_source
                notfound.append(id)
            if redfish_obj is None or type(redfish_obj) != dict:
                logger.info(f"Resource - {id} - not available")
                continue

            for key, val in redfish_obj.items():
                if key == '@odata.id':
                    pass
                #  keep extracting nested @odata.id references from the currently fetched object
                elif type(val) == list or type(val) == dict:
                    handleNestedObject(self, val)
        logger.info("\n\nattempted to fetch the following URIs:\n")
        logger.info(json.dumps(sorted(fetched),indent = 4))
        logger.info("\n\nAgent did not return objects for the following URIs:\n")
        logger.info(json.dumps(sorted(notfound),indent = 4))
        
        # now need to revisit all uploaded objects and update any links renamed after
        # the uploaded object was written
        RedfishEventHandler.updateAllAliasedLinks(self,aggregation_source)
        # now we need to re-direct any boundary port link references
        # this needs to be done on ALL agents, not just the one we just uploaded
        RedfishEventHandler.updateAllAgentsRedirectedLinks(self)

        return visited  

    def create_uploaded_object(self, path: str, payload: dict):
        # before to add the ID and to call the methods there should be the json validation

        # generate unique uuid if is not present
        if '@odata.id' not in payload and 'Id' not in payload:
            pass
            raise exception(f"create_uploaded_object: no Redfish ID (@odata.id) found")

        # we assume agents can upload collections, just not the root level collections
        # we will check for uploaded collections later

        payload_to_write = payload

        try:
            # this would be another location to verify new object to be written 
            # meets Sunfish and Redfish requirements
            pass
        except ResourceNotFound:
            logger.error("The collection where the resource is to be created does not exist.")
        except AgentForwardingFailure as e:
            raise e
        except AttributeError:
            # The object does not have a handler.
            logger.debug(f"The object {object_type} does not have a custom handler")
            pass
        # persist change in Sunfish tree
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
        for node_position in range(4, len(path_nodes) - 1):
            redfish_path = f'/redfish/v1/{"/".join(path_nodes[3:node_position + 1])}'
            logger.info(f"Checking redfish path: {redfish_path}")
            if redfish_path not in visited:  
                need_parent_prefetch = True
                logger.info(f"Inspect redfish path: {redfish_path}")
                queue.append(redfish_path)
                visited.append(redfish_path)
        if need_parent_prefetch:  # requeue this id and return 'None'
            queue.append(id)
        else:  # all grand-parent objects have been visited
            # go get this object from the aggregation_source
            # fetchResource() will also create the Sunfish copy, if appropriate
            redfish_obj = RedfishEventHandler.fetchResource(self, id, aggregation_source)
            fetched.append(id)
            return redfish_obj
    
    def fetchResource(self, obj_id, aggregation_source):
        # only called if all grand-parent objects have been put in queue, sorted, inspected, and already fetched.
        # The parent object, if not a collection, will also have already been fetched
        # this routine will also call create and/or merge the object into Sunfish database
        resource_endpoint = aggregation_source["HostName"] + obj_id
        logger.info(f"fetch: {resource_endpoint}")
        response = requests.get(resource_endpoint)

        if response.status_code == 200: # Agent must have returned this object
            redfish_obj = response.json()
            # however, it must be a minimally valid object
            # This would be a great spot to insert a call to a Redfish schema validation function
            # that could return a grading of this new redfish_obj: [PASS, FAIL, CAUTIONS] 
            # However, we are debugging not just code, but also new Redfish schema,
            # so for now we just test for two required Redfish Properties to help weed out obviously incorrect responses
            if '@odata.id' in redfish_obj and '@odata.type' in redfish_obj:

                # now rename if necessary and copy object into Sunfish inventory
                redfish_obj = RedfishEventHandler.createInspectedObject(self,redfish_obj, aggregation_source)
                if redfish_obj['@odata.id'] not in aggregation_source["Links"]["ResourcesAccessed"]:
                    aggregation_source["Links"]["ResourcesAccessed"].append(redfish_obj['@odata.id'])
                return redfish_obj
            else:
                # we treat this as an unsuccessful retrieval
                return 
        else: # Agent did not successfully return the obj_id sought
            # we still need to check the obj_id for an aliased parent segment
            # so we detect renamed navigation links 
            sunfish_aliased_URI = RedfishEventHandler.xlateToSunfishPath(self, obj_id, aggregation_source)
            if obj_id != sunfish_aliased_URI:
                RedfishEventHandler.updateSunfishAliasDB(self, sunfish_aliased_URI, obj_id, aggregation_source)


    def createInspectedObject(self,redfish_obj, aggregation_source):
        if '@odata.id' in redfish_obj:
            obj_path = os.path.relpath(redfish_obj['@odata.id'], self.conf['redfish_root'])
        else:
            # we shouldn't allow an improper object to be passed in, so let's take an exception
            raise PropertyNotFound(f"missing @odata.id in \n {json.dumps(redfish_obj, indent=2)}")

        file_path = os.path.join(self.conf['redfish_root'], obj_path)
        logger.debug(f"try creating agent-named object: {file_path}")

        agent_redfish_URI = redfish_obj['@odata.id']
        sunfish_aliased_URI = RedfishEventHandler.xlateToSunfishPath(self, agent_redfish_URI, aggregation_source)
        # @odata.id is the Agent-proposed path name, but we need to search for the Sunfish (aliased) name.
        # becomes part of xlateToSunfishObj(self, agent_obj,aggregation_source) -> translated_agent_obj
        # if Sunfish has aliased the object URI, we need to update the object before we write it!
        if agent_redfish_URI != sunfish_aliased_URI:
            redfish_obj['@odata.id'] = sunfish_aliased_URI
            RedfishEventHandler.updateSunfishAliasDB(self, sunfish_aliased_URI, agent_redfish_URI, aggregation_source)
            if 'Id' in redfish_obj:
                if redfish_obj['Id'] == agent_redfish_URI.split("/")[-1]:
                    redfish_obj['Id'] = sunfish_aliased_URI.split("/")[-1]
        logger.debug(f"xlated agent_redfish_URI is {sunfish_aliased_URI}")  
        if 'Collection' in redfish_obj['@odata.type']:
            logger.debug("This is a collection, ignore it until we need it")
            pass
        else:
            # use Sunfish (aliased) paths for conflict testing if it exists
            obj_path = os.path.relpath(sunfish_aliased_URI, self.conf['redfish_root'])
            fs_full_path = os.path.join(os.getcwd(), self.conf["backend_conf"]["fs_root"], obj_path, 'index.json')
            file_path = os.path.join(self.conf['redfish_root'], obj_path)

            if os.path.exists(fs_full_path):
                uploading_agent_uri= aggregation_source["@odata.id"]
                existing_obj = self.get_object(file_path)
                modified_existing_obj = False
                existing_agent_uri = existing_obj["Oem"]["Sunfish_RM"]["ManagingAgent"]["@odata.id"]
                logger.debug(f"managingAgent of Sunfish {obj_path} is {uploading_agent_uri}")
                if existing_agent_uri == uploading_agent_uri:
                    # reject this duplicate posting of the object from same agent 
                    # note we don't update the object 
                    warnings.warn('Duplicate Resource found, ignored')
                    pass
                else:
                    # is object a Fabric?
                    obj_type = redfish_obj["@odata.type"].split('.')[0]
                    obj_type = obj_type.replace("#","") # #Fabric -> Fabric
                    
                    if obj_type == 'Fabric':
                        # is the conflicting Fabric object the same Fabric Object?
                        if "UUID" in redfish_obj and "UUID" in existing_obj:
                            if redfish_obj['UUID'] == existing_obj['UUID']:
                                # assume new Fabric object is the same as existing one
                                # because aggregation_sources are cooperating
                                # So, do not post this newly uploaded copy
                                # However, do update existing object with new 'sharer agent'
                                modified_existing_obj =RedfishEventHandler.updateIfMergedFabrics(self,redfish_obj, \
                                        uploading_agent_uri, existing_obj)
                                if modified_existing_obj:
                                    self.storage_backend.replace(existing_obj)
                                    logger.info(f"----- updated (replaced) existing fabric object")
                            else:
                                # different fabrics, just rename the new one
                                redfish_obj = RedfishEventHandler.renameUploadedObject(self, redfish_obj, aggregation_source)
                                add_aggregation_source_reference(redfish_obj, aggregation_source)
                                logger.info(f"creating object: {file_path}")
                                RedfishEventHandler.create_uploaded_object(self, file_path, redfish_obj)
                        else:
                            # assume different fabrics, just rename the new one
                            redfish_obj = RedfishEventHandler.renameUploadedObject(self, redfish_obj, aggregation_source)
                            add_aggregation_source_reference(redfish_obj, aggregation_source)
                            logger.info(f"creating object: {file_path}")
                            RedfishEventHandler.create_uploaded_object(self, file_path, redfish_obj)
                    else:
                        # we have a simple name conflict on a non-Fabric object
                        # find new name, build xref, check boundary ports and create the new object
                        redfish_obj = RedfishEventHandler.renameUploadedObject(self, redfish_obj, aggregation_source)
                        add_aggregation_source_reference(redfish_obj, aggregation_source)
                        logger.info(f"creating object: {file_path}")
                        if redfish_obj["Oem"]["Sunfish_RM"]["BoundaryComponent"] == "BoundaryPort":
                            RedfishEventHandler.track_boundary_port(self, redfish_obj, aggregation_source)
                        RedfishEventHandler.create_uploaded_object(self, file_path, redfish_obj)


            else:   # assume new object, create it and its parent collection if needed
                add_aggregation_source_reference(redfish_obj, aggregation_source)
                logger.info(f"creating object: {file_path}")
                if redfish_obj["Oem"]["Sunfish_RM"]["BoundaryComponent"] == "BoundaryPort":
                    RedfishEventHandler.track_boundary_port(self, redfish_obj, aggregation_source)
                # is this new object a new fabric object with same fabric UUID as an existing fabric?
                RedfishEventHandler.create_uploaded_object(self, file_path, redfish_obj)

        return redfish_obj
    
    def xlateToSunfishPath(self,agent_path, aggregation_source):
        # redfish_obj uses agent namespace
        # aggregation_source is an object in the Sunfish namespace
        # will eventually replace file read & load of aliasDB with aliasDB passed in as arg
        try:
            uri_alias_file = os.path.join(os.getcwd(), self.conf["backend_conf"]["fs_private"], 'URI_aliases.json')
            if os.path.exists(uri_alias_file):
                with open(uri_alias_file, 'r') as data_json:
                    uri_aliasDB = json.load(data_json)
                    data_json.close()
            else:
                logger.error(f"alias file {uri_alias_file} not found")
                raise Exception 

        except:
            raise Exception

        agentGiven_segments = agent_path.split("/")
        owning_agent_id = aggregation_source["@odata.id"].split("/")[-1]
        logger.debug(f"agent id: {owning_agent_id}")
        #  check if owning_agent has any aliases assigned
        if owning_agent_id in uri_aliasDB["Agents_xref_URIs"]:
            logger.debug(f"xlating Agent path : {agent_path}")
            agentFinal_obj_path = ""
            for i in range(1,len(agentGiven_segments)):
                agentFinal_obj_path=agentFinal_obj_path +"/"+ agentGiven_segments[i]
                # test this path segment
                if agentFinal_obj_path in uri_aliasDB["Agents_xref_URIs"][owning_agent_id]["aliases"]:
                    # need to replace agent_path built to this point with sunfish alias
                    sunfishAliasPath = uri_aliasDB["Agents_xref_URIs"][owning_agent_id] \
                                    ["aliases"][agentFinal_obj_path]
                    agentFinal_obj_path = sunfishAliasPath
                    logger.debug(f"aliased path is {agentFinal_obj_path}")
                # next segment
            agent_path = agentFinal_obj_path
        return agent_path

    def updateAllAliasedLinks(self,aggregation_source):
        try:
            uri_alias_file = os.path.join(os.getcwd(), self.conf["backend_conf"]["fs_private"], 'URI_aliases.json')
            if os.path.exists(uri_alias_file):
                with open(uri_alias_file, 'r') as data_json:
                    uri_aliasDB = json.load(data_json)
                    data_json.close()
            else:
                logger.error(f"alias file {uri_alias_file} not found")
                raise Exception 

        except:
            raise Exception

        
        owning_agent_id = aggregation_source["@odata.id"].split("/")[-1]
        logger.debug(f"updating all objects for : {owning_agent_id}")

        agent_uploads=[]
        # for every aggregation_source with aliased links:
        if owning_agent_id in uri_aliasDB['Agents_xref_URIs']:
            # grab the k,v aliases structure and the list of URIs for owned objects
            if 'aliases' in uri_aliasDB['Agents_xref_URIs'][owning_agent_id]:
                agent_aliases = uri_aliasDB['Agents_xref_URIs'][owning_agent_id]['aliases']
                agent_uploads = aggregation_source["Links"]["ResourcesAccessed"] 

            #  update all the objects
            for upload_obj_URI in agent_uploads:
                logger.debug(f"updating links in obj: {upload_obj_URI}")
                RedfishEventHandler.updateObjectAliasedLinks(self, upload_obj_URI, agent_aliases)

        return   

    def updateObjectAliasedLinks(self, object_URI, agent_aliases):

        def findNestedURIs(self, URI_to_match, URI_to_sub, obj, path_to_nested_URI):
            #pdb.set_trace()
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
                            logger.info(f"modifying {value} to {URI_to_sub}")
                            obj[key] = URI_to_sub
                            nestedPaths.append(path_to_nested_URI)
                    elif key != "Sunfish_RM" and (type(value) == list or type(value) == dict):
                        nestedPaths.extend(findNestedURIs(self, URI_to_match, URI_to_sub, value, path_to_nested_URI+"["+key+"]" ))
            return nestedPaths

        try:
            sunfish_obj = self.storage_backend.read( object_URI)
            obj_type = redfish_obj["@odata.type"].split('.')[0]
            obj_type = obj_type.split("/")[-1]
            obj_type = obj_type.replace("#","") # #Évent -> Event 
            # should not do aliasing on the members of a Collection
            # since the members list should contain both original and aliased URIs
            if "Collection" not in obj_type :
                aliasedNestedPaths=[]
                obj_modified = False
                for agent_URI, sunfish_URI in agent_aliases.items():
                    # find all the references to the aliased agent_URI and replace it
                    path_to_nested_URI=""
                    aliasedNestedPaths= findNestedURIs(self, agent_URI, sunfish_URI, sunfish_obj, path_to_nested_URI )
                    if aliasedNestedPaths:
                        obj_modified = True
                if obj_modified:
                    logger.info(json.dumps(sunfish_obj, indent=2))
                    self.storage_backend.replace(sunfish_obj)

        except:
            logger.error(f"could not update links in object {object_URI}")

    def updateAllAgentsRedirectedLinks(self ):
        # after renaming all links, need to redirect the placeholder links
        # will eventually replace file read & load of aliasDB with aliasDB passed in as arg
        try:
            uri_alias_file = os.path.join(os.getcwd(), self.conf["backend_conf"]["fs_private"], 'URI_aliases.json')
            if os.path.exists(uri_alias_file):
                with open(uri_alias_file, 'r') as data_json:
                    uri_aliasDB = json.load(data_json)
                    data_json.close()
            else:
                logger.error(f"alias file {uri_alias_file} not found")
                raise Exception 

        except:
            raise Exception


        modified_aliasDB = False
        for owning_agent_id in uri_aliasDB['Agents_xref_URIs']:
            logger.debug(f"redirecting placeholder links in all boundary ports for : {owning_agent_id}")
            if owning_agent_id in uri_aliasDB['Agents_xref_URIs']:
                if 'boundaryPorts' in uri_aliasDB['Agents_xref_URIs'][owning_agent_id]:
                    for agent_bp_URI in uri_aliasDB['Agents_xref_URIs'][owning_agent_id]['boundaryPorts']:
                        agent_bp_obj = self.storage_backend.read(agent_bp_URI)
                        logger.debug(f"------ redirecting links for {agent_bp_URI}")
                        # check PortType
                        if "PortType" in agent_bp_obj and agent_bp_obj["PortType"] == "InterswitchPort":
                            # We are assuming if one end of link is ISL, both must be
                            if "PeerPortURI" in uri_aliasDB['Agents_xref_URIs'][owning_agent_id]['boundaryPorts'][agent_bp_URI]:
                                RedfishEventHandler.redirectInterswitchLinks(self,owning_agent_id, agent_bp_obj,uri_aliasDB)
                                modified_aliasDB = True
                                # need to replace the update object and re-save the uri_aliasDB
                                self.storage_backend.replace(agent_bp_obj)
                            else:
                                logger.info(f"------ PeerPortURI NOT found")
                                pass

                        elif "PortType" in agent_bp_obj and (agent_bp_obj["PortType"] == "UpstreamPort" ):
                            if "PeerPortURI" in uri_aliasDB['Agents_xref_URIs'][owning_agent_id]['boundaryPorts'][agent_bp_URI]:
                                RedfishEventHandler.redirectUpstreamPortLinks(self,owning_agent_id, agent_bp_obj,uri_aliasDB)
                                modified_aliasDB = True
                                # need to replace the update object and re-save the uri_aliasDB
                                self.storage_backend.replace(agent_bp_obj)
                            else:
                                logger.info(f"------ PeerPortURI NOT found")
                                pass

                        elif "PortType" in agent_bp_obj and (agent_bp_obj["PortType"] == "DownstreamPort" ):
                            if "PeerPortURI" in uri_aliasDB['Agents_xref_URIs'][owning_agent_id]['boundaryPorts'][agent_bp_URI]:
                                RedfishEventHandler.redirectDownstreamPortLinks(self,owning_agent_id, agent_bp_obj,uri_aliasDB)
                                modified_aliasDB = True
                                # need to replace the update object and re-save the uri_aliasDB
                                self.storage_backend.replace(agent_bp_obj)
                            else:
                                logger.info(f"------ PeerPortURI NOT found")
                                pass
                        


        if modified_aliasDB:
            with open(uri_alias_file,'w') as data_json:
                json.dump(uri_aliasDB, data_json, indent=4, sort_keys=True)
                data_json.close()
        return 


    def redirectInterswitchLinks(self,owning_agent_id, agent_bp_obj,uri_aliasDB):


        logger.info(f"redirecting Interswitch ConnectedSwitches and ConnectedSwitchPorts")

        agent_bp_URI = agent_bp_obj["@odata.id"]
        redirected_CSP = uri_aliasDB['Agents_xref_URIs'][owning_agent_id]\
              ['boundaryPorts'][agent_bp_URI]["PeerPortURI"]
        switch_uri_segments = redirected_CSP.split("/")[0:-2]
        redirected_switch_link=""
        for i in range(1,len(switch_uri_segments)):
            redirected_switch_link = redirected_switch_link +"/" + switch_uri_segments[i] 
        logger.debug(f"------ redirected_switch_link is {redirected_switch_link}")

        if "Links" not in agent_bp_obj:
            agent_bp_obj["Links"] = {}
        if "ConnectedSwitchPorts" not in agent_bp_obj["Links"]:
            agent_bp_obj["Links"]["ConnectedSwitchPorts"]=[]
        if "ConnectedSwitches" not in agent_bp_obj["Links"]:
            agent_bp_obj["Links"]["ConnectedSwitches"]=[]
        if len(agent_bp_obj["Links"]["ConnectedSwitchPorts"]) >1:
                logger.error(f"Interswitch Link claims >1 ConnectedSwitchPorts")
        else: 
            if agent_bp_obj["Links"]["ConnectedSwitchPorts"]:
                agent_placeholder_CSP = agent_bp_obj["Links"]["ConnectedSwitchPorts"][0]["@odata.id"]
                agent_bp_obj["Links"]["ConnectedSwitchPorts"][0]["@odata.id"] = redirected_CSP
                logger.info(f"redirected {agent_placeholder_CSP} to \n------ {redirected_CSP}")
                # save the original agent placeholder in the uri_aliasDB
                uri_aliasDB['Agents_xref_URIs'][owning_agent_id]\
                    ['boundaryPorts'][agent_bp_URI]["AgentPeerPortURI"] = agent_placeholder_CSP
            else: # no placeholder links in ConnectedSwitchPorts array
                agent_bp_obj["Links"]["ConnectedSwitchPorts"].append({"@odata.id":redirected_CSP})
                logger.info(f"created ConnectedSwitchPort to {redirected_CSP}")


        if len(agent_bp_obj["Links"]["ConnectedSwitches"]) >1:
            logger.error(f"Interswitch Link claims >1 ConnectedSwitches")
        else:
            if agent_bp_obj["Links"]["ConnectedSwitches"]:
                agent_placeholder_switch_link = agent_bp_obj["Links"]["ConnectedSwitches"][0]["@odata.id"]
                agent_bp_obj["Links"]["ConnectedSwitches"][0]["@odata.id"] = redirected_switch_link
                logger.info(f"redirected {agent_placeholder_switch_link} to \n------ {redirected_switch_link}")
                # save the original agent placeholder in the uri_aliasDB
                uri_aliasDB['Agents_xref_URIs'][owning_agent_id]\
                    ['boundaryPorts'][agent_bp_URI]["AgentPeerSwitchURI"] = agent_placeholder_switch_link
            else: # no placeholder links in ConnectedSwitches array
                agent_bp_obj["Links"]["ConnectedSwitches"].append({"@odata.id":redirected_switch_link})
                logger.info(f"created ConnectedSwitches to {redirected_switch_link}")


    def redirectUpstreamPortLinks(self,owning_agent_id, agent_bp_obj,uri_aliasDB):

        logger.info(f"redirecting UpstreamPort AssociatedEndpoints and ConnectedPorts")

        agent_bp_URI = agent_bp_obj["@odata.id"]
        redirected_CP = uri_aliasDB['Agents_xref_URIs'][owning_agent_id]\
              ['boundaryPorts'][agent_bp_URI]["PeerPortURI"]
        # find the parent (assumed to be a host) obj of this peer port
        host_uri_segments = redirected_CP.split("/")[0:-2]
        host_link=""
        for i in range(1,len(host_uri_segments)):
            host_link = host_link +"/" + host_uri_segments[i] 
        logger.debug(f"host_link is {host_link}")

        # extract the Endpoint URI associated with this parent object
        host_obj = self.storage_backend.read(host_link)
        redirected_endpoint = host_obj["Links"]["Endpoints"][0]["@odata.id"]

        if "Links" not in agent_bp_obj:
            agent_bp_obj["Links"] = {}
        if "ConnectedPorts" not in agent_bp_obj["Links"]:
            agent_bp_obj["Links"]["ConnectedPorts"]=[]
        if "AssociatedEndpoints" not in agent_bp_obj["Links"]:
            agent_bp_obj["Links"]["AssociatedEndpoints"]=[]

        if len(agent_bp_obj["Links"]["ConnectedPorts"]) >1:
                logger.error(f"UpstreamPort Link claims >1 ConnectedPorts")
        else: 
            if agent_bp_obj["Links"]["ConnectedPorts"]:
                agent_placeholder_CP = agent_bp_obj["Links"]["ConnectedPorts"][0]["@odata.id"]
                agent_bp_obj["Links"]["ConnectedPorts"][0]["@odata.id"] = redirected_CP
                logger.info(f"redirected {agent_placeholder_CP} to \n------ {redirected_CP}")
                # save the original agent placeholder in the uri_aliasDB
                uri_aliasDB['Agents_xref_URIs'][owning_agent_id]\
                    ['boundaryPorts'][agent_bp_URI]["AgentPeerPortURI"] = agent_placeholder_CP
            else: # no placeholder links in ConnectedSwitchPorts array
                agent_bp_obj["Links"]["ConnectedPorts"].append({"@odata.id":redirected_CP})
                logger.info(f"created ConnectedPorts to {redirected_CP}")


        if len(agent_bp_obj["Links"]["AssociatedEndpoints"]) >1:
            logger.error(f"UpstreamPort Link claims >1 AssociatedEndpoints")
        else:
            if agent_bp_obj["Links"]["AssociatedEndpoints"]:
                agent_placeholder_endpoint = agent_bp_obj["Links"]["AssociatedEndpoints"][0]["@odata.id"]
                agent_bp_obj["Links"]["AssociatedEndpoints"][0]["@odata.id"] = redirected_endpoint
                logger.info(f"redirected {agent_placeholder_endpoint} to \n------ {redirected_endpoint}")
                # save the original agent placeholder in the uri_aliasDB
                uri_aliasDB['Agents_xref_URIs'][owning_agent_id]\
                    ['boundaryPorts'][agent_bp_URI]["AgentPeerEndpointURI"] = agent_placeholder_endpoint
            else: # no placeholder links in AssociatedEndpoints array
                agent_bp_obj["Links"]["AssociatedEndpoints"].append({"@odata.id":redirected_endpoint})
                logger.info(f"created AssociatedEndpoints to {redirected_endpoint}")

    def redirectDownstreamPortLinks(self,owning_agent_id, agent_bp_obj,uri_aliasDB):

        logger.info(f"redirecting Downstream ConnectedSwitches and ConnectedSwitchPorts")

        agent_bp_URI = agent_bp_obj["@odata.id"]
        redirected_CSP = uri_aliasDB['Agents_xref_URIs'][owning_agent_id]\
              ['boundaryPorts'][agent_bp_URI]["PeerPortURI"]
        switch_uri_segments = redirected_CSP.split("/")[0:-2]
        redirected_switch_link=""
        for i in range(1,len(switch_uri_segments)):
            redirected_switch_link = redirected_switch_link +"/" + switch_uri_segments[i] 
        logger.info(f"------ redirected_switch_link is {redirected_switch_link}")

        if "Links" not in agent_bp_obj:
            agent_bp_obj["Links"] = {}
        if "ConnectedSwitchPorts" not in agent_bp_obj["Links"]:
            agent_bp_obj["Links"]["ConnectedSwitchPorts"]=[]
        if "ConnectedSwitches" not in agent_bp_obj["Links"]:
            agent_bp_obj["Links"]["ConnectedSwitches"]=[]
        if len(agent_bp_obj["Links"]["ConnectedSwitchPorts"]) >1:
                logger.error(f"Downstream Link claims >1 ConnectedSwitchPorts")
        else: 
            if agent_bp_obj["Links"]["ConnectedSwitchPorts"]:
                agent_placeholder_CSP = agent_bp_obj["Links"]["ConnectedSwitchPorts"][0]["@odata.id"]
                agent_bp_obj["Links"]["ConnectedSwitchPorts"][0]["@odata.id"] = redirected_CSP
                logger.info(f"redirected {agent_placeholder_CSP} to \n------ {redirected_CSP}")
                # save the original agent placeholder in the uri_aliasDB
                uri_aliasDB['Agents_xref_URIs'][owning_agent_id]\
                    ['boundaryPorts'][agent_bp_URI]["AgentPeerPortURI"] = agent_placeholder_CSP
            else: # no placeholder links in ConnectedSwitchPorts array
                agent_bp_obj["Links"]["ConnectedSwitchPorts"].append({"@odata.id":redirected_CSP})
                logger.info(f"created ConnectedSwitchPort to {redirected_CSP}")


        if len(agent_bp_obj["Links"]["ConnectedSwitches"]) >1:
            logger.error(f"Downstream Link claims >1 ConnectedSwitches")
        else:
            if agent_bp_obj["Links"]["ConnectedSwitches"]:
                agent_placeholder_switch_link = agent_bp_obj["Links"]["ConnectedSwitches"][0]["@odata.id"]
                agent_bp_obj["Links"]["ConnectedSwitches"][0]["@odata.id"] = redirected_switch_link
                logger.info(f"redirected {agent_placeholder_switch_link} to \n------ {redirected_switch_link}")
                # save the original agent placeholder in the uri_aliasDB
                uri_aliasDB['Agents_xref_URIs'][owning_agent_id]\
                    ['boundaryPorts'][agent_bp_URI]["AgentPeerSwitchURI"] = agent_placeholder_switch_link
            else: # no placeholder links in ConnectedSwitches array
                agent_bp_obj["Links"]["ConnectedSwitches"].append({"@odata.id":redirected_switch_link})
                logger.info(f"created ConnectedSwitches to {redirected_switch_link}")

        

    def updateSunfishAliasDB(self,sunfish_URI, agent_URI, aggregation_source):
        try:
            uri_alias_file = os.path.join(os.getcwd(), self.conf["backend_conf"]["fs_private"], 'URI_aliases.json')
            if os.path.exists(uri_alias_file):
                with open(uri_alias_file, 'r') as data_json:
                    uri_aliasDB = json.load(data_json)
                    data_json.close()
            else:
                logger.error(f"alias file {uri_alias_file} not found")
                raise Exception 

        except:
            raise Exception

        owning_agent_id = aggregation_source["@odata.id"].split("/")[-1]
        logger.debug(f"updating aliases for : {owning_agent_id}")
        if owning_agent_id not in uri_aliasDB["Agents_xref_URIs"]:
            uri_aliasDB["Agents_xref_URIs"][owning_agent_id] = {}
            uri_aliasDB["Agents_xref_URIs"][owning_agent_id]["aliases"] = {}
            uri_aliasDB["Agents_xref_URIs"][owning_agent_id]["aliases"][agent_URI]=sunfish_URI 
        else:
            uri_aliasDB["Agents_xref_URIs"][owning_agent_id]["aliases"][agent_URI]=sunfish_URI 

        if sunfish_URI not in uri_aliasDB["Sunfish_xref_URIs"]["aliases"]:
            uri_aliasDB["Sunfish_xref_URIs"]["aliases"][sunfish_URI] = []
            uri_aliasDB["Sunfish_xref_URIs"]["aliases"][sunfish_URI].append(agent_URI)
        else:
            uri_aliasDB["Sunfish_xref_URIs"]["aliases"][sunfish_URI].append(agent_URI)

        # now need to write aliasDB back to file
        with open(uri_alias_file,'w') as data_json:
            json.dump(uri_aliasDB, data_json, indent=4, sort_keys=True)
            data_json.close()

        return uri_aliasDB

    def updateIfMergedFabrics(self,redfish_obj, uploading_agent_uri, sunfish_obj ):
        # both objects must be Fabric objects
        # both objects must have Sunfish_RM property
        logger.info(f"----- merged fabric processed")
        did_a_merge = True
        # update sunfish_obj with agent_uri of redfish_obj as a sharer
        new_obj_owner={"@odata.id":uploading_agent_uri}

        if "FabricSharedWith" in sunfish_obj["Oem"]["Sunfish_RM"]:
            sunfish_obj["Oem"]["Sunfish_RM"]["FabricSharedWith"].append(new_obj_owner)
        else:
            sunfish_obj["Oem"]["Sunfish_RM"]["FabricSharedWith"] = []
            sunfish_obj["Oem"]["Sunfish_RM"]["FabricSharedWith"].append(new_obj_owner)
        logger.debug(f"sunfish merged fabric object: {json.dumps(sunfish_obj,indent=2)}")
        
        return did_a_merge

    def checkForAliasedFabrics(self, redfish_obj, aggregation_source):
        found_an_aliased_fabric = False
        obj_type = redfish_obj["@odata.type"].split('.')[0]
        obj_type = obj_type.replace("#","") # #Évent -> Event 
        if obj_type == "Fabric":
            # TODO:
            # check all existing Fabrics
            # look for Fabric UUID in existing Fabrics
            # compare UUIDs
            if "UUID" in redfish_obj and "UUID" in sunfish_obj:
                if redfish_obj['UUID'] == sunfish_obj['UUID']:
                    did_a_merge = True
                    # update both redfish_obj and sunfish_obj with Fabric xref in Sunfish_RM 
                    new_obj_fabric_xref={"@odata.id":sunfish_obj["@odata.id"]}
                    existing_obj_fabric_xref={"@odata.id":redfish_obj["@odata.id"]}
                    if "MergedFabrics" in redfish_obj["Oem"]["Sunfish_RM"]:
                        redfish_obj["Oem"]["Sunfish_RM"]["MergedFabrics"].append(new_obj_fabric_xref)
                    else:
                        redfish_obj["Oem"]["Sunfish_RM"]["MergedFabrics"] = []
                        redfish_obj["Oem"]["Sunfish_RM"]["MergedFabrics"].append(new_obj_fabric_xref)

                    if "MergedFabrics" in sunfish_obj["Oem"]["Sunfish_RM"]:
                        sunfish_obj["Oem"]["Sunfish_RM"]["MergedFabrics"].append(existing_obj_fabric_xref)
                    else:
                        sunfish_obj["Oem"]["Sunfish_RM"]["MergedFabrics"] = []
                        sunfish_obj["Oem"]["Sunfish_RM"]["MergedFabrics"].append(existing_obj_fabric_xref)
                    logger.debug(f"sunfish merged fabric object: {json.dumps(sunfish_obj,indent=2)}")

                else:
                    logger.debug(f"----- not same fabrics")
        
        return found_an_aliased_fabric

    def renameUploadedObject(self,redfish_obj, aggregation_source):
        # redfish_obj uses agent namespace
        # aggregation_source is an object in the Sunfish namespace
        # this routine ONLY renames the @Odata.id and "id"
        try:
            uri_alias_file = os.path.join(os.getcwd(), self.conf["backend_conf"]["fs_private"], 'URI_aliases.json')
            if os.path.exists(uri_alias_file):
                with open(uri_alias_file, 'r') as data_json:
                    uri_aliasDB = json.load(data_json)
                    data_json.close()
            else:
                logger.error(f"alias file {uri_alias_file} not found")
                raise Exception 

        except:
            raise Exception

        agentGiven_obj_path = redfish_obj['@odata.id']
        agentGiven_segments = agentGiven_obj_path.split("/")
        agentGiven_obj_name = agentGiven_segments[-1]
        owning_agent_id = aggregation_source["@odata.id"].split("/")[-1]
        # generate a new path and object name 
        logger.debug(f"renaming object: {agentGiven_obj_path}")
        logger.debug(f"agent id: {owning_agent_id}")
        sunfishGiven_obj_name = "Sunfish_"+owning_agent_id[:4]+"_"+agentGiven_obj_name
        sunfishGiven_obj_path = "/"
        for i in range(1,len(agentGiven_segments)-1):
            sunfishGiven_obj_path=sunfishGiven_obj_path + agentGiven_segments[i]+"/"
        sunfishGiven_obj_path=sunfishGiven_obj_path + sunfishGiven_obj_name
        # need to check new name is also unused 
        if sunfishGiven_obj_path in uri_aliasDB["Sunfish_xref_URIs"]["aliases"]:
            # new name was still not unique, just brute force it!
            temp_string = "Sunfish_"+owning_agent_id+"_"+agentGiven_obj_name
            sunfishGiven_obj_path=sunfishGiven_obj_path.replace(sunfishGiven_obj_name,temp_string) 

        #
        logger.debug(sunfishGiven_obj_path)
        redfish_obj['@odata.id'] = sunfishGiven_obj_path
        if redfish_obj['Id'] == agentGiven_obj_name:
            redfish_obj['Id'] = sunfishGiven_obj_name
        # now need to update aliasDB
        if owning_agent_id not in uri_aliasDB["Agents_xref_URIs"]:
            uri_aliasDB["Agents_xref_URIs"][owning_agent_id] = {}
            uri_aliasDB["Agents_xref_URIs"][owning_agent_id]["aliases"] = {}
            uri_aliasDB["Agents_xref_URIs"][owning_agent_id]["aliases"][agentGiven_obj_path]=sunfishGiven_obj_path 
        else:
            uri_aliasDB["Agents_xref_URIs"][owning_agent_id]["aliases"][agentGiven_obj_path]=sunfishGiven_obj_path 

        if sunfishGiven_obj_path not in uri_aliasDB["Sunfish_xref_URIs"]["aliases"]:
            uri_aliasDB["Sunfish_xref_URIs"]["aliases"][sunfishGiven_obj_path] = []
            uri_aliasDB["Sunfish_xref_URIs"]["aliases"][sunfishGiven_obj_path].append(agentGiven_obj_path)
        else:
            uri_aliasDB["Sunfish_xref_URIs"]["aliases"][sunfishGiven_obj_path].append(agentGiven_obj_path)

        # now need to write aliasDB back to file
        with open(uri_alias_file,'w') as data_json:
            json.dump(uri_aliasDB, data_json, indent=4, sort_keys=True)
            data_json.close()

        return redfish_obj


    def match_boundary_port(self, searching_agent_id, searching_port_URI, URI_aliasDB):
        
        matching_port_URIs = []
        # pull up the link partner dict for this agent.Port 
        searching_for = URI_aliasDB['Agents_xref_URIs'][searching_agent_id]\
                ['boundaryPorts'][searching_port_URI]

        if "RemoteLinkPartnerId" in searching_for:
            searching_for_remote_partnerId =searching_for["RemoteLinkPartnerId"]
        else:
            searching_for_remote_partnerId = 'No remote partnerId' # do NOT use 'None' or ""
        if "RemotePortId" in searching_for:
            searching_for_remote_portId =searching_for["RemotePortId"]
        else:
            searching_for_remote_portId = 'No remote portId' # do NOT use 'None' or ""
        if "LocalLinkPartnerId" in searching_for:
            searching_for_local_partnerId =searching_for["LocalLinkPartnerId"]
        else:
            searching_for_local_partnerId = 'No local partnerId' # do NOT use 'None' or ""
        if "LocalPortId" in searching_for:
            searching_for_local_portId =searching_for["LocalPortId"]
        else:
            searching_for_local_portId = 'No local portId' # do NOT use 'None' or ""

        logger.info(f"searching for match to {searching_port_URI}")
        for agent_id, agent_db in URI_aliasDB['Agents_xref_URIs'].items():
            if agent_id != searching_agent_id and 'boundaryPorts' in agent_db:
                for port_URI, port_details in agent_db['boundaryPorts'].items():
                    # always check if the remote port device ID is found first
                    if ("LocalLinkPartnerId" in port_details) and \
                        (port_details["LocalLinkPartnerId"] == searching_for_remote_partnerId) and \
                        ("LocalPortId" in port_details) and \
                        (port_details["LocalPortId"] == searching_for_remote_portId):
                        matching_port_URIs.append(port_URI)
                        # cross reference BOTH agents' boundaryPorts
                        logger.info(f"----- found a matching port {port_URI}")
                        URI_aliasDB['Agents_xref_URIs'][agent_id]['boundaryPorts']\
                            [port_URI]['PeerPortURI'] = searching_port_URI
                        URI_aliasDB['Agents_xref_URIs'][searching_agent_id]['boundaryPorts']\
                            [searching_port_URI]['PeerPortURI'] = port_URI
                    # only check if the local port device ID is being waited on if first check fails
                    else:
                        if ("RemoteLinkPartnerId" in port_details) and \
                            (port_details["RemoteLinkPartnerId"] == searching_for_local_partnerId) and \
                            ("RemotePortId" in port_details) and \
                            (port_details["RemotePortId"] == searching_for_local_portId):
                            matching_port_URIs.append(port_URI)
                            # cross reference BOTH agent's boundaryPorts
                            logger.info(f"----- found a matching port {port_URI}")
                            URI_aliasDB['Agents_xref_URIs'][agent_id]['boundaryPorts']\
                                [port_URI]['PeerPortURI'] = searching_port_URI
                            URI_aliasDB['Agents_xref_URIs'][searching_agent_id]['boundaryPorts']\
                                [searching_port_URI]['PeerPortURI'] = port_URI


        logger.debug(f"matching_ports {matching_port_URIs}")
        return matching_port_URIs



    def track_boundary_port(self, redfish_obj, aggregation_source):

        agent_alias_dict = {
            "aliases":{},
            "boundaryPorts":{}
            }

        try:
            uri_alias_file = os.path.join(os.getcwd(), self.conf["backend_conf"]["fs_private"], 'URI_aliases.json')
            if os.path.exists(uri_alias_file):
                with open(uri_alias_file, 'r') as data_json:
                    uri_aliasDB = json.load(data_json)
                    data_json.close()
            else:
                logger.error(f"alias file {uri_alias_file} not found")
                raise Exception 

        except:
            raise Exception


        logger.info(f"---- now processing a boundary port")
        obj_type = redfish_obj["@odata.type"].split(".")[0]
        obj_type = obj_type.replace("#","")
        save_alias_file = False 
        port_protocol = redfish_obj["PortProtocol"]
        port_type = redfish_obj["PortType"]
        port_bc_flag = redfish_obj["Oem"]["Sunfish_RM"]["BoundaryComponent"]
        if obj_type == "Port" and port_bc_flag == "BoundaryPort":
            owning_agent_id = aggregation_source["@odata.id"].split("/")[-1]
            localPortURI = redfish_obj['@odata.id']
            if port_protocol=="CXL" and (port_type == "InterswitchPort" or \
                    port_type== "UpstreamPort" or port_type== "DownstreamPort"):
                # create a boundPort entry in uri_aliasDB
                if owning_agent_id not in uri_aliasDB["Agents_xref_URIs"]:
                    uri_aliasDB["Agents_xref_URIs"][owning_agent_id] = agent_alias_dict
                    uri_aliasDB["Agents_xref_URIs"][owning_agent_id]["boundaryPorts"][localPortURI]={} 
                elif "boundaryPorts" not in uri_aliasDB["Agents_xref_URIs"][owning_agent_id]:
                    uri_aliasDB["Agents_xref_URIs"][owning_agent_id]["boundaryPorts"] = {}
                    uri_aliasDB["Agents_xref_URIs"][owning_agent_id]["boundaryPorts"][localPortURI] = {}

                #  log what the fabric port reports its own PortId and its own LinkPartnerId
                if "CXL" in redfish_obj and "LinkPartnerTransmit" in redfish_obj["CXL"]: # rely on 'and' short circuiting
                    local_link_partner_id = redfish_obj["CXL"]["LinkPartnerTransmit"]["LinkPartnerId"]
                    local_port_id = redfish_obj["CXL"]["LinkPartnerTransmit"]["PortId"]
                    if localPortURI not in uri_aliasDB["Agents_xref_URIs"][owning_agent_id]["boundaryPorts"]:
                        uri_aliasDB["Agents_xref_URIs"][owning_agent_id]["boundaryPorts"][localPortURI] = {}
                    uri_aliasDB["Agents_xref_URIs"][owning_agent_id]["boundaryPorts"][localPortURI]\
                                ["LocalLinkPartnerId"] = local_link_partner_id
                    uri_aliasDB["Agents_xref_URIs"][owning_agent_id]["boundaryPorts"][localPortURI]\
                                ["LocalPortId"] =  local_port_id

                #  log if the fabric port reports its received LinkPartnerInfo from other end
                if "CXL" in redfish_obj and "LinkPartnerReceive" in redfish_obj["CXL"]: # rely on 'and' short circuiting
                    remote_link_partner_id = redfish_obj["CXL"]["LinkPartnerReceive"]["LinkPartnerId"]
                    remote_port_id = redfish_obj["CXL"]["LinkPartnerReceive"]["PortId"]
                    logger.debug(f"---- obj link_partner_id {remote_link_partner_id}")
                    if localPortURI not in uri_aliasDB["Agents_xref_URIs"][owning_agent_id]["boundaryPorts"]:
                        uri_aliasDB["Agents_xref_URIs"][owning_agent_id]["boundaryPorts"][localPortURI] = {}
                    uri_aliasDB["Agents_xref_URIs"][owning_agent_id]["boundaryPorts"][localPortURI]\
                                ["RemoteLinkPartnerId"] =remote_link_partner_id
                    uri_aliasDB["Agents_xref_URIs"][owning_agent_id]["boundaryPorts"][localPortURI]\
                                ["RemotePortId"] = remote_port_id
                    
                # now need to write aliasDB back to file
                save_alias_file = True
                with open(uri_alias_file,'w') as data_json:
                    json.dump(uri_aliasDB, data_json, indent=4, sort_keys=True)
                    data_json.close()
            else:  
                logger.debug(f"---- CXL BoundaryPort found, but not InterswitchPort, UpstreamPort, or DownstreamPort")
                pass
        matching_ports = RedfishEventHandler.match_boundary_port(self, owning_agent_id, localPortURI, uri_aliasDB)
        if matching_ports or save_alias_file:
            with open(uri_alias_file,'w') as data_json:
                json.dump(uri_aliasDB, data_json, indent=4, sort_keys=True)
                data_json.close()
        logger.debug(f"----- boundary ports matched {matching_ports}")
        return
                    


def add_aggregation_source_reference(redfish_obj, aggregation_source):
    #  BoundaryComponent = ["owned", "foreign", "BoundaryLink","unknown"]
    oem = {
        "@odata.type": "#SunfishExtensions.v1_0_0.ResourceExtensions",
        "ManagingAgent": {
            "@odata.id": aggregation_source["@odata.id"]
        },
        "BoundaryComponent": "owned"
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

