# Copyright IBM Corp. 2023
# This software is available to you under a BSD 3-Clause License. 
# The full license terms are available here: https://github.com/OpenFabrics/sunfish_library_reference/blob/main/LICENSE

import json
import os
import time

def get_resource_path(payload, redfish_root):
    length = len(redfish_root)
    object_id = payload['@odata.id'][length:]
    object_id = object_id.split('/')
    collection = object_id[0]
    id = object_id[1]
    path = os.path.join(os.getcwd(), 'Resources', collection, id)
    return path

def check_object(payload, redfish_root):
    path = get_resource_path(payload, redfish_root)
    return os.path.exists(path) and os.path.exists(os.path.join(path, 'index.json')) 

def check_uploaded_objects(upload_event, redfish_root):
    aggSrc_Id = upload_event["Context"]
    aggSrc_path = os.path.join(os.getcwd(), 'Resources','AggregationService','AggregationSources',\
            aggSrc_Id, 'index.json')
    with open(aggSrc_path, "r", encoding="utf-8") as file:
        aggSrc_obj = json.load(file)
    # extract any ResourcesAccessed
    things_uploaded = aggSrc_obj.get("Links", {}).get("ResourcesAccessed", [])
    return things_uploaded

def check_delete(path):
    if os.path.exists(path):
        print('non eliminato')
        return False
    return True

def get_id(root, collection):
    list = os.listdir(os.path.join(os.getcwd(), root, collection))
    for dir in list:
        if dir != '.DS_Store' and dir != 'index.json':
            return dir
