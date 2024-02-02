# Copyright IBM Corp. 2023
# This software is available to you under a BSD 3-Clause License. 
# The full license terms are available here: https://github.com/OpenFabrics/sunfish_library_reference/blob/main/LICENSE
import logging
import os
from uuid import uuid4
import warnings

import requests
from sunfish.events.event_handler_interface import EventHandlerInterface
from sunfish.events.redfish_subscription_handler import subscribtions
from sunfish.lib.exceptions import *

class RedfishEventHandler(EventHandlerInterface):
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

            if prefix in subscribtions["RegistryPrefixes"]:
                for id in subscribtions["RegistryPrefixes"][prefix]["exclude"]:
                    to_exclude.extend(id)
            if messageId in subscribtions["MessageIds"]:
                for id in subscribtions["MessageIds"][messageId]["exclude"]:
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
                if type in subscribtions["ResourceTypes"]:
                    to_forward.extend(subscribtions["ResourceTypes"][type])
                if origin in subscribtions["OriginResources"]:
                    to_forward.extend(subscribtions["OriginResources"][origin])
                sub = self.check_subdirs(origin)
                to_forward.extend(sub)

            if prefix in subscribtions["RegistryPrefixes"]:
                for id in subscribtions["RegistryPrefixes"][prefix]["to_send"]:
                    to_forward.append(id)
            if messageId in subscribtions["MessageIds"]:
                for id in subscribtions["MessageIds"][messageId]["to_send"]:
                    to_forward.append(id)
            
            set1 = set(to_forward)
            set2 = set(to_exclude)
            to_forward = list(set1 - set2)
            
            #MemberId
            # if prefix in subscribtions["RegistryPrefixes"]:
            #     for id in subscribtions["RegistryPrefixes"][prefix]["to_send"]:
            #             if messageId not in subscribtions["MessageIds"] or messageId in subscribtions["MessageIds"] and not id in subscribtions["MessageIds"][messageId]["exclude"]:
            #                 to_forward.append(id)
            # if prefix in subscribtions["MessageIds"]:
            #     for id in subscribtions["MessageIds"][payload["MessageId"]]:
            #             for x in subscribtions["RegistryPrefixes"][prefix]:
            #                 if x not in subscribtions["RegistryPrefixes"][prefix]["exclude"]:
            #                     to_forward.append(id)
        
            ## parameter of forward_event is a set with no duplicates 
            # return self.forward_event(list(set(to_forward)), payload)
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
                requests.post(data['Destination'], json=payload)
            except requests.exceptions.ConnectionError as e:
                list.remove(id)
            except ResourceNotFound:
                raise ResourceNotFound(path)

        # if forwarding status is okay it returns the list of subscribers to whom the event was forwarded
        return list

    def check_subdirs(self, origin):
        keylist = list(subscribtions["OriginResources"].keys())
        to_forward = []
        for el in keylist:
            if '/*' in el:
                base_origin = el.replace("/*", "")
                if base_origin in origin:
                        for id in subscribtions["OriginResources"][el]:
                            to_forward.append(id)
        
        return to_forward
    
    def AggregationSourceDiscovered(self, event,context):
        ###
        # Fabric Agents are modelled as AggregationSource objects (RedFish v2023.1 at the time of writing this comment)
        # Registration will happen with the OFMF receiving a and event with MessageId: AggregationSourceDiscovered
        # The arguments of the event message are:
        #   - Arg1: "Redfish"
        #   - Arg2: "agent_ip:port"
        # I am also assuming that the agent name to be used is contained in the OriginOfCondifiton field of the event as in the below example:
        # {
        #    "OriginOfCondition: [
        #           "@odata.id" : "/redfish/v1/AggregationService/AggregationSource/AgentName"
        #    ]"
        # }
        logging.info("AggregationSourceDiscovered method called")
        
        connectionMethodId = event['OriginOfCondition']['@odata.id'] 
        hostname = event['MessageArgs'][1] # Agent address

        response = requests.get(f"{hostname}/{connectionMethodId}")
        if response.status_code != 200:
            raise Exception("Cannot find ConnectionMethod")
        response = response.json()

        ### Save agent registration
        connection_method_name = connectionMethodId.split('/')[-1]
        connection_method_name = connectionMethodId[:-len(connection_method_name)]
        self.create_object(connection_method_name, response)

        connection_method_template = {
            "@Redfish.Copyright": "Copyright 2014-2021 SNIA. All rights reserved.",
            "@odata.type": "#AggregationSource.v1_2_.AggregationSource",
            "HostName": hostname,
            "Links": {
                "ConnectionMethod": {
                    "@odata.id": connectionMethodId
                },
                "ResourcesAccessed": [ ]
            }
        }

        resp_post = self.create_object(os.path.join(self.conf["redfish_root"], "AggregationService/AggregationSources"), connection_method_template)

        aggregation_source_id = resp_post['@odata.id']
        agent_subscription_context = {"Context": aggregation_source_id.split('/')[-1]}

        resp_patch = requests.patch(f"{hostname}/redfish/v1/EventService/Subscriptions/SunfishServer",
                                    json=agent_subscription_context)

        return resp_patch
    
    def ResourceCreated(self, event, context):
        logging.info("New resource created")

        id = event['OriginOfCondition']['@odata.id'] # /redfish/v1/Fabrics/CXL
        aggregation_source = self.get_object(
            os.path.join(self.conf["redfish_root"], "AggregationService", "AggregationSources", context))
        hostname = aggregation_source["HostName"]

        response = requests.get(f"{hostname}/{id}")
        if response.status_code != 200:
            raise Exception("Cannot find ConnectionMethod")
        object = response.json()
        add_aggregation_source_reference(object,aggregation_source)

        self.create_object(id, object)

        RedfishEventHandler.bfsInspection(self, object, aggregation_source)

        self.patch_object(id,aggregation_source)

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
                logging.info(f"Resource - {id} - not available")
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
            logging.info(f"Checking redfish path: {redfish_path}")
            if redfish_path not in visited:
                need_parent_prefetch = True
                logging.info(f"Inspect redfish path: {redfish_path}")
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
        logging.info(f"fetch: {resource_endpoint}")
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

        file_path = os.path.join(self.conf['redfish_root'], obj_path)
        #file_path = create_path(constants.PATHS['Root'], obj_path)

        if 'Collection' not in redfish_obj['@odata.type']:
            try:
                if self.get_object(file_path) == redfish_obj:
                    pass
                elif self.get_object(file_path) != redfish_obj:
                    warnings.warn('Resource state changed')
            except ResourceNotFound:
                add_aggregation_source_reference(redfish_obj,aggregation_source)
                self.create_object(file_path, redfish_obj)


def add_aggregation_source_reference(redfish_obj,aggregation_source):
    if "Oem" not in redfish_obj:
        redfish_obj["Oem"] = {}
    if "Sunfish_RM" not in redfish_obj["Oem"]:
        oem = {
            "@odata.type": "#SunfishExtensions.v1_0_0.ResourceExtensions",
            "ManagingAgent": {
                "@odata.id": aggregation_source["@odata.id"]
            }
        }
        redfish_obj["Oem"]["Sunfish_RM"] = oem
