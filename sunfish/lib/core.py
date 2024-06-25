# Copyright IBM Corp. 2023
# This software is available to you under a BSD 3-Clause License. 
# The full license terms are available here: https://github.com/OpenFabrics/sunfish_library_reference/blob/main/LICENSE

import os
import string
import uuid
import logging
from typing import Optional

from sunfish.lib.exceptions import CollectionNotSupported, ResourceNotFound, AgentForwardingFailure, PropertyNotFound

from sunfish.events.redfish_subscription_handler import RedfishSubscriptionHandler
from sunfish.models.types import *
from sunfish.lib.agents_management import Agent
import sunfish.models.plugins as plugin_modules
logger = logging.getLogger(__name__)


class Core:

    def __init__(self, conf):
        """init that implements the chosen backend specified in the conf dict.

        Args:
            conf (dict): dictionary where are specified the storage implementation type and the specific backend configuration.
        """

        self.conf = conf

        # The Sunfish core library uses a plugin mechanism that allows dynamic loading of certain classes. This helps
        # users with updating the behavior of the sunfish library without having to modify its core classes.
        # At the moment we support plugins for the storage backend and for the redfish event handlers.
        # Plugins are implemented as namespaced packages and must be placed in a folder at the top of the project named
        # "sunfish_plugins", with subfolders named "storage" and/or "events_handlers" and/or "objects_handlers".
        # The python packages defined inside each subfolder are totally user defined.
        # ── sunfish_plugins
        #    ├── storage
        #    │   └──my_storage_package     <--- User defined
        #    │      ├── __init__.py
        #    │      └── my_storage_backend.py
        #    └── events_handlers
        #    │   └──my_handler_package     <--- User defined
        #    │      ├── __init__.py
        #    │      └── my_handler.py
        #    ├── object_handlers
        #    │   └──my_objects_handler_package     <--- User defined
        #    │      ├── __init__.py
        #    │      └── my_objects_handler.py

        # When initializing the Sunfish libraries can load their storage or event handler plugin by specifying them in
        # the configuration as in the below example:
        #
        # "storage_backend" : {
        #         "module_name": "storage.my_storage_package.my_storage_backend",
        #         "class_name": "StorageBackend"
        # },
        # "event_handler" : {
        #         "module_name": "events_handlers.my_handler_package.my_handler",
        #         "class_name": "StorageBackend"
        # },
        # "objects_handler" : {
        #         "module_name": "objects_handlers.my_objects_handler_package.my_objects_handler",
        #         "class_name": "StorageBackend"
        # },
        #
        # In all cases "class_name" represents the name of the class that is initialized and implements the respective
        # interface.

        # Default storage plugin loaded if nothing is specified in the configuration
        if "storage_backend" not in conf:
            storage_plugin = {
                "module_name": "storage.file_system_backend.backend_FS",
                "class_name": "BackendFS"
            }
        else:
            storage_plugin = conf["storage_backend"]
        storage_cl = plugin_modules.load_plugin(storage_plugin)
        self.storage_backend = storage_cl(self.conf)

        # Default event_handler plugin loaded if nothing is specified in the configuration
        if "events_handler" not in conf:
            event_plugin = {
                "module_name": "events_handlers.redfish.redfish_event_handler",
                "class_name": "RedfishEventHandler"
            }
        else:
            event_plugin = conf["events_handler"]
        event_cl = plugin_modules.load_plugin(event_plugin)
        self.event_handler = event_cl(self)

        # Default objects_handler plugin loaded if nothing is specified in the configuration
        if "objects_handler" not in conf:
            objects_plugin = {
                "module_name": "objects_handlers.sunfish_server.redfish_object_handler",
                "class_name": "RedfishObjectHandler"
            }
        else:
            objects_plugin = conf["objects_handler"]
        objects_handler_cl = plugin_modules.load_plugin(objects_plugin)
        self.objects_handler = objects_handler_cl(self)

        if conf['handlers']['subscription_handler'] == 'redfish':
            self.subscription_handler = RedfishSubscriptionHandler(self)

    def get_object(self, path: string):
        """Calls the correspondent read function from the backend implementation and checks that the path is valid.

        Args:
            path (str): path of the resource. It should comply with Redfish specification.

        Raises:
            InvalidPath: custom exception that is raised if the path is not compliant with the current Redfish specification.

        Returns:
            str|exception: str of the requested resource or an exception in case of fault. 
        """
        try:
            logger.debug(f"Getting object {path}")
            return self.storage_backend.read(path)
        except ResourceNotFound:
            logger.debug(f"The object {path} does not exist")
            raise

    def create_object(self, path: string, payload: dict):
        """Calls the correspondent create function from the backend implementation. 
        Before to call the create function it generates a unique uuid and updates the payload adding Id and @odata.id.
        To distinguish the storage of an element from the storage of an EventDestination (event subscription schema) the property 'Destination' is checked 
        because it belongs only to EventDestination and it is required.
        @odata.type is checked to verify that this is not a try to store a Collection (forbidden)

        Args:
            path: the RedFish path to the collection where the resource is to be created
            payload (resource): resource that we want to store.

        Returns:
            str|exception: return the stored resource or an exception in case of fault.
        """

        # before to add the ID and to call the methods there should be the json validation

        # generate unique uuid if is not present
        if '@odata.id' not in payload and 'Id' not in payload:
            id = str(uuid.uuid4())
            to_add = {
                'Id': id,
                '@odata.id': os.path.join(path, id)
            }
            payload.update(to_add)

        object_type = self._get_type(payload)
        # we assume no changes can be done on collections
        if "Collection" in object_type:
            raise CollectionNotSupported()

        payload_to_write = payload

        try:
            # 1. check the path target of the operation exists
            # self.storage_backend.read(path)
            # 2. is needed first forward the request to the agent managing the object
            agent_response = self.objects_handler.forward_to_manager(SunfishRequestType.CREATE, path, payload=payload)
            if agent_response:
                payload_to_write = agent_response
            # 3. Execute any custom handler for this object type
            self.objects_handler.dispatch(object_type, path, SunfishRequestType.CREATE, payload=payload)
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

    def replace_object(self, path: str, payload: dict):
        """Calls the correspondent replace function from the backend implementation.

        Args:
            payload (resource): resource that we want to replace.

        Returns:
            str|exception: return the replaced resource or an exception in case of fault.
        """
        object_type = self._get_type(payload, path=path)
        # we assume no changes can be done on collections
        if "Collection" in object_type:
            raise CollectionNotSupported()
        try:
            # 1. check the path target of the operation exists
            self.storage_backend.read(path)
            # 2. is needed first forward the request to the agent managing the object
            self.objects_handler.forward_to_manager(SunfishRequestType.REPLACE, path, payload=payload)
            # 3. Execute any custom handler for this object type
            self.objects_handler.dispatch(object_type, path, SunfishRequestType.REPLACE, payload=payload)
        except ResourceNotFound:
            logger.error(logger.error(f"The resource to be replaced ({path}) does not exist."))
        except AttributeError:
            # The object does not have a handler.
            logger.debug(f"The object {object_type} does not have a custom handler")
            pass
        # 4. persist change in Sunfish tree
        return self.storage_backend.replace(payload)

    def patch_object(self, path: str, payload: dict):
        """Calls the correspondent patch function from the backend implementation.

        Args:
            payload (resource): resource that we want to partially update.

        Returns:
            str|exception: return the updated resource or an exception in case of fault.
        """
        # we assume no changes can be done on collections
        obj = self.storage_backend.read(path)
        object_type = self._get_type(obj, path=path)
        if "Collection" in object_type:
            raise CollectionNotSupported()
        try:
            # 1. check the path target of the operation exists
            self.storage_backend.read(path)
            # 2. is needed first forward the request to the agent managing the object
            self.objects_handler.forward_to_manager(SunfishRequestType.PATCH, path, payload=payload)
            # 3. Execute any custom handler for this object type
            self.objects_handler.dispatch(object_type, path, SunfishRequestType.PATCH, payload=payload)
        except ResourceNotFound:
            logger.error(f"The resource to be patched ({path}) does not exist.")
        except AttributeError:
            # The object does not have a handler.
            logger.debug(f"The object {object_type} does not have a custom handler")
            pass

        # 4. persist change in Sunfish tree
        return self.storage_backend.patch(path, payload)

    def delete_object(self, path: string):
        """Calls the correspondent remove function from the backend implementation. Checks that the path is valid.

        Args:
            path (str): path of the resource that we want to replace.

        Returns:
            str|exception: return confirmation string or an exception in case of fault.
        """
        object_type = self._get_type({}, path=path)
        # we assume no changes can be done on collections
        if "Collection" in object_type:
            raise CollectionNotSupported()

        try:
            # 1. check the path target of the operation exists
            self.storage_backend.read(path)
            # 2. is needed first forward the request to the agent managing the object
            self.objects_handler.forward_to_manager(SunfishRequestType.DELETE, path)
            # 3. Execute any custom handler for this object type
            self.objects_handler.dispatch(object_type, path, SunfishRequestType.DELETE)
        except ResourceNotFound:
            logger.error(f"The resource to be deleted ({path}) does not exist.")
        except AttributeError:
            # The object does not have a handler.
            logger.debug(f"The object {object_type} does not have a custom handler")

        # 4. persist change in Sunfish tree
        self.storage_backend.remove(path)
        return f"Object {path} deleted"

    def handle_event(self, payload):

        if "Context" in payload:
            context = payload["Context"]
        else:
            context = ""
        logger.debug("Started handling incoming events")
        for event in payload["Events"]:
            logger.debug(f"Handling event {event['MessageId']}")
            message_id = event['MessageId'].split(".")[-1]
            try:
                self.event_handler.dispatch(message_id, self.event_handler, event, context)
            except PropertyNotFound as e:
                logger.warning(repr(e))
                raise e
        return self.event_handler.new_event(payload)

    def _get_type(self, payload: dict, path: str = None):
        # controlla odata.type
        if "@odata.type" in payload:
            object_type = payload["@odata.type"].split('.')[0].replace("#", "")
        elif path is not None:
            obj = self.storage_backend.read(path)
            object_type = obj["@odata.type"].split('.')[0].replace("#", "")
        else:
            raise PropertyNotFound("@odata.type")

        return object_type
