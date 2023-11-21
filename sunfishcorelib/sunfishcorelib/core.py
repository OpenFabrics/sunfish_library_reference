# Copyright IBM Corp. 2023
# This software is available to you under a BSD 3-Clause License. 
# The full license terms are available here: https://github.com/OpenFabrics/sunfish_library_reference/blob/main/LICENSE

import os
import uuid
from sunfishcorelib.storage_backend.backend_FS import BackendFS
from sunfishcorelib.sunfishcorelib.exceptions import CollectionNotSupported, InvalidPath
from sunfishcorelib.events.event_handler import EventHandler

class Core:

    def __init__(self, conf):
        """init that implements the chosen backend specified in the conf dict.

        Args:
            conf (dict): dictionary where are specified the storage implementation type and the specific backend configuration.
        """
        if conf['storage_backend'] == 'FS':
            self.redfish_root = conf["redfish_root"]
            self.storage_backend = BackendFS(conf["backend_conf"], self.redfish_root)
            self.event_handler = EventHandler(self.storage_backend, conf["backend_conf"]["fs_root"], self.redfish_root)
        # elif conf['storage_backend'] == '<OTHER STORAGE>':
            # ...
    
    def get_object(self, path):
        """Calls the correspondent read function from the backend implementation and checks that the path is valid.

        Args:
            path (str): path of the resource. It should comply with Redfish specification.

        Raises:
            InvalidPath: custom exception that is raised if the path is not compliant with the current Redfish specification.

        Returns:
            str|exception: str of the requested resource or an exception in case of fault. 
        """
        # call function from backend
        return self.storage_backend.read(path)
        
    def create_object(self, path, payload:dict):
        """Calls the correspondent create function from the backend implementation. 
        Before to call the create function it generates a unique uuid and updates the payload adding Id and @odata.id.
        To distinguish the storage of an element from the storage of an EventDestination (event subscription schema) the property 'Destination' is checked 
        because it belongs only to EventDestination and it is required.
        @odata.type is checked to verify that this is not a try to store a Collection (forbidden)

        Args:
            payload (resource): resource that we want to store.

        Returns:
            str|exception: return the stored resource or an exception in case of fault.
        """
        
         # generate unique uuid
        id = str(uuid.uuid4())
        to_add = {
            'Id': id,
            '@odata.id': os.path.join(path,id)
        }
        payload.update(to_add)

        ## controlla odata.type
        if 'Destination' in payload:
            return self.event_handler.new_subscription(payload)

        if '@odata.type' in payload:
            if "Collection" in payload['@odata.type']:
                raise CollectionNotSupported()
        
        # call function from backend
        return self.storage_backend.write(payload)

    def replace_object(self, payload):
        """Calls the correspondent replace function from the backend implementation.

        Args:
            payload (resource): resource that we want to replace.

        Returns:
            str|exception: return the replaced resource or an exception in case of fault.
        """
        ## controlla odata.type
        if "Context" in payload:
            self.event_handler.delete_subscription(payload)
            self.event_handler.new_subscription(payload)
        # call function from backend
        return self.storage_backend.replace(payload)
    
    def patch_object(self, payload):
        """Calls the correspondent patch function from the backend implementation.

        Args:
            payload (resource): resource that we want to partially update.

        Returns:
            str|exception: return the updated resource or an exception in case of fault.
        """
        if "Context" in payload:
            self.event_handler.delete_subscription(payload)
            resp = self.storage_backend.patch(payload)
            self.event_handler.new_subscription(resp)
            return resp
        # call function from backend
        return self.storage_backend.patch(payload)

    def delete_object(self, path):
        """Calls the correspondent remove function from the backend implementation. Checks that the path is valid.

        Args:
            path (str): path of the resource that we want to replace.

        Returns:
            str|exception: return confirmation string or an exception in case of fault.
        """
        ## delete subscription
        ## controlla odata.type
        payload = self.storage_backend.read(path)
        if "Context" in payload:
            self.event_handler.delete_subscription(payload)

        # call function from backend
        return self.storage_backend.remove(path)
    
    def handle_event(self, payload):
        return self.event_handler.new_event(payload)