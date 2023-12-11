# Copyright IBM Corp. 2023
# This software is available to you under a BSD 3-Clause License. 
# The full license terms are available here: https://github.com/OpenFabrics/sunfish_library_reference/blob/main/LICENSE
import os

import requests
from sunfish.events.subscription_handler import subscribtions
from sunfish.lib.exceptions import *

class EventHandler:
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
        for event in payload["Events"]:
            prefix = event["MessageId"].split('.')[0]
            messageId = event["MessageId"]
            origin = 'not_specified'

            to_forward = []
            if "OriginOfCondition" in event:
                origin = event["OriginOfCondition"]["@odata.id"]
                type = self.check_data_type(origin)
                if type in subscribtions["ResourceTypes"]:
                    to_forward.extend(subscribtions["ResourceTypes"][type])
                if origin in subscribtions["OriginResources"]:
                    to_forward.extend(subscribtions["OriginResources"][origin])
                sub = self.check_subdirs(origin)
                to_forward.extend(sub)

            #MemberId
            if prefix in subscribtions["RegistryPrefixes"]:
                for id in subscribtions["RegistryPrefixes"][prefix]["to_send"]:
                        if messageId not in subscribtions["MessageIds"] or messageId in subscribtions["MessageIds"] and not id in subscribtions["MessageIds"][messageId]["exclude"]:
                            to_forward.append(id)
            if prefix in subscribtions["MessageIds"]:
                for id in subscribtions["MessageIds"][payload["MessageId"]]:
                        for x in subscribtions["RegistryPrefixes"][prefix]:
                            if x not in subscribtions["RegistryPrefixes"][prefix]["exclude"]:
                                to_forward.append(id)
        
            ## parameter of forward_event is a set with no duplicates 
            return self.forward_event(list(set(to_forward)), payload)
        
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
        # resp = 400
        
        for id in list:
            path = os.path.join(self.redfish_root, 'EventService', 'Subscriptions', id)
            try:
                data = self.core.get_object(path)
                print('send to: ', data["Id"])
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
        
    def ResourceCreated(self, event):
        pass

    def AggregationSourceDiscovered(self, event):
        pass
