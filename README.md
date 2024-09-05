# Sunfishcore Library
The Sunfish library offers an interface that permits to handle Redfish objects via RESTful operations (read, write, put, patch and delete), and it manage the persistency of these objects. The interface has many implementations that manage different kinds of persistency.
Current available persistency implementations:
- File System (FS)

## Prerequisites for the library
The library requires:
- Python (version>=3.9)
- Poetry

## Installation

We suggest using a Python virtual environment.
To install the project requirements:
```
pip install -r requirements.txt
```

## To generate the installation file
From the directory ```sunfish_library_reference``` execute the following command:
```
make build
```


## Tests
To test this Library you need ```pytest``` to be installed.
To run the tests run the command 
```
make test
```

## Plugins

The Sunfish core library uses a plugin based mechanism for providing custom implementation of:

- Storage backends: implementation of the Sunfish storage interface used for controlling how RedFish storage are persisted. Plugins in this class must implement the `BackendInterface` class in  `storage.backend_interface`.
- Event handlers: Sunfish interactions with hardware agents and clients is implemented through RedFish events. When an event is received, users might want to execute a specific action depending on the specific event. These are provided via this plugin. Plugins in this class must implement the `EventHandlerInterface` class in  `events.event_handler_interface`.
- Objects handlers: Whenever a request for an object (get, create, replace, patch, delete) is received on the Sunfish external api the core library checks whether a special handler is to be executed for that specific object. Examples are an object is created and it requires other objects to be created in turn as a result. Plugins in this class must implement the `ObjectHandlerInterface` class in  `lib.object_handler_interface`.
- Objects managers: Sunfish keeps all objects in the form of a RedFish tree. Objects belong to a manager (e.g., a Sunfish agent) and this plugin provides the methods for Sungish to interact with the manager. Plugins in this class must implement the `ObjectManagerInterface` class in  `lib.object_manager_interface`.

Plugins are based on python's namespaced packages and are required to be placed in a specific folder at the top of your project. Only the actual plugins have a user defined name. Please see the below example. 

```commandline
─ sunfish_plugins
   ├── storage
   │   └──my_storage_package     <--- User defined
   │      ├── __init__.py
   │      └── my_storage_backend.py
   └── events_handlers
   │   └──my_handler_package     <--- User defined
   │      ├── __init__.py
   │      └── my_handler.py
   ├── objects_handlers
   │   └──my_objects_handler_package     <--- User defined
   │      ├── __init__.py
   │      └── my_objects_handler.py
   ├── objects_managers
   │   └──my_objects_manager_package     <--- User defined
   │      ├── __init__.py
   │      └── my_objects_manager.py
```

Please note no setup.py or project.toml should be placed in any of the plugins folders, including the pre-defined folders (i.e., sunfish_plugins, storage, events_handlers, objects_handlers, objects_managers). Failing to do so will make the plugins impossible to be discovered. 


When initializing the library, users can specify their implementation of their plugins as part of the sunfish configuration. See the below example. 

```python
sunfish_config = {
    
}
```

This plugin mechanism allows user to modify the standard behavior of Sunfish without having to modify the core library. Users can place the `sunifsh_plugins` folder at the top of their project that imports the sunfish core library and benefit from the flexibility of a plugin.

If no plugins are specified in the configuration, the Sunfish library will load the default implementations. See the code for more details. 

## Usage

When initializing the sunfish core library, users need to specify the **configuration parameters** as a dict  to be passed to the `init` function. The below snippet shows all the possible fields :
```json
{
    "redfish_root": "/redfish/v1/",
    "handlers": {
        "subscription_handler": "redfish"
    },
    "storage_backend": {
                "module_name": "storage.file_system_backend.backend_FS",
                "class_name": "BackendFS"
    },
    "events_handler": {
                "module_name": "events_handlers.redfish.redfish_event_handler",
                "class_name": "RedfishEventHandler"
    },
    "objects_handler": {
        "module_name": "objects_handlers.sunfish_server.redfish_object_handler",
        "class_name": "RedfishObjectHandler"
    },
    "objects_manager": {
        "module_name": "objects_managers.sunfish_agent.sunfish_agent_manager",
        "class_name": "SunfishAgentManager"
    }
}
```

Where:
- `redfish_root`: the root of the RedFish service served by the Sunfish core library.
- `subscripition_hadler`: Identifies how to handle subscriptions to events. At the moment only `redfish` is supported and follows the Redfish standard
- `storage_backend`: specifies the storage plugin to load.
- `events_handler`: specifies the event handling plugin to load.
- `objects_handler`: specifies the object handling plugin to load.
- `objects_manager`: specifies the object manager plugin to load.

All plugins must specify the module and class name via the `module_name` and `class_name` fields respectively.

Sunfish should be installed and imported in an existing Python project. To use it:
- instantiate an object Core(conf)
- use the methods _get_object_, _create_object_, _replace_object_, _patch_object_, _delete_object_ 
- these methods will raise the exception defined in `sunfish.lib.exceptions.py`

**IMPORTANT:** this Library assumes that the .json object are legal and well-formed according to the Redfish specification.

## License and copyright attribution
The code in this project is made available via the BSD 3-Clause License. See [LICENSE](https://github.com/OpenFabrics/sunfish_library_reference/blob/main/LICENSE) to access the full license terms. This project adopts the Developer Certificate of Origin (DCO) to certify that each commit was written by the author, or that the author has the rights necessary to contribute the code. All commits must include a DCO which looks like this: Signed-off-by: Joe Smith <joe.smith@email.com>. Specifically, we utilize the [Developer Certificate of Origin Version 1.1] (https://github.com/OpenFabrics/sunfish_library_reference/blob/main/DCO). The project requires that the name used is your real name. Neither anonymous contributors nor those utilizing pseudonyms will be accepted.
