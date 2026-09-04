# Copyright IBM Corp. 2023
# This software is available to you under a BSD 3-Clause License. 
# The full license terms are available here: https://github.com/OpenFabrics/sunfish_library_reference/blob/main/LICENSE

from genericpath import isdir
# from http.server import BaseHTTPRequestHandler
import json
import os
import logging
import pytest
import shutil
import pdb
from pathlib import Path
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
        try:
            core = Core(conf)
        except ModuleNotFoundError as e:
            assert False, f" test_init_core_wrong_plugin raised an exception {e}"

    # TEST REST
    # Delete
    @pytest.mark.order("last")
    def test_delete(self):
        # id = test_utils.get_id(self.conf["backend_conf"]["fs_root"], 'Systems')
        system_url = os.path.join(self.conf["redfish_root"], 'Systems', '1')
        logging.info('Deleting ', system_url)
        self.core.delete_object(system_url)
        assert test_utils.check_delete(system_url) == True

    # reset the test directory
    def test_reset_directories(self):
        base_path = Path(__file__).parent.parent
        src = base_path / "tests/Resources"
        dst = base_path / "Resources"
        # Copy the test tree over the existing Resources tree
        shutil.rmtree(dst, ignore_errors=True)
        shutil.copytree(src, dst, dirs_exist_ok=True) 

    def test_delete_exception(self):
        system_url = os.path.join(self.conf["redfish_root"], 'Systems', '-1')
        # raise exception if element doesnt exist
        with pytest.raises(ResourceNotFound):
            self.core.delete_object(system_url)

    # Post
    def test_post_object(self):
        json_file = tests_template.test_post_system
        path = os.path.join(self.conf["redfish_root"], "Systems")
        #pdb.set_trace()
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
        #return ("127.0.0.1", 8080)

    def test_event_forwarding(self, httpserver: HTTPServer):
        httpserver.expect_request("/").respond_with_data("OK")
        #pdb.set_trace()
        #resp = self.core.handle_event(tests_template.task_event_cancelled)
        resp = self.core.event_handler.new_event(tests_template.task_event_cancelled)
        assert len(resp) == 1

    def test_event_forwarding_exception(self, httpserver: HTTPServer):
        path = os.path.join(self.conf['redfish_root'], self.conf["backend_conf"]["subscribers_root"])
        assert self.core.create_object(path, tests_template.wrong_sub)
        #resp = self.core.handle_event(tests_template.event)
        resp = self.core.event_handler.new_event(tests_template.event)
        assert len(resp) == 0

    def test_event_forwarding_2(self, httpserver: HTTPServer):
        httpserver.expect_request("/").respond_with_data("OK")
        #resp = self.core.handle_event(tests_template.event_resource_type_system)
        resp = self.core.event_handler.new_event(tests_template.event_resource_type_system)
        assert len(resp) == 1

    def test_resource_created_event_no_context_exception(self):
        with pytest.raises(PropertyNotFound):
            resp = self.core.handle_event(tests_template.resource_event_no_context)

    def test_agent_create_forwarding(self, httpserver: HTTPServer):
        aggr_source_path = os.path.join(self.conf['redfish_root'], "AggregationService/AggregationSources")
        fabrics_path = os.path.join(self.conf['redfish_root'], "Fabrics")
        connection_path = os.path.join(self.conf['redfish_root'], "Fabrics/CXL/Connections")
        connection_uri = os.path.join(self.conf['redfish_root'], "Fabrics/CXL/Connections/12")
        httpserver.expect_request(connection_uri, method="POST").respond_with_json(
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

    # test agent register and agent upload event handlers
    def test_agent_register(self, httpserver: HTTPServer):
        connection_path = os.path.join(self.conf['redfish_root'], "AggregationService/ConnectionMethods/Pytest2")
        httpserver.expect_ordered_request(connection_path, method="GET").respond_with_json(tests_template.connection_method_pytest2)
        connection_path = os.path.join(self.conf['redfish_root'], "EventService/Subscriptions/SunfishServer")
        httpserver.expect_ordered_request(connection_path, method="PATCH").respond_with_data("OK")
        resp = self.core.handle_event(tests_template.reg_event)
        assert len(httpserver.log) == 2
        
        assert  len(resp) == 1

    def test_agent_upload(self, httpserver: HTTPServer, caplog):
        
        # arm the httpserver with agent's response to GET on OriginOfCondition
        connection_path = os.path.join(self.conf['redfish_root'], "Fabrics/Pytest1")
        httpserver.expect_ordered_request(connection_path, method="GET").respond_with_json(tests_template.fabrics_pytest1)
        # the above is actually retrieved again at start of recursive fetch (upload)
        connection_path = os.path.join(self.conf['redfish_root'], "Fabrics/Pytest1")
        httpserver.expect_ordered_request(connection_path, method="GET").respond_with_json(tests_template.fabrics_pytest1)
        # arm the httpserver with agent's response to GET on subordinate Switches collection
        connection_path = os.path.join(self.conf['redfish_root'], "Fabrics/Pytest1/Switches")
        httpserver.expect_ordered_request(connection_path, method="GET").respond_with_json(tests_template.fabrics_switch_collection)
        # arm the httpserver with agent's response to GET on Switch object  
        connection_path = os.path.join(self.conf['redfish_root'], "Fabrics/Pytest1/Switches/Pytest1")
        httpserver.expect_ordered_request(connection_path, method="GET").respond_with_json(tests_template.fabrics_switch_pytest1)
        resp = self.core.handle_event(tests_template.upload_event)
        upload_list =  test_utils.check_uploaded_objects(tests_template.upload_event, self.conf['redfish_root'])
        assert len(upload_list) == 3
        assert len(httpserver.log) == 4
        # TODO
        # should verify the two objects got uploaded and written to the Sunfish DB
        
        assert  len(resp) == 1
        #assert "Sunfish Internal Event Generation function Error" in caplog.text

    
    def test_event_resourceChanged(self, httpserver: HTTPServer):
        # requires test_agent_upload runs successfully before calling this test
        #
        # This test checks two things:
        #   1) when a new Subscription is created, Sunfish core creates a ResourceCreated Event
        #       which will get forwarded to the new subscriber
        #   2) then when a ResourceUpdated event is sent to Sunfish core, 
        #       Sunfish fetches the updated resource (OriginOfCondition)
        #       and also sends a ResourceUpdated event to the new subscriber
        #
        # arm the httpserver with subscriber's response to POST of the create_object of subscription sub4
        connection_path = os.path.join(self.conf['redfish_root'], "/")
        httpserver.expect_ordered_request(connection_path, method="POST").respond_with_data("OK")
        # install another subscriber for ResourceEvents, (this will also trigger a ResourceCreated event!)
        path = os.path.join(self.conf['redfish_root'], self.conf["backend_conf"]["subscribers_root"])
        assert self.core.create_object(path, tests_template.sub4)

        # arm the httpserver with agent's response to GET on OriginOfCondition
        connection_path = os.path.join(self.conf['redfish_root'], "Fabrics/Pytest1/Switches/Pytest1")
        httpserver.expect_ordered_request(connection_path, method="GET").respond_with_json(tests_template.fabrics_switch_pytest1_modified)
        # arm the httpserver with subscriber's response to POST on Eventlistener
        connection_path = os.path.join(self.conf['redfish_root'], "Fabrics/Pytest1/Switches/Pytest1")
        httpserver.expect_ordered_request("/", method="POST").respond_with_data("OK")
        # send Sunfish core a ResourceUpdated event naming a Switch as OriginOfCondition
        resp = self.core.handle_event(tests_template.update_switch)
        assert len(httpserver.log) == 3
        # TODO
        # should verify the updated switch got uploaded and written to the Sunfish DB
        
        # handle_event() will return list of UUIDs to which the event was forwarded
        assert  len(resp) == 1

    def test_2nd_agent_upload(self, httpserver: HTTPServer, caplog):
        
        # this tests a 2nd agent upload of a CXL fabric with the same names as
        # the previous agent's upload.  The 2nd agent's upload has a different Fabric UUID
        # so Sunfish will RENAME the 2nd agent's fabric object
        # Because this test runs AFTER test_event_resourceChanged, there will be events 
        # issued for the creation of 3 new objects uploaded from the 2nd agent
        #
        # this test requires the previous test_agent_upload and test_event_resourceChanged 
        # both completed successfully
        #
        # arm the httpserver with agent's response to GET on OriginOfCondition
        connection_path = os.path.join(self.conf['redfish_root'], "Fabrics/Pytest1")
        httpserver.expect_ordered_request(connection_path, method="GET").respond_with_json(tests_template.fabrics_pytest1b)
        # the above is actually retrieved again at start of recursive fetch (upload)
        connection_path = os.path.join(self.conf['redfish_root'], "Fabrics/Pytest1")
        httpserver.expect_ordered_request(connection_path, method="GET").respond_with_json(tests_template.fabrics_pytest1b)
        # arm the httpserver with agent's response to GET on subordinate Switches collection
        connection_path = os.path.join(self.conf['redfish_root'], "Fabrics/Pytest1/Switches")
        httpserver.expect_ordered_request(connection_path, method="GET").respond_with_json(tests_template.fabrics_switch_collection)
        # arm the httpserver with agent's response to GET on Switch object  
        connection_path = os.path.join(self.conf['redfish_root'], "Fabrics/Pytest1/Switches/Pytest1")
        httpserver.expect_ordered_request(connection_path, method="GET").respond_with_json(tests_template.fabrics_switch_pytest1b)
        # arm the httpserver with client's response to the associated 3 ResourceCreated Events
        httpserver.expect_ordered_request("/", method="POST").respond_with_data("OK")
        httpserver.expect_ordered_request("/", method="POST").respond_with_data("OK")
        httpserver.expect_ordered_request("/", method="POST").respond_with_data("OK")
        #pdb.set_trace()
        resp = self.core.handle_event(tests_template.upload_event2)
        # check that 2nd agent uploaded the correct number of objects (3)
        upload_list =  test_utils.check_uploaded_objects(tests_template.upload_event2, self.conf['redfish_root'])
        assert len(upload_list) == 3
        assert len(httpserver.log) == 7
        # TODO
        # should verify the two objects got uploaded and written to the Sunfish DB
        # assert test_utils.check_delete(system_url) == True
        
        assert  len(resp) == 1
        #assert "Sunfish Internal Event Generation function Error" in caplog.text

    def test_event_resourceDeleted(self, httpserver: HTTPServer):
        # requires test_agent_upload runs successfully before calling this test
        #
        # This test checks:
        #   1)  when a ResourceDeleted event is sent to Sunfish core, 
        #       Sunfish removes the deleted resource (OriginOfCondition),
        #       Sunfish removes all the subordinates of the deleted resource
        #       and traverses the whole database and removing links to the deleted resources
        #       and also sends a ResourceDeleted event to any ResourceEvents subscribers
        #       AND sends a ResourceChanged event for any 
        #
        # arm the httpserver with subscriber's blind response to receipt of Events:
        #   for delete of /Fabrics/Pytest1
        #   for delete of /Fabrics/Pytest1/Switches
        #   for delete of /Fabrics/Pytest1/Switches/Pytest1
        #   for changes to /Fabrics
        #   for changes to /AggregationService/AggregationSources/xxxxxxxx
        httpserver.expect_ordered_request("/", method="POST").respond_with_data("OK")
        httpserver.expect_ordered_request("/", method="POST").respond_with_data("OK")
        httpserver.expect_ordered_request("/", method="POST").respond_with_data("OK")
        httpserver.expect_ordered_request("/", method="POST").respond_with_data("OK")
        httpserver.expect_ordered_request("/", method="POST").respond_with_data("OK")
        # send Sunfish core a ResourceDeleted event naming a fabric as OriginOfCondition
        resp = self.core.handle_event(tests_template.delete_fabric_event)
        # deleted objects should be removed from uploaded_objects list in the aggregationSource
        upload_list =  test_utils.check_uploaded_objects(tests_template.delete_fabric_event, self.conf['redfish_root'])
        assert len(upload_list) == 0
        assert len(httpserver.log) == 5
        # TODO
        # should verify the deleted fabric got removed from the Sunfish DB
        
        # handle_event() will return list of UUIDs to which the event was forwarded
        assert  len(resp) == 1


    def test_event_resourceDeleted2(self, httpserver: HTTPServer):
        # requires test_agent_upload runs successfully before calling this test
        #
        # This test checks:
        #   1)  when a ResourceDeleted event is sent to Sunfish core, 
        #       Sunfish removes the deleted resource (OriginOfCondition),
        #       Sunfish removes all the subordinates of the deleted resource
        #       and traverses the whole database and removing links to the deleted resources
        #       and also sends a ResourceDeleted event to any ResourceEvents subscribers
        #       AND sends a ResourceChanged event for any 
        #
        # arm the httpserver with subscriber's blind response to receipt of Events:
        #   for delete of /Fabrics/Pytest1
        #   for delete of /Fabrics/Pytest1/Switches
        #   for delete of /Fabrics/Pytest1/Switches/Pytest1
        #   for changes to /Fabrics
        #   for changes to /AggregationService/AggregationSources/xxxxxxxx
        httpserver.expect_ordered_request("/", method="POST").respond_with_data("OK")
        httpserver.expect_ordered_request("/", method="POST").respond_with_data("OK")
        httpserver.expect_ordered_request("/", method="POST").respond_with_data("OK")
        httpserver.expect_ordered_request("/", method="POST").respond_with_data("OK")
        httpserver.expect_ordered_request("/", method="POST").respond_with_data("OK")
        # send Sunfish core a ResourceDeleted event naming a fabric as OriginOfCondition
        # this is the renamed fabric for 2nd agent, 
        resp = self.core.handle_event(tests_template.delete_fabric_event2)
        # deleted objects should be removed from uploaded_objects list in the aggregationSource
        upload_list =  test_utils.check_uploaded_objects(tests_template.delete_fabric_event2, self.conf['redfish_root'])
        assert len(upload_list) == 0
        assert len(httpserver.log) == 5
        # TODO
        # should verify the deleted fabric got removed from the Sunfish DB
        
        assert  len(resp) == 1

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
