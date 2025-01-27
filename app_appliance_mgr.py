# Copyright IBM Corp. 2023
# This software is available to you under a BSD 3-Clause License. 
# The full license terms are available here: https://github.com/OpenFabrics/sunfish_server_reference/blob/main/LICENSE
import os
import traceback
import json

from flask import Flask, request, render_template
from sunfish.lib.core import Core
from sunfish.lib.exceptions import *
import logging
import requests

FORMAT = "[%(filename)s:%(lineno)s - %(funcName)20s() ] %(message)s"
logging.basicConfig(format=FORMAT, level=logging.DEBUG)

sunfish_request_headers = {
    "Content-Type": "application/json"
}

eventURI = "http://127.0.0.1:5000/EventListener"
sunfishSubscriber = "/redfish/v1/EventService/Subscriptions/SunfishServer"

service_string = "test this string"

logger = logging.getLogger("Agent")
conf = {
    "storage_backend": {
        "module_name": "storage.my_storage_package.my_storage_backend",
        "class_name": "StorageBackend"
	},
	"redfish_root": "/redfish/v1/",
	"backend_conf" : {
		"fs_root": "Resources",
		"fs_private": "Resources/SunfishPrivate",
		"subscribers_root": "EventService/Subscriptions",
		"clean_resource_path": "../am_agent_Resources"
	},
	"handlers": {
		"subscription_handler": "redfish",
		"event_handler": "redfish"
	}
}

# hardcoded registration event
# requires the OriginOfCondition object exist in Agent's Resource tree
reg_event = {
    "@odata.type": "#Event.v1_7_0.Event",
    "Name": "AggregationSourceDiscovered",
    "Context": "",
    "Events": [ {
        "Severity": "Ok",
        "Message": "A aggregation source of connection method",
        "MessageId": "ResourceEvent.1.x.AggregationSourceDiscovered",
        "MessageArgs": [ "Redfish", "http://127.0.0.1:5002" ],
        "OriginOfCondition": {
            "@odata.id": "/redfish/v1/AggregationService/ConnectionMethods/CXL2"
        }
    } ]
}

upload_event = {
    "@odata.type": "#Event.v1_7_0.Event",
    "Name": "Fabric Created",
    "Context": "None",
    "Events": [ {
        "Severity": "Ok",
        "Message": "New Fabric Created ",
        "MessageId": "ResourceEvent.1.x.ResourceCreated",
        "MessageArgs": [ ],
        "OriginOfCondition": {
            "@odata.id": "/redfish/v1/Fabrics/CXL"
        }
    } ]
}

# initialize flask

template_dir = os.path.abspath('./templates_web')
app = Flask(__name__, template_folder=template_dir)
sunfish_core = Core(conf)

@app.route('/browse')
def browse():
    return render_template('browse.html')


def reg_agent():

        logger.debug(f"Sending Register Event to {eventURI}")
        logger.debug(f"data \n{reg_event}")
        try:
            r = requests.post(eventURI, headers=sunfish_request_headers, data=json.dumps(reg_event))
            if r.status_code == 200:
                logger.debug(f"Register request was successful. status code: {r.status_code}, reason {r.reason}")
                logger.debug(f"Response payload:\n {json.dumps(r.json(), indent=2)}")
                return [r.reason,r.status_code]
            else:
                logger.debug(f"Register request was unsuccessful. status code: {r.status_code}, reason {r.reason}")
                pass
                return 500
        except requests.exceptions.RequestException as e:
            logger.error("RequestException")
            logger.error(e)
            raise e

def upload_agent():

        logger.debug(f"Sending Upload Event to {eventURI}")
        logger.debug(f"data \n{upload_event}")
        try:
            subscriber = sunfish_core.get_object(sunfishSubscriber)
            upload_event["Context"] = subscriber["Context"]
            logger.debug(f"event to send \n{upload_event}")
            r = requests.post(eventURI, headers=sunfish_request_headers, data=json.dumps(upload_event))
            if r.status_code == 200:
                logger.debug(f"upload request was successful. status code: {r.status_code}, reason {r.reason}")
                logger.debug(f"Response payload:\n {json.dumps(r.json(), indent=2)}")
                return [r.status_code,r.reason]
            else:
                logger.debug(f"upload request was unsuccessful. status code: {r.status_code}, reason {r.reason}")
                pass
                return 500
        except requests.exceptions.RequestException as e:
            logger.error("RequestException")
            logger.error(e)
            raise e

# Usa codici http
@app.route('/<path:resource>', methods=["GET"], strict_slashes=False)
def get(resource):
	logger.debug(f"GET on: {request.path}")
	try:
		resp = sunfish_core.get_object(request.path)
		return resp, 200
	except ResourceNotFound as e:
		return e.message, 404



@app.route('/<path:resource>', methods=["POST"], strict_slashes=False)
def post(resource):
	logger.debug("POST")
	logger.debug(f"resource = {resource}")
	try :
		if resource == "EventListener":
			resp = sunfish_core.handle_event(request.json)
		elif resource =="AgentRegister":
			resp = reg_agent() 
		elif resource =="AgentUpload":
			resp = upload_agent()
		elif resource == "ResetResources":
			resp = sunfish_core.storage_backend.reset_resources(conf['backend_conf']['fs_root'],conf['backend_conf']['clean_resource_path'])
		else:
			resp = sunfish_core.create_object(request.path, request.json)
		return resp
	except CollectionNotSupported as e:
		return e.message, 405 # method not allowed
	except AlreadyExists as e:
		return e.message, 409 # Conflict
	except PropertyNotFound as e:
		return e.message, 400

@app.route('/<path:resource>', methods=["PUT"], strict_slashes=False)
def put(resource):
	try:
		data = request.json
		resp = sunfish_core.replace_object(data)
		return resp, 200
	except ResourceNotFound as e:
		return e.message, 404

@app.route('/<path:resource>', methods=["PATCH"], strict_slashes=False)
def patch(resource):
	try:
		logger.debug("PATCH")
		data = request.json
		resp = sunfish_core.patch_object(path=request.path, payload=data)
		return resp, 200
	except ResourceNotFound as e:
		return e.message, 404
	except Exception:
		traceback.print_exc()

@app.route('/<path:resource>', methods=["DELETE"], strict_slashes=False)
def delete(resource):
	try:
		resp = sunfish_core.delete_object(request.path)
		return resp, 200
	except ResourceNotFound as e:
		return e.message, 404
	except ActionNotAllowed as e:
		return e.message, 403 # forbidden
	except InvalidPath as e:
		return e.message, 400

# we run app debugging mode
logger = logging.getLogger("Agent running")
app.run(debug=False)
