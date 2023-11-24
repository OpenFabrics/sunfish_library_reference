# Copyright IBM Corp. 2023
# This software is available to you under a BSD 3-Clause License. 
# The full license terms are available here: https://github.com/OpenFabrics/sunfish_library_reference/blob/main/LICENSE

import json
import os
from sunfishcorelib.sunfishcorelib.exceptions import *

_COLLECTION_TEMPLATE = \
{
  "@odata.id": "",
  "@odata.type": "",
  "Name": " Collection",
  "Members@odata.count": 0,
  "Members": [ ]
}

def update_collections_json(path, link):
    """Updates the file representing the collection where a resource has been added. It adds the reference to the new resource.

    Args:
        path (str): path of the file to be updated
        link (str): reference ID to the new resource
    """
    # Read json from file.
    with open(path, 'r') as file_json:
        data = json.load(file_json)

    # Update the keys of payload in json file.
    data['Members'].append({"@odata.id": link})
    data['Members@odata.count'] = len(data['Members'])

    # Write the updated json to file.
    with open(path, 'w') as file_json:
        json.dump(data, file_json, indent=4)

def update_collections_parent_json(path, type, link):
    """Adds a new collection inside the file where the collections are listed.

    Args:
        path (str): path of the file to be updated
        type (str): type of the new collection
        link (str): reference ID to the new collection
    """
    with open(path, 'r') as file_json:
        data = json.load(file_json)

    # Update the keys of payload in json file.
    data[type] = {"@odata.id": link}

    # Write the updated json to file.
    with open(path, 'w') as file_json:
        json.dump(data, file_json, indent=4)

def check_unique_id(path, resource_id):
    """Checks if a resource with the same ID is already stored.

    Args:
        path (str): path of the file where the elements are listed.
        resource_id (str): id to check

    Returns:
        bool: returns True if the ID is unique, return False if it is already used.
    """
    data = open(path)
    json_data = json.load(data)
    data.close()
    members = json_data["Members"]
    
    for x in members:
        if x["@odata.id"] == resource_id:
            return False
    return True

def generate_collection(collection_type):
    """Using the collection template it fills the fields that depends on the specific collection.

    Args:
        collection_type (str): type of the collection

    Returns:
        dict: dictionary of the collection generated
    """
    collection = _COLLECTION_TEMPLATE
    collection["@odata.id"] = "/redfish/v1/" + collection_type
    collection["@odata.type"] = "#"+ collection_type + "Collection." + collection_type + "Collection"
    collection["Name"] = collection_type + " Collection"
    return collection

def path_exist(path, root):
    to_check = os.path.join(os.getcwd(), root, path)
    if os.path.exists(to_check):
        return to_check
    else:
        raise InvalidPath(os.path.join(redfish_root, path))

def check_collection_type(name, type):
    name = ''.join('#', name, 'Collection', '.', name, 'Collection')
    if name == type:
        return
    else:
        raise IllegalCollectionType(type)