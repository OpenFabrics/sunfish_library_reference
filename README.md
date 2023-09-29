# Sunfishcore Library
The Sunfishcore library offers an interface that permits to handle Redfish objects via RESTful operations (read, write, put, patch and delete), and it manage the persistency of these objects. The interface has many implementations that manage different kinds of persistency.
Current available persistency implementations:
- File System (FS)

## Prerequisites for the library
The library requires:
- Python (version>=3.9)
- Poetry

## To generate the installation file
From the directory ```sunfish_library_reference``` execute the following command:
```
poetry build #This command will create the .whl file

```

## Installation

We suggest using a Python virtual environment. 
To install the project requirements:
```
pip install -r requirements.txt
```
To install sunfishcorelib you need to use the file .whl:
```
pip3 install dist/sunfishcore-0.1.0-py3-none-any.whl

```

## Tests
To test this Library you need ```pytest``` to be installed.
To run the tests run the command 
```
python3 -m pytest test_sunfishcore_library.py -vvvv
```

## Usage
To use sunfishcorelib you need to specify the **configuration parameters**, an example could be:
```
conf = {
    "storage_backend": "FS",
	"redfish_root": "/redfish/v1/",
	"backend_conf" : {
		"fs_root": "Resources/Sunfish"
	}
}
```

where:
- _storage_backend_ specifies the persistency implementation that you want to use
- _redfish_root_ specifies the Redfish version that must be included in all the requests
- _backend_conf[fs_root]_ specifies the root directory of Redfish objects' file system

sunfishcorelib should be implemented in an existing Python project. To use it:
- instantiate an object Core(conf)
- use the methods _get_object_, _create_object_, _replace_object_, _patch_object_, _delete_object_ 
- these methods will raise the exception defined in `sunfishcorelib.exceptions.py`

**IMPORTANT:** this Library assumes that the .json object are legal and well-formed according to the Redfish specification.

## License and copyright attribution
The code in this project is made available via the BSD 3-Clause License. See [LICENSE](https://github.com/OpenFabrics/sunfish_library_reference/blob/main/LICENSE) to access the full license terms. This project adopts the Developer Certificate of Origin (DCO) to certify that each commit was written by the author, or that the author has the rights necessary to contribute the code. All commits must include a DCO which looks like this: Signed-off-by: Joe Smith <joe.smith@email.com>. Specifically, we utilize the [Developer Certificate of Origin Version 1.1] (https://github.com/OpenFabrics/sunfish_library_reference/blob/main/DCO). The project requires that the name used is your real name. Neither anonymous contributors nor those utilizing pseudonyms will be accepted.
