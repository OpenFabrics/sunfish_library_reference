# Copyright IBM Corp. 2023
# This software is available to you under a BSD 3-Clause License. 
# The full license terms are available here: https://github.com/OpenFabrics/sunfish_library_reference/blob/main/LICENSE

import os
import string
import uuid
import logging
from typing import Optional

from sunfish.storage.backend_FS import BackendFS
from sunfish.lib.exceptions import CollectionNotSupported, ResourceNotFound, AgentForwardingFailure, PropertyNotFound
from sunfish.events.redfish_event_handler import RedfishEventHandler, RedfishEventHandlersTable

from sunfish.events.redfish_subscription_handler import RedfishSubscriptionHandler
from sunfish.lib.object_handler import RedfishObjectHandler
from sunfish.models.types import *
from sunfish.lib.agents_management import Agent

logger = logging.getLogger(__name__)


class Core:

    def __init__(self, conf):
        """init that implements the chosen backend specified in the conf dict.

        Args:
            conf (dict): dictionary where are specified the storage implementation type and the specific backend configuration.
        """

        self.conf = conf

        if conf['storage_backend'] == 'FS':
            self.storage_backend = BackendFS(self.conf)
        # elif conf['storage_backend'] == '<OTHER STORAGE>':
        # ...

        if conf['handlers']['subscription_handler'] == 'redfish':
            self.subscription_handler = RedfishSubscriptionHandler(self)

        if conf['handlers']['event_handler'] == 'redfish':
            self.event_handler = RedfishEventHandler(self)

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
        if not '@odata.id' in payload and not 'Id' in payload:
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
            agent_response = self._forward_to_agent(SunfishRequestType.CREATE, path, payload=payload)
            if agent_response:
                payload_to_write = agent_response
            # 3. Execute any custom handler for this object type
            RedfishObjectHandler.dispatch(self, object_type, path, SunfishRequestType.CREATE, payload=payload)
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
            self._forward_to_agent(SunfishRequestType.REPLACE, path, payload=payload)
            # 3. Execute any custom handler for this object type
            RedfishObjectHandler.dispatch(self, object_type, path, SunfishRequestType.REPLACE, payload=payload)
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
            self._forward_to_agent(SunfishRequestType.PATCH, path, payload=payload)
            # 3. Execute any custom handler for this object type
            RedfishObjectHandler.dispatch(self, object_type, path, SunfishRequestType.PATCH, payload=payload)
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
            self._forward_to_agent(SunfishRequestType.DELETE, path)
            # 3. Execute any custom handler for this object type
            RedfishObjectHandler.dispatch(self, object_type, path, SunfishRequestType.DELETE)
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
            self.event_handler.dispatch(message_id, self.event_handler, event, context)
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

    def _forward_to_agent(self, request_type: SunfishRequestType, path: string, payload: dict = None) -> Optional[dict]:
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
        agent = Agent.is_agent_managed(self, path_to_check)
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
