# Copyright IBM Corp. 2023
# This software is available to you under a BSD 3-Clause License. 
# The full license terms are available here: https://github.com/OpenFabrics/sunfish_library_reference/blob/main/LICENSE

import pdb
import json
import logging
import os
import shutil

from sunfish.storage.backend_interface import BackendInterface
from sunfish_plugins.storage.file_system_backend import utils
from sunfish.lib.exceptions import *

logger = logging.getLogger(__name__)

class BackendFS(BackendInterface):

    def __init__(self, conf):
        self.root = conf["backend_conf"]["fs_root"]
        self.redfish_root = conf["redfish_root"]

    def read(self, path: str) -> dict:
        """Loads the content of the index.json corresponding to the requested path.

        Args:
            path (str): id of the requested resource (according to redfish specification)

        Raises:
            ResourceNotFound: if the resource does not exist in the storage

        Returns:
            json: data of the resource
        """
        logger.debug("BackendFS: read called")

        length = len(self.redfish_root)
        resource = path.replace(self.redfish_root, "")
        logger.debug(f"PATH: {path}")
        path = os.path.join(os.getcwd(), self.root, resource, 'index.json')
        logger.debug(f"BackendFS: read called on {path}")
        try:
            json_data = open(path)
            data = json.load(json_data)
            return data
        except FileNotFoundError as e:
            raise ResourceNotFound(resource)

    def write(self, payload: dict):
        """Checks if the Collection exists for that resource and stores the resource in the correct position of the file system.
        It create the directory of the resource, creates the index.json file and updates the files linked with the new resource (Collection members or Resources list).

        Args:
            payload (json): json representing the resource that should be stored.

        Raises:
            CollectionNotSupported: the storage of the collections is not supported.
            AlreadyExists: it is not possible to have duplicate resources with the same ID.

        Returns:
            json: stored data
        """
        logging.info('BackendFS write called')

        # get ID and collection from payload
        length = len(self.redfish_root)
        id = payload['@odata.id'][length:]  # id without redfish.root (es. /redfish/v1/)
        parent_is_collection = True # default assumption

        print(f"BackendFS.write called on {id}")
        id = id.split('/')
        for index in range(2, len(id[1:])):
            to_check = os.path.join('/'.join(id[:index]), 'index.json')
            to_check = os.path.join(os.getcwd(), self.root, to_check)
            print(f"BackendFS.write():  path to check: {to_check}")
            if os.path.exists(to_check) is False:
                print("path does not exist\n")
                raise ActionNotAllowed()
        '''
            with open(to_check, 'r') as data_json:
                data = json.load(data_json)
                data_json.close()
                if 'Collection' in data["@odata.type"]:
                    print("path is to a Collection\n")
                    members = data["Members"]
                    for x in members:
                        if x["@odata.id"] == os.path.join(self.redfish_root, '/'.join(id[:index + 1])):
                            present = True
                else:
                    if data[id[index]]:
                        element = data[id[index]]
                        if type(element) is not list:
                            continue
                        for el in element:
                            if el["@odata.id"] == os.path.join(self.redfish_root, '/'.join(id[:index + 1])):
                                present = True
                            else:
                                el["@odata.id"] = os.path.join(self.redfish_root, '/'.join(id[:index + 1]))
                                print(f"BackendFS.write of {el['@odata.id']}")
                                with open(to_check, 'w') as data_json:
                                    json.dump(data, data_json, indent=4, sort_keys=True)
                                    data_json.close()

        '''
        # we get here only if all grandparent objects exist
        last_element = len(id) - 1
        collection_type = id[last_element - 1]
        resource_id = id[last_element]
        full_collection = ''
        # create the path of the full collection if it is a subcollection
        if len(id) > 2:
            for i in range(0, last_element - 1):
                full_collection = full_collection + id[i] + '/'

        collection_type = os.path.join(full_collection, collection_type)

        collection_path = os.path.join(os.getcwd(), self.root,
                                       collection_type)  # collection_path  .../Resources/[folder], collection_type = [folder]
        parent_path = os.path.dirname(collection_path)  # parent path .../Resources

        #pdb.set_trace()
        # check if the directory of the Collection already exists
        if not os.path.exists(collection_path):
            # if parent directory doesn't exist, we assume it is a collection and create the collection
            print(f"backendFS.write: making collection path directory")
            os.makedirs(collection_path)

            # the following line assumes the path element name dictates the collection type
            # it is more proper to examine the @odata.type property of the object being created!
            config = utils.generate_collection(collection_type)

            # if the item to be written is managed by an agent, we want the collection containing it to also be marked
            # accordingly. We do this only for collections to be created because we assume that if the collection is
            # there already:
            #  a. The collection is a first level one that is managed by Sunfish
            #  b. The collection was previously created during an agent discovery process and therefore already marked
            # if "Oem" in payload and "Sunfish_RM" in payload["Oem"] and len(id) > 2 :
            #     if "Oem" not in config:
            #         config["Oem"] = {}
            #     config["Oem"]["Sunfish_RM"] = payload["Oem"]["Sunfish_RM"]

            ## write file Resources/[folder]/index.json
            with open(os.path.join(collection_path, "index.json"), "w") as fd:
                fd.write(json.dumps(config, indent=4, sort_keys=True))
                fd.close()

            # check if the index.json representing the collection exists. In case it doesnt it will create index.json with the collection template
            if os.path.exists(os.path.join(parent_path, "index.json")):
                collection_name = collection_type.split('/')[-1]
                utils.update_collections_parent_json(path=os.path.join(parent_path, "index.json"), type=collection_name,
                                                     link=self.redfish_root + collection_type)
            else:
                utils.generate_collection(collection_type)
        else:
            # checks if there is already a resource with the same id
            index_path = os.path.join(collection_path, "index.json")
            with open(index_path, 'r') as data_json:
                parent_data = json.load(data_json)
                data_json.close()
            if 'Collection' in parent_data["@odata.type"]:
                print("parent path is to a Collection\n")
                if utils.check_unique_id(index_path, payload['@odata.id']) is False:
                    raise AlreadyExists(payload['@odata.id'])
                    pass
            else:
                print("path is to an object\n")
                parent_is_collection = False  #
                pass



        # creates folder of the element and write index.json (assuming that the payload is valid i dont use any kind of template to write index.json)
        folder_id_path = os.path.join(collection_path, resource_id)  # .../Resources/[folder]/[resource_id]

        # if folder does not exist, check the parent path
        # not sure we need this next check given we do the same above
        if not os.path.exists(folder_id_path):
            os.mkdir(folder_id_path)
            parent_path = os.path.join(*folder_id_path.split("/")[:-2])
            parent_json = "/" + os.path.join(parent_path, "index.json")
            root_path = os.path.join(os.getcwd(), self.root)
            if not os.path.exists(parent_json) and parent_path != root_path[1:]:
                logger.warning(
                    "You should not be here, this is creating an entire path with multiple missing grandparents")



        logger.info(f"backend_FS.write:  writing {folder_id_path}/index.json")
        with open(os.path.join(folder_id_path, "index.json"), "w") as fd:
            fd.write(json.dumps(payload, indent=4, sort_keys=True))
            fd.close()

        json_collection_path = os.path.join(collection_path, 'index.json')

        # updates the collection with the new element created
        if parent_is_collection:      # need to insert new member into collection
            if os.path.exists(json_collection_path):
                utils.update_collections_json(path=json_collection_path, link=payload['@odata.id'])
            else:
                utils.generate_collection(collection_type)
                pass

        # Events have to be handled in a different way. 
        # To check if write() is called by an event subscription (EventDestination format) I check 'Destination' because
        # it is the only required required property that other objects doesnt have

        logging.info('BackendFS: [POST] success')
        return payload

    def replace(self, payload: dict):
        try:
            return self._update_object(payload, True)
        except ResourceNotFound as e:
            raise ResourceNotFound(e.resource_id)

    def patch(self, path:str, payload:dict):
        _object = self.read(path)
        _object.update(payload)
        try:
            return self._update_object(_object, False)
        except ResourceNotFound as e:
            raise ResourceNotFound(e.resource_id)

    def _update_object(self, payload: dict, replace: bool):
        """writes the updated json file.

        Args:
            payload (json): json containing the fields to be updated.
            replace (bool, optional): if replace is False it loads only the fields to be updated, if replace is True it directly writes the json file. Defaults to False.

        Raises:
            ResourceNotFound: is not possible to update a resource that is not in the storage

        Returns:
            str: id of the updated resource
        """
        ## code that re-write into file
        logging.info('BackendFS patch update called')

        # get ID and collection from payload
        length = len(self.redfish_root)
        id = payload['@odata.id'][length:]
        id = id.split('/')

        last_element = len(id) - 1
        collection_type = id[last_element - 1]
        resource_id = id[last_element]
        full_collection = ''
        if len(id) > 2:
            for i in range(0, last_element - 1):
                full_collection = full_collection + id[i] + '/'
        
        collection_type = os.path.join(full_collection, collection_type)	        
        path = os.path.join(os.getcwd(), self.root, collection_type, resource_id, 'index.json')   #   .../Resources/[folder]/[resource_id]/index.json

        try:
            if replace is False:
                # Read json from file.
                with open(path, 'r') as data_json:
                    data = json.load(data_json)
                    data_json.close()

                # Update the keys of payload in json file.
                for key, value in payload.items():
                    data[key] = value
            else:
                data = payload
            # Write the updated json to file.
            with open(path, 'w') as f:
                json.dump(data, f, indent=4, sort_keys=True)
                f.close()

        except FileNotFoundError as e:
            raise ResourceNotFound(resource_id)

        result: str = self.read(payload["@odata.id"])
        # result:str = payload['@odata.id']

        return result

    def remove(self, path:str):
        """Deletes the object and updates the linked files of the same collection. Then it scans all the dir tree and deletes the links of the deleted resource.

        Args:
            path (str): reference path of the resource that should be removed.

        Raises:
            ActionNotAllowed: it is not possible to remove the whole file system.
            ResourceNotFound: it is not possible to remove a resource that does not exists.

        Returns:
            str: confirmation string
        """
        ## code that removes a file
        logging.info('BackendFS: remove called')

        length = len(self.redfish_root)
        resource_id = path[length:]

        full_path = os.path.join(os.getcwd(), self.root, resource_id)

        if len(resource_id) == 0:
            raise ActionNotAllowed()

        if os.path.exists(full_path) is False:
            raise ResourceNotFound(resource_id)

        parent_path = os.path.dirname(full_path)
        json_path = os.path.join(parent_path, 'index.json')
        shutil.rmtree(full_path)

        try:
            with open(json_path, "r") as file:
                pdata = json.load(file)
                file.close()

            data = {
                "@odata.id": os.path.join(self.redfish_root, resource_id)
            }
            collection_name = resource_id.split('/')[-1]
            if 'Members' in pdata and data in pdata['Members']:
                pdata['Members'].remove(data)
                pdata['Members@odata.count'] = int(pdata['Members@odata.count']) - 1
            elif collection_name in pdata:
                del pdata[collection_name]

            with open(json_path, "w") as file:
                json.dump(pdata, file, indent=4, sort_keys=True)
                file.close()

        except FileNotFoundError as e:
            raise ResourceNotFound(resource_id)

        # check links
        to_replace = False
        first = False

        for path, directories, files in os.walk(os.path.join(os.getcwd(), self.root)):
            if 'index.json' in files:
                file_path = os.path.join(path, 'index.json')

                with open(file_path, "r") as file:
                    pdata = json.load(file)

                if 'Links' in pdata and path != os.path.join(os.getcwd(), self.root):
                    link_list = pdata['Links']
                    to_del = []
                    for link in link_list:
                        for x in link_list[link]:
                            if isinstance(link_list[link], list):
                                to_compare = ""
                                if type(x) is dict and "@odata.id" in x:
                                    to_compare = x['@odata.id']
                                elif type(x) is str:
                                    to_compare = x
                                if to_compare == os.path.join(self.redfish_root, resource_id):
                                    to_replace = True
                                    link_list[link].remove(x)
                                    if len(link_list[link]) == 0:
                                        to_del.append(link)
                            elif isinstance(link_list[link], dict):
                                if x == os.path.join(self.redfish_root, resource_id):
                                    to_del.append(link)
                                    to_replace = True
                    if to_del:
                        for el in to_del:
                            del link_list[el]
                    if to_replace:
                        with open(file_path, "w") as file:
                            json.dump(pdata, file, indent=4, sort_keys=True)
                        to_replace = False

        return "DELETE: file removed."



    def reset_resources(self, resource_path: str, clean_resource_path: str):
        ###
        # this command ONLY applies to the File System storage backend
        # The arguments are:
        #   - clean_resource_path: "<relative path to directory root containing the clean resource tree>"
        #   - resource_path: "<relative path to the FS backend's Resources directory>"
        # there is no protection on the receipt of this command
		# This command will not work if the backend file system is not the host's filesystem!
		#
        logger.info("reset_resources method called")
        logger.info(f"fs root resource path is {resource_path}")
        logger.info(f"clean_resource path is {clean_resource_path}")
        try:
            if os.path.exists(resource_path) and os.path.exists(clean_resource_path):
                shutil.rmtree(resource_path)
                shutil.copytree(clean_resource_path, resource_path)
                logger.debug("reset_resources complete")
                resp = "OK", 204
            else:
                logger.debug("reset_resources: one or more paths do not exist.")
                pass
        except Exception:
            raise Exception("reset_resources Failed")
            resp = "Fail", 500
        return resp

