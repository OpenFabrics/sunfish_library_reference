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

def check_delete(path):
    if os.path.exists(path):
        print('non eliminato')
        return False
    return True

# def check_update(payload, redfish_root):
#     path = os.path.join(get_resource_path(payload, redfish_root), 'index.json')
#     modification_time = time.ctime(os.path.getctime(path))
#     current_time = time.ctime(time.time())
#     # print('modification ', modification_time, ' now ', current_time)
#     if current_time == modification_time:
#         return True
#     return False