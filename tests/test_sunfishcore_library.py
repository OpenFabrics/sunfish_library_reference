# Copyright IBM Corp. 2023
# This software is available to you under a BSD 3-Clause License. 
# The full license terms are available here: https://github.com/OpenFabrics/sunfish_library_reference/blob/main/LICENSE

from http.server import BaseHTTPRequestHandler
import json
import os
import shutil
import logging
import pytest
import requests
from pytest_httpserver import HTTPServer
from sunfishcorelib.sunfishcorelib.core import Core
from sunfishcorelib.sunfishcorelib.exceptions import *
from tests import test_utils, tests_template

class TestSunfishcoreLibrary():
    @classmethod
    def setup_class(cls):
        shutil.rmtree(os.path.join(os.getcwd(),'tests', 'Resources', 'EventService', 'Subscriptions'))
        path = os.path.join(os.getcwd(), 'tests', 'Resources', 'EventService', 'Subscriptions')
        os.mkdir(path)
        with open(os.path.join(path,'index.json'), 'w') as f:
            json.dump(tests_template.setup_subscriptions, f)
        f.close()
        
        cls.conf = {
            "storage_backend": "FS",
	        "redfish_root": "/redfish/v1/",
	        "backend_conf" : {
		        "fs_root": "tests/Resources",
                "subscribers_root": "EventService/Subscriptions"
	        }
        }
        cls.core = Core(cls.conf)
    
    # TEST REST
    # Delete
    @pytest.mark.order("last")
    def test_delete(self):
        id = test_utils.get_id(self.conf["backend_conf"]["fs_root"], 'Systems')
        system_url = os.path.join(self.conf["redfish_root"], 'Systems', id)
        logging.info('Deleting ', system_url)
        self.core.delete_object(system_url)
        assert test_utils.check_delete(system_url) == True
    
        # raise exception if element doesnt exist
        with pytest.raises(ResourceNotFound):
            self.core.delete_object(system_url)

    # Post
    def test_post_object(self):
        json_file = tests_template.test_post_system
        path = os.path.join(self.conf["redfish_root"], "Systems")
        assert self.core.create_object(path, json_file)

        # Collection excpetion
        path = os.path.join(self.conf["redfish_root"], "Systems")
        with pytest.raises(CollectionNotSupported):
            self.core.create_object(path, tests_template.test_collection)

    # Get
    def test_get(self):
        id = test_utils.get_id(self.conf["backend_conf"]["fs_root"], 'Systems')
        system_url = os.path.join(self.conf["redfish_root"], 'Systems', id)
        assert self.core.get_object(system_url)
    
    # Exception get element that doesnt exists
    def test_get_exception(self):
        system_url = os.path.join(self.conf["redfish_root"], 'Systems', '-1')
        with pytest.raises(ResourceNotFound):
            self.core.get_object(system_url)

    # Put
    def test_put(self):
        # pytest.set_trace()
        id = test_utils.get_id(self.conf["backend_conf"]["fs_root"], 'Systems')
        payload = tests_template.test_put
        id_properties = {
            "@odata.id": os.path.join(self.conf["redfish_root"], 'Systems', id),
            "Id": id
        }
        payload.update(id_properties)
        self.core.replace_object(payload)
        assert self.core.replace_object(payload) == payload

    #  Exception put element that doesnt exists
    def test_put_exception(self):
        payload = tests_template.test_update_exception
        with pytest.raises(ResourceNotFound):
            self.core.replace_object(payload)
    
    # Patch
    def test_patch(self):
        id = test_utils.get_id(self.conf["backend_conf"]["fs_root"], 'Systems')
        payload = tests_template.test_patch
        id_properties = {
            "@odata.id": os.path.join(self.conf["redfish_root"], 'Systems', id),
            "Id": id
        }
        payload.update(id_properties)
        assert self.core.patch_object(payload) == self.core.get_object(payload['@odata.id'])
    
    # Exception patch element that doesnt exists
    def test_patch_exception(self):
        payload = tests_template.test_update_exception
        with pytest.raises(ResourceNotFound):
            self.core.patch_object(payload)

    # EVENTING and SUBSCRIPTIONS
    def test_subscription(self):
        path = os.path.join(self.conf['redfish_root'], self.conf["backend_conf"]["subscribers_root"])
        assert self.core.create_object(path, tests_template.sub1)
        assert self.core.create_object(path, tests_template.sub2)
        assert self.core.create_object(path, tests_template.sub3)

    @pytest.fixture(scope="session")
    def httpserver_listen_address(self):
        return ("localhost", 8080)
    
    def test_event_forwarding(self, httpserver: HTTPServer):
        httpserver.expect_request("/").respond_with_data("OK")
        resp = self.core.handle_event(tests_template.event)
        assert len(resp) == 1

    def test_event_forwarding_exception(self, httpserver: HTTPServer):
        path = os.path.join(self.conf['redfish_root'], self.conf["backend_conf"]["subscribers_root"])
        assert self.core.create_object(path, tests_template.wrong_sub)
        resp = self.core.handle_event(tests_template.event)
        assert len(resp) == 1