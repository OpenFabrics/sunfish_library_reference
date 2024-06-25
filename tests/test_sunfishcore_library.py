# Copyright IBM Corp. 2023
# This software is available to you under a BSD 3-Clause License. 
# The full license terms are available here: https://github.com/OpenFabrics/sunfish_library_reference/blob/main/LICENSE

from genericpath import isdir
# from http.server import BaseHTTPRequestHandler
import json
import os
import logging
import pytest
from pytest_httpserver import HTTPServer
from sunfish.lib.core import Core
from sunfish.lib.exceptions import *
from tests import test_utils, tests_template
class TestSunfishcoreLibrary():
    @classmethod
    def setup_class(cls):
        path = os.path.join(os.getcwd(), 'tests', 'conf.json')
        try:
            json_data = open(path)
            cls.conf = json.load(json_data)
        except FileNotFoundError as e:
            raise ResourceNotFound('conf.json')

        cls.core = Core(cls.conf)

    @pytest.mark.order("first")
    def test_init_core(self):
        path = os.path.join(os.getcwd(), 'tests', 'conf.json')
        try:
            json_data = open(path)
            conf = json.load(json_data)
        except FileNotFoundError as e:
            raise ResourceNotFound('conf.json')

        core = Core(conf)

    @pytest.mark.order("second")
    def test_init_core_wrong_plugin(self):
        path = os.path.join(os.getcwd(), 'tests', 'conf_broken_module.json')
        try:
            json_data = open(path)
            conf = json.load(json_data)
        except FileNotFoundError as e:
            raise ResourceNotFound('conf.json')
        with pytest.raises(ModuleNotFoundError):
            core = Core(conf)


    # TEST REST
    # Delete
    @pytest.mark.order("last")
    def test_delete(self):
        # id = test_utils.get_id(self.conf["backend_conf"]["fs_root"], 'Systems')
        system_url = os.path.join(self.conf["redfish_root"], 'Systems', '1')
        logging.info('Deleting ', system_url)
        self.core.delete_object(system_url)
        assert test_utils.check_delete(system_url) == True

    def test_delete_exception(self):
        system_url = os.path.join(self.conf["redfish_root"], 'Systems', '-1')
        # raise exception if element doesnt exist
        with pytest.raises(ResourceNotFound):
            self.core.delete_object(system_url)

    # Post
    def test_post_object(self):
        json_file = tests_template.test_post_system
        path = os.path.join(self.conf["redfish_root"], "Systems")
        assert self.core.create_object(path, json_file)

    def test_post_collection_exception(self):
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
        path = "/redfish/v1/Systems/1"
        id_properties = {
            "@odata.id": os.path.join(self.conf["redfish_root"], 'Systems', id),
            "Id": id
        }
        payload.update(id_properties)

        assert self.core.replace_object(path, payload) == payload

    #  Exception put element that doesnt exists
    def test_put_exception(self):
        payload = tests_template.test_put_exception
        with pytest.raises(PropertyNotFound):
            self.core.replace_object(None, payload)

    # Patch
    def test_patch(self):
        id = test_utils.get_id(self.conf["backend_conf"]["fs_root"], 'Systems')
        object_path = os.path.join(self.conf["redfish_root"], 'Systems', id)
        object_to_update = self.core.get_object(object_path)

        payload = tests_template.test_patch
        self.core.patch_object(object_path, payload)

        object_to_update.update(payload)

        assert object_to_update == self.core.get_object(object_path)

    # Exception patch element that doesnt exists
    def test_patch_exception(self):
        payload = tests_template.test_update_exception
        with pytest.raises(ResourceNotFound):
            self.core.patch_object('/redfish/v1/Systems/-1', payload)

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
        resp = self.core.handle_event(tests_template.task_event_cancelled)
        assert len(resp) == 1

    def test_event_forwarding_exception(self, httpserver: HTTPServer):
        path = os.path.join(self.conf['redfish_root'], self.conf["backend_conf"]["subscribers_root"])
        assert self.core.create_object(path, tests_template.wrong_sub)
        resp = self.core.handle_event(tests_template.event)
        assert len(resp) == 0

    def test_event_forwarding_2(self, httpserver: HTTPServer):
        httpserver.expect_request("/").respond_with_data("OK")
        resp = self.core.handle_event(tests_template.event_resource_type_system)
        print('RESP ', resp)
        assert len(resp) == 1

    def test_resource_created_event_no_context_exception(self):
        with pytest.raises(PropertyNotFound):
            resp = self.core.handle_event(tests_template.resource_event_no_context)

    def test_agent_create_forwarding(self, httpserver: HTTPServer):
        aggr_source_path = os.path.join(self.conf['redfish_root'], "AggregationService/AggregationSources")
        fabrics_path = os.path.join(self.conf['redfish_root'], "Fabrics")
        connection_path = os.path.join(self.conf['redfish_root'], "Fabrics/CXL/Connections")
        httpserver.expect_request(connection_path, method="POST").respond_with_json(
            tests_template.test_connection_cxl_fabric)

        resp = self.core.storage_backend.write(tests_template.aggregation_source)
        resp = self.core.storage_backend.write(tests_template.test_fabric)
        resp = self.core.create_object(connection_path, tests_template.test_connection_cxl_fabric)

        assert resp == tests_template.test_response_connection_cxl_fabric

    def test_agent_forwarding_exception(self, httpserver: HTTPServer):
        connection_path = os.path.join(self.conf['redfish_root'], "Fabrics/CXL/Connections/12")

        with pytest.raises(AgentForwardingFailure):
            resp = self.core.delete_object(connection_path)

    def test_agent_delete_forwarding(self, httpserver: HTTPServer):
        connection_path = os.path.join(self.conf['redfish_root'], "Fabrics/CXL/Connections/12")
        httpserver.expect_request(connection_path, method="delete").respond_with_data("OK")

        resp = self.core.delete_object(connection_path)

        assert resp == f"Object {connection_path} deleted"

    # deletes all the subscriptions
    @pytest.mark.order("last")
    def test_clean_up(self):
        path = os.path.join(os.getcwd(), self.conf["backend_conf"]["fs_root"],
                            self.conf["backend_conf"]["subscribers_root"])
        list = os.listdir(path)
        for sub in list:
            if os.path.isdir(os.path.join(path, sub)):
                path_sub = os.path.join(self.conf["redfish_root"], self.conf["backend_conf"]["subscribers_root"], sub)
                self.core.delete_object(path_sub)
