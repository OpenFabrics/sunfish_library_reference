# Copyright IBM Corp. 2023
# This software is available to you under a BSD 3-Clause License. 
# The full license terms are available here: https://github.com/OpenFabrics/sunfish_server_reference/blob/main/LICENSE

from flask import Flask, request
from sunfishcorelib.core import Core
from sunfishcorelib.exceptions import *

conf = {
    "storage_backend": "FS",
	"redfish_root": "/redfish/v1/",
	"backend_conf" : {
		"fs_root": "Resources"
	}
}

# initialize flask

app = Flask(__name__)
sunfish_core = Core(conf)

# Usa codici http
@app.route('/<path:resource>', methods=["GET"])
def get(resource):

	try:
		resp = sunfish_core.get_object(resource)
		return resp, 200
	except ResourceNotFound as e:
		return e.message, 404

@app.route('/<path:resource>', methods=["POST"])
def post(resource):
	try :
		resp = sunfish_core.create_object(request.json)
		return resp
	except CollectionNotSupported as e:
		return e.message, 405 # method not allowed
	except AlreadyExists as e:
		return e.message, 409 # Conflict

@app.route('/<path:resource>', methods=["PUT"])
def put(resource):
	try:
		data = request.json
		resp = sunfish_core.replace_object(data)
		return resp, 200
	except ResourceNotFound as e:
		return e.message, 404

@app.route('/<path:resource>', methods=["PATCH"])
def patch(resource):
	try:
		data = request.json
		resp = sunfish_core.patch_object(data)
		return resp, 200
	except ResourceNotFound as e:
		return e.message, 404

@app.route('/<path:resource>', methods=["DELETE"])
def delete(resource):
	try:
		resp = sunfish_core.delete_object(resource)
		return resp, 200
	except ResourceNotFound as e:
		return e.message, 404
	except ActionNotAllowed as e:
		return e.message, 403 # forbidden
	except InvalidPath as e:
		return e.message, 400

# we run app debugging mode
app.run(debug=False)