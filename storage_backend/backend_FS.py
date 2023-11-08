# Copyright IBM Corp. 2023
# This software is available to you under a BSD 3-Clause License. 
# The full license terms are available here: https://github.com/OpenFabrics/sunfish_library_reference/blob/main/LICENSE

import logging
import os
import shutil

from flask import json
from storage_backend.backend_interface import BackendInterface
from storage_backend import utils
from sunfishcorelib.exceptions import *

class BackendFS(BackendInterface):

    def __init__(self, conf, redfish_root):
        self.root = conf["fs_root"]
        self.redfish_root = redfish_root

    def read(self, path:str):
        """Loads the content of the index.json corresponding to the requested path.

        Args:
            path (str): id of the requested resource (according to redfish specification)

        Raises:
            ResourceNotFound: if the resource does not exist in the storage

        Returns:
            json: data of the resource
        """
        logging.info('BackendFS read called')
        
        length = len(self.redfish_root)
        resource = path[length:]
        path = os.path.join(os.getcwd(), self.root, resource, 'index.json')
        
        try:
            json_data = open(path)
            data:json = json.load(json_data)
            return data
        except FileNotFoundError as e:
            raise ResourceNotFound(resource)
         
    def write(self, payload:json):
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
        id = payload['@odata.id'][length:] # id without redfish.root (es. /redfish/v1/)

        id = id.split('/')
        for index in range(2, len(id[1:])):
            present = False
            to_check = os.path.join('/'.join(id[:index]), 'index.json')
            to_check = utils.path_exist(to_check, self.root)
            with open(to_check, 'r') as data_json:
                    data = json.load(data_json)
                    data_json.close()
                    if 'Collection' in data["@odata.type"]:
                        members = data["Members"]
                        for x in members:
                            if x["@odata.id"] == os.path.join(self.redfish_root, '/'.join(id[:index+1])):
                                present = True
                    else:
                        if data[id[index]]:
                            element = data[id[index]]
                            if element["@odata.id"] == os.path.join(self.redfish_root, '/'.join(id[:index+1])):
                                present = True
                            else:
                                element["@odata.id"] = os.path.join(self.redfish_root, '/'.join(id[:index+1]))
                                with open(to_check, 'w') as data_json:
                                    json.dump(data, data_json, indent=4, sort_keys=True)
                                    data_json.close()

        last_element = len(id)-1
        collection_type = id[last_element-1]
        resource_id = id[last_element]
        full_collection = ''
        if len(id) > 2:
            for i in range(0, last_element-1):
                full_collection = full_collection + id[i] + '/'

        collection_type = os.path.join(full_collection, collection_type)	        
        
        collection_path = os.path.join(os.getcwd(), self.root, collection_type)   # collection_path  .../Resources/[folder], collection_type = [folder]
        parent_path = os.path.dirname(collection_path) # parent path .../Resources

        # check if the directory of the Collection already exists
        if not os.path.exists(collection_path):
            os.makedirs(collection_path)
           
            config = utils.generate_collection(collection_type)
            ## write file Resources/[folder]/index.json
            with open(os.path.join(collection_path, "index.json"), "w") as fd:
                fd.write(json.dumps(config, indent=4, sort_keys=True))
                fd.close()

            # update file Resources/index.json
            utils.update_collections_parent_json(path=os.path.join(parent_path, "index.json"), type=collection_type, link=self.redfish_root+collection_type)
        else:
            # checks if there is already a resource with the same id
            index_path = os.path.join(collection_path, "index.json")
            if utils.check_unique_id(index_path, payload['@odata.id']) is False:
                raise AlreadyExists(payload['@odata.id'])
                

        # create folder of the element and write index.json (assuming that the payload is valid i dont use any kind of template to write index.json)
        folder_id_path = os.path.join(collection_path, resource_id) # .../Resources/[folder]/[id]

        if not os.path.exists(folder_id_path):
            os.mkdir(folder_id_path)

        with open(os.path.join(folder_id_path, "index.json"), "w") as fd:
            fd.write(json.dumps(payload, indent=4, sort_keys=True))
            fd.close()
        
        json_collection_path = os.path.join(collection_path, 'index.json')
        utils.update_collections_json(path=json_collection_path, link=payload['@odata.id'])
        
        logging.info('BackendFS: [POST] success')
        return payload
        
    def replace(self, payload:json):
        try:
            return self._update_object(payload, True)
        except ResourceNotFound as e:
            raise ResourceNotFound(e.resource_id)
    
    def patch(self, payload:json):
        try:
            return self._update_object(payload, False)
        except ResourceNotFound as e:
            raise ResourceNotFound(e.resource_id)
    
    def _update_object(self, payload:json, replace:bool):
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

        last_element = len(id)-1
        collection_type = id[last_element-1]
        resource_id = id[last_element]
        full_collection = ''
        if len(id) > 2:
            for i in range(0, last_element-1):
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

        result:str = payload['@odata.id']
        return result

#   #   TO FIX: the code doesnt consider the linked resources. If the remove function is called, it removes only the folders but it doesnt update all the linked resources 
#               --> a link that referes to a deleted resource doesnt work.
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

        path = os.path.join(os.getcwd(), self.root, resource_id)

        if len(resource_id) == 0:
            raise ActionNotAllowed()

        if os.path.exists(path) is False:
            raise ResourceNotFound(resource_id)
        
        parent_path = os.path.dirname(path)
        json_path = os.path.join(parent_path, 'index.json')
        shutil.rmtree(path)
            
        try:
            with open(json_path,"r") as file:
                pdata = json.load(file)
                file.close()

            data = {
                "@odata.id":os.path.join(self.redfish_root, resource_id)
            }

            if 'Members' in pdata:
                pdata['Members'].remove(data)
                pdata['Members@odata.count'] = int(pdata['Members@odata.count']) - 1
            elif resource_id in pdata:
                pdata[resource_id].remove(data)

            with open(json_path,"w") as file:
                json.dump(pdata,file, indent=4, sort_keys=True)
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
                    file.close()
                
                if 'Links' in pdata and path != os.path.join(os.getcwd(), self.root):
                    link_list = pdata['Links']
                    to_del = []
                    for link in link_list:
                        for x in link_list[link]:
                            if isinstance(link_list[link], list):
                                if x['@odata.id'] == os.path.join(self.redfish_root, resource_id): 
                                    to_replace = True
                                    link_list[link].remove(x)
                                    if(len(link_list[link]) == 0):
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
                                json.dump(pdata,file, indent=4, sort_keys=True)
                                file.close()
                        to_replace = False

        return "DELETE: file removed."
    
