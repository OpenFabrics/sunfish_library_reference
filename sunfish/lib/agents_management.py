# Copyright IBM Corp. 2024
# This software is available to you under a BSD 3-Clause License.
# The full license terms are available here: https://github.com/OpenFabrics/sunfish_library_reference/blob/main/LICENSE

import json
import logging
import string
import requests

from sunfish.lib.exceptions import AgentForwardingFailure
from sunfish.models.types import *
import sunfish

logger = logging.getLogger(__name__)

agent_request_headers = {
    "Content-Type": "application/json"
}


class Agent:
    agent_request_headers = {
        "Content-Type": "application/json"
    }

    def __init__(self, sunfish_core: 'sunfish.lib.core.Core', redfish_path: string):
        self.redfish_path: string = redfish_path
        self.sunfish_core: 'sunfish.lib.core.Core' = sunfish_core
        self.aggregation_source: dict = self.sunfish_core.storage_backend.read(redfish_path)

    def get_id(self) -> string:
        return self.aggregation_source["@odata.id"]

    @classmethod
    def is_agent_managed(cls, sunfish_core: 'sunfish.lib.core.Core', path: string):
        # if this is a top level resource, there's no need to check for the agent as no agent can own top level ones.
        # Example of top levels is Systems, Chassis, etc...
        level = len(path.replace(sunfish_core.conf["redfish_root"], "").split("/"))
        if level == 1:
            return None

        collection = sunfish_core.storage_backend.read(path)

        logger.debug(f"Checking if the object {path} is managed by an Agent")
        if "Oem" in collection and "Sunfish_RM" in collection["Oem"]:
            agent = collection["Oem"]["Sunfish_RM"]["ManagingAgent"]["@odata.id"]
            return Agent(sunfish_core, agent)

        return None

    def _forward_get_request(self, path: string) -> dict:
        resource_uri = self.aggregation_source["HostName"] + "/" + path

        logger.debug(f"Forwarding resource GET request {resource_uri}")
        try:
            r = requests.get(resource_uri, headers=self.agent_request_headers)
            if r.status_code == 200:
                logger.debug(f"GET request was successful. status code: {r.status_code}, reason {r.reason}")
                logger.debug(f"Response payload:\n {json.dumps(r.json(), indent=2)}")
                return r.json()
            else:
                logger.debug(f"GET request was unsuccessful. status code: {r.status_code}, reason {r.reason}")
                raise AgentForwardingFailure(f"creating object {resource_uri} ", r.status_code, r.reason)
        except requests.exceptions.RequestException as e:
            logger.error("RequestException")
            logger.error(e)
            raise e

    def _forward_create_request(self, path: string, payload: dict) -> dict:
        resource_uri = self.aggregation_source["HostName"] + "/" + path

        logger.debug(f"Forwarding resource CREATE request {resource_uri}")
        try:
            r = requests.post(resource_uri, headers=self.agent_request_headers, data=json.dumps(payload))
            if r.status_code == 200:
                logger.debug(f"CREATE request was successful. status code: {r.status_code}, reason {r.reason}")
                logger.debug(f"Response payload:\n {json.dumps(r.json(), indent=2)}")
                return r.json()
            else:
                logger.debug(f"CREATE request was unsuccessful. status code: {r.status_code}, reason {r.reason}")
                raise AgentForwardingFailure(f"creating object {resource_uri} ", r.status_code, r.reason)
        except requests.exceptions.RequestException as e:
            logger.error("RequestException")
            logger.error(e)
            raise e

    def _forward_delete_request(self, path: string) -> dict:
        resource_uri = self.aggregation_source["HostName"] + "/" + path

        logger.debug(f"Forwarding resource DELETE request {resource_uri}")
        try:
            r = requests.delete(resource_uri, headers=self.agent_request_headers)
            if r.status_code in [200, 202, 204]:
                logger.debug(f"DELETE request was successful. status code: {r.status_code}, reason {r.reason}")
                return {}
            else:
                logger.debug(f"DELETE request was unsuccessful. status code: {r.status_code}, reason {r.reason}")
                raise AgentForwardingFailure(f"deleting object {resource_uri} ", r.status_code, r.reason)
        except requests.exceptions.RequestException as e:
            logger.error(e)
            raise e

    def _forward_patch_request(self, path: string, payload: dict) -> dict:
        resource_uri = self.aggregation_source["HostName"] + "/" + path

        logger.debug(f"Forwarding resource PATCH request {resource_uri}")
        try:
            r = requests.patch(resource_uri, headers=self.agent_request_headers, data=json.dumps(payload))
            if r.status_code == 200:
                logger.debug(f"PATCH request was successful. status code: {r.status_code}, reason {r.reason}")
                logger.debug(f"Response payload:\n {json.dumps(r.json(), indent=2)}")
                return r.json()
            else:
                logger.debug(f"PATCH request was unsuccessful. status code: {r.status_code}, reason {r.reason}")
                raise AgentForwardingFailure(f"patching object {resource_uri} ", r.status_code, r.reason)
        except requests.exceptions.RequestException as e:
            logger.error(e)
            raise e

    def _forward_replace_request(self, path: string, payload: dict) -> dict:
        resource_uri = self.aggregation_source["HostName"] + "/" + path

        logger.debug(f"Forwarding resource REPLACE request {resource_uri}")
        try:
            r = requests.patch(resource_uri, headers=self.agent_request_headers, data=json.dumps(payload))
            if r.status_code == 200:
                logger.debug(f"REPLACE request was successful. status code: {r.status_code}, reason {r.reason}")
                logger.debug(f"Response payload:\n {json.dumps(r.json(), indent=2)}")
                return r.json()
            else:
                logger.debug(f"REPLACE request was unsuccessful. status code: {r.status_code}, reason {r.reason}")
                raise AgentForwardingFailure(f"replacing object {resource_uri} ", r.status_code, r.reason)
        except requests.exceptions.RequestException as e:
            logger.error(e)
            raise e

    def forward_request(self, request: SunfishRequestType, path: string, payload: dict = None) -> dict:
        """
        Args:
            path: the path of the resource associated with the request
            request: a string representing the request to pe forwarded [GET, CREATE, DELETE, PATCH, UPDATE]
            payload: a dict containing the payload of the request to be forwarded

        Returns:
             A dict containing the payload response associated with the request.
        Raises:
            AgentForwardingFailure: in case the request fails for reasons that are beyond network connectivity,
                                   such as non existing path, illegal operations, malformed payload, etc.
            requests.exceptions.RequestException: In case of connection related issues
        """
        try:
            if request == SunfishRequestType.GET:
                return self._forward_get_request(path)
            elif request == SunfishRequestType.CREATE:
                if payload is None:
                    logger.error("CREATE request payload missing")
                    raise AgentForwardingFailure("CREATE", -1, "Missing payload")
                return self._forward_create_request(path, payload)
            elif request == SunfishRequestType.DELETE:
                return self._forward_delete_request(path)
            elif request == SunfishRequestType.PATCH:
                if payload is None:
                    logger.error("PATCH request payload missing")
                    raise AgentForwardingFailure("PATCH", -1, "Missing payload")
                return self._forward_patch_request(path, payload)
            elif request == SunfishRequestType.REPLACE:
                if payload is None:
                    logger.error("REPLACE request payload missing")
                    raise AgentForwardingFailure("REPLACE", -1, "Missing payload")
                return self._forward_replace_request(path, payload)
        except AgentForwardingFailure as e:
            raise e
        except requests.exceptions.RequestException as e:
            raise e
