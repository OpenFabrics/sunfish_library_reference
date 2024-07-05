# Copyright IBM Corp. 2023
# This software is available to you under a BSD 3-Clause License. 
# The full license terms are available here: https://github.com/OpenFabrics/sunfish_library_reference/blob/main/LICENSE

import json
import os
import string

from sunfish.events.subscription_handler_interface import SubscriptionHandlerInterface
from sunfish.lib.exceptions import *

# Missing:
## EventType not handle because Event is considered as the only value for the property
## Actions
## DeliveryRetryPolicy
## Heartbeat events
## IncludeOriginOfCondition

subscriptions = {
    "RegistryPrefixes": {
        # "RegistryPrefix": {
        # "to_send": [ ],
        # "exclude": [ ]
        # }, ...
    },
    "MessageIds": {
        # "ResourceEvent": {
        # "to_send": [ ],
        # "exclude": [ ]
        # }, ...
    },
    "ResourceTypes": {
        # "Type": [
        #    "id_1",
        #    "id_n"
        # ], ...
    },
    #  if "SubordinateResources": true -> save OriginResource with /* at the end
    "OriginResources": {
        # "OriginResource": [
        #    "id_1",
        #    "id_n"
        # ], ...
    }
}


class RedfishSubscriptionHandler(SubscriptionHandlerInterface):

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
        self.load_subscriptions()

    # Loads the subscriptions already stored
    def load_subscriptions(self):
        path = os.path.join(os.getcwd(), self.fs_root, self.subscribers_root)
        if not os.path.exists(path):
            return
        dirs = os.listdir(path)
        for sub in dirs:
            sub_path = ''
            if os.path.isdir(os.path.join(path, sub)):
                try:
                    sub_path = os.path.join(path, sub, 'index.json')
                    json_data = open(sub_path)
                    data: json = json.load(json_data)
                    self.new_subscription(data)
                except FileNotFoundError as e:
                    raise ResourceNotFound(sub_path)
        return

    def new_subscription(self, payload: dict):
        # check if sub has colliding properties
        if self.validate_subscription(payload) is False:
            raise IllegalSubscription

        if "RegistryPrefixes" in payload:
            for prefix in payload["RegistryPrefixes"]:
                if prefix in subscriptions["RegistryPrefixes"]:
                    subscriptions["RegistryPrefixes"][prefix]["to_send"].append(payload["Id"])
                else:
                    subscriptions["RegistryPrefixes"][prefix] = {
                        "to_send": [payload["Id"]],
                        "exclude": []
                    }

        if "ExcludeRegistryPrefixes" in payload:
            for exclude_prefix in payload["ExcludeRegistryPrefixes"]:
                if exclude_prefix in subscriptions["RegistryPrefixes"]:
                    subscriptions["RegistryPrefixes"][exclude_prefix]["exclude"].append(payload["Id"])
                else:
                    subscriptions["RegistryPrefixes"][exclude_prefix] = {
                        "to_send": [],
                        "exclude": [payload["Id"]]
                    }

        if "MessageIds" in payload:
            for msgId in payload["MessageIds"]:
                if msgId in subscriptions["MessageIds"]:
                    subscriptions["MessageIds"][msgId]["to_send"].append(payload["Id"])
                else:
                    subscriptions["MessageIds"][msgId] = {
                        "to_send": [payload["Id"]],
                        "exclude": []
                    }

        if "ExcludeMessageIds" in payload:
            for exclude_msgId in payload["ExcludeMessageIds"]:
                if exclude_msgId in subscriptions["MessageIds"]:
                    subscriptions["MessageIds"][exclude_msgId]["exclude"].append(payload["Id"])
                else:
                    subscriptions["MessageIds"][exclude_msgId] = {
                        "to_send": [],
                        "exclude": [payload["Id"]]
                    }

        if "OriginResources" in payload:
            for prefix in payload["OriginResources"]:
                origin = prefix["@odata.id"]
                if "SubordinateResources" in payload and payload["SubordinateResources"]:
                    origin = os.path.join(origin, '*')
                if origin in subscriptions["OriginResources"]:
                    subscriptions["OriginResources"][origin].append(payload["Id"])
                else:
                    subscriptions["OriginResources"][origin] = [payload["Id"]]

        if "ResourceTypes" in payload:
            for type in payload["ResourceTypes"]:
                if type in subscriptions["ResourceTypes"]:
                    subscriptions["ResourceTypes"][type].append(payload["Id"])
                else:
                    subscriptions["ResourceTypes"][type] = [payload["Id"]]
        return

    def validate_subscription(self, payload: dict):
        check = True
        # check RegistryPrefixes and ExcludeRegistryPrefixes
        if "RegistryPrefixes" in payload:
            for prefix in payload["RegistryPrefixes"]:
                if "ExcludeRegistryPrefixes" in payload:
                    for exclude_pref in payload["ExcludeRegistryPrefixes"]:
                        if prefix == exclude_pref:
                            check = False
        # check MessageIds and ExcludeMessageIds
        if "MessageIds" in payload:
            for msg_id in payload["MessageIds"]:
                if "ExcludeMessageIds" in payload:
                    for exclude_msg in payload["ExcludeMessageIds"]:
                        if msg_id == exclude_msg:
                            check = False

        # check ExcludeRegistryPrefixes and MessageIds
        if "ExcludeRegistryPrefixes" in payload:
            for exclude_pref in payload["ExcludeRegistryPrefixes"]:
                if "MessageIds" in payload:
                    for msg_id in payload["MessageIds"]:
                        msg_id = msg_id.split('.')[0]
                        if msg_id == exclude_pref:
                            check = False
        return check

    # Deletes from the subscriptions data structure the ID of the subs deleted
    def delete_subscription(self, id):
        for prefix in subscriptions["OriginResources"]:
            if id in subscriptions["OriginResources"][prefix]:
                subscriptions["OriginResources"][prefix].remove(id)
        for prefix in subscriptions["ResourceTypes"]:
            if id in subscriptions["ResourceTypes"][prefix]:
                subscriptions["ResourceTypes"][prefix].remove(id)
        for prefix in subscriptions["RegistryPrefixes"]:
            if id in subscriptions["RegistryPrefixes"][prefix]["to_send"]:
                subscriptions["RegistryPrefixes"][prefix]["to_send"].remove(id)
            if id in subscriptions["RegistryPrefixes"][prefix]["exclude"]:
                subscriptions["RegistryPrefixes"][prefix]["exclude"].remove(id)
        for prefix in subscriptions["MessageIds"]:
            if id in subscriptions["MessageIds"][prefix]["to_send"]:
                subscriptions["MessageIds"][prefix]["to_send"].remove(id)
            if id in subscriptions["MessageIds"][prefix]["exclude"]:
                subscriptions["MessageIds"][prefix]["exclude"].remove(id)
        return
