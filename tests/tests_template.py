# Copyright IBM Corp. 2023
# This software is available to you under a BSD 3-Clause License. 
# The full license terms are available here: https://github.com/OpenFabrics/sunfish_library_reference/blob/main/LICENSE

setup_subscriptions = {
    "@odata.id": "/redfish/v1/EventService/Subscriptions",
    "@odata.type": "#EventService/SubscriptionsCollection.EventService/SubscriptionsCollection",
    "Members": [
        
    ],
    "Members@odata.count": 0,
    "Name": "EventService/Subscriptions Collection"
}

test_post_system = {
    "@odata.type": "#ComputerSystem.1.00.0.ComputerSystem",
    "@odata.id": "/redfish/v1/Systems/1",
    "Id": "1",
    "Boot": {
        "BootSourceOverrideEnabled": "Once",
        "BootSourceOverrideSupported": [
            "None",
            "Pxe",
            "Floppy",
            "Cd",
            "Usb"
        ],
        "BootSourceOverrideTarget": "Pxe",
        "UefiTargetBootSourceOverride": "uefi device path"
    },
    "FabricAdapters": [
        {
            "@odata.id": "/redfish/1/Systems/1234/FabricAdapters"
        }
    ],
    "IndicatorLED": "Off",
    "Links": {
        "Chassis": [
            {
                "@odata.id": "/redfish/v1/Chassis/1"
            }
        ]
    },
    "Manufacturer": "Manufacturer Name",
    "Memory": {
        "Status": {
            "Health": "OK",
            "HealthRollUp": "OK",
            "State": "Disabled"
        },
        "TotalSystemMemoryGB": 12
    },
    "Model": "Model Name",
    "Name": "Compute Node 1234",
    "Power": "On",
    "Processors": {
        "Count": 4,
        "Model": "Multi-Core Intel(R) Xeon(R) processor 7xxx Series",
        "Status": {
            "Health": "OK",
            "HealthRollUp": "OK",
            "State": "Enabled"
        }
    },
    "SKU": "sku",
    "Status": {
        "Health": "OK",
        "HealthRollUp": "OK",
        "State": "Enabled"
    },
    "SystemType": "Physical"
}

test_post_ports = {
    "@odata.type": "#Port.v1_7_0.Port",
    "Id": "D1",
    "Name": "CXL Port 1",
    "Description": "CXL Downstream Port 1 in switch",
    "Status": {
        "State": "Enabled",
        "Health": "OK",
        "HealthRollup": "OK"
    },
    "PortId": "D1",
    "RemotePortId": "4C-1D-96-FF-FE-DD-D8-D1",
    "PortProtocol": "CXL",
    "CurrentProtocolVersion": "2.0",
    "CapableProtocolVersions": [
        "1.1", "2.0"
    ],
    "PortType": "DownstreamPort",
    "PortMedium": "Optical",
    "CurrentSpeedGbps": 256,
    "Width": 8,
    "MaxSpeedGbps": 512,
    "ActiveWidth": 16,
    "LinkState": "Enabled",
    "LinkStatus": "LinkUp",
    "InterfaceEnabled": True,
    "LinkNetworkTechnology": "PCIe",
    "Links": {
        "AssociatedEndpoints": [
			{
                "@odata.id": "/redfish/v1/Fabrics/CXL/Endpoints/T1"
            }
        ],
        "ConnectedPorts": [
            {
                "@odata.id": "/redfish/v1/Chassis/PCXL1/FabricAdapters/1/Ports/1"
            }
        ]
    },
    "Oem": {},
    "@odata.id": "/redfish/v1/Fabrics/CXL/Switches/CXL/Ports/D1"
}

test_collection = {
    "@odata.type": "#ComputerSystemCollection.ComputerSystemCollection",
    "Name": "Computer System Collection",
    "Members@odata.count": 0,
    "Members": [],
    "@odata.id": "/redfish/v1/Systems"
}

test_put = {
    "@odata.type": "#ComputerSystem.1.00.0.ComputerSystem",
    "Boot": {
        "BootSourceOverrideEnabled": "Once",
        "BootSourceOverrideSupported": [
            "None"
        ],
        "BootSourceOverrideTarget": "Pxe",
        "UefiTargetBootSourceOverride": "uefi device path"
    },
    "FabricAdapters": [
        {
            "@odata.id": "/redfish/1/Systems/1234/FabricAdapters"
        }
    ],
    "IndicatorLED": "Off",
    "Memory": {
        "Status": {
            "Health": "OK",
            "HealthRollUp": "OK",
            "State": "Disabled"
        },
        "TotalSystemMemoryGB": 8
    },
    "Model": "Model Name",
    "Name": "Compute Node PUT",
    "Power": "On",
    "Processors": {
        "Count": 4,
        "Model": "Multi-Core Intel(R) Xeon(R) processor 7xxx Series",
        "Status": {
            "Health": "OK",
            "HealthRollUp": "OK",
            "State": "Enabled"
        }
    },
    "SKU": "sku",
    "Status": {
        "Health": "OK",
        "HealthRollUp": "OK",
        "State": "Enabled"
    },
    "SystemType": "Physical"
}

test_patch = {
    "@odata.type": "#ComputerSystem.1.0.0.ComputerSystem",
    "Status": {
        "State": "Enabled",
        "Health": "OK"
    }
}

test_put_exception = {
    "@odata.id": "/redfish/v1/Systems/1",
    "Memory": {
        "TotalSystemMemoryGB": 12,
        "Status": {
            "State": "Disabled",
            "Health": "OK",
            "HealthRollUp": "OK"
        }
    }
}

test_update_exception = {
    "@odata.id": "/redfish/v1/Systems/-1",
    "Memory": {
        "TotalSystemMemoryGB": 12,
        "Status": {
            "State": "Disabled",
            "Health": "OK",
            "HealthRollUp": "OK"
        }
    }
}

# SUBSCRIPTIONS
sub1 = {
    "@odata.type": "#EventDestination.EventDestination",
    "Destination": "http://localhost:8080",
    "EventFormatType": "Event",
    "RegistryPrefixes": [
        "TaskEvent"
    ]
    ,
    "ExcludeRegistryPrefixes": [
        "Basic"
    ],
    "ExcludeMessageIds": [
        "TaskEvent.1.0.TaskCancelled"
    ]
}

sub2 = {
    "@odata.type": "#EventDestination.EventDestination",
    "Destination": "http://localhost:8080",
    "EventFormatType": "Event",
    "RegistryPrefixes": [
        "Basic"
    ],
    "MessageIds": [
        "TaskEvent.1.0.TaskCancelled"
    ],
    "ExcludeMessageIds": [
        "BaseEvent.1.0.AccessDenied"
    ]
}

sub3 = {
    "@odata.type": "#EventDestination.EventDestination",
    "Destination": "http://localhost:8080",
    "EventFormatType": "Event",
    "RegistryPrefixes": [
        "Basic"
    ],
    "ExcludeRegistryPrefixes": [
        "ResourceEvent",
        "TaskEvent"
    ],
    "ResourceTypes": [
        "ComputerSystem"
    ],
    "OriginResources": [{
        "@odata.id": "/redfish/v1/Systems/1"
    }],
    "SubordinateResources": "True"
}

wrong_sub = {
    "@odata.type": "#EventDestination.v1_13_2.EventDestination",
    "Destination": "http://wrong_dest:8080",
    "EventFormatType": "Event",
    "RegistryPrefixes": [
        "ResourceEvent"
    ]
}

event = {
    "@odata.type": "#Event.v1_7_0.Event",
    "Name": "Event Array",
    "Context": "ContosoWebClient",
    "Events": [
        {
            "EventId": "4593",
            "Severity": "OK",
            "Message": "The resource has been created successfully.",
            "MessageId": "ResourceEvent.1.0.Prova",
            "MessageArgs": [
            ]
        }
    ]
}

task_event_cancelled = {
    "@odata.type": "#Event.v1_7_0.Event",
    "Name": "Task Event",
    "Context": "ContosoWebClient",
    "Events": [
        {
            "EventId": "1234",
            "Severity": "Warning",
            "Message": "Work on the task with Id 1234 has been halted prior to completion due to an explicit request.",
            "MessageId": "TaskEvent.1.0.TaskCancelled",
            "MessageArgs": [
                "1234"
            ]
        }
    ]
}

base_event_access_denied = {
    "@odata.type": "#Event.v1_7_0.Event",
    "Name": "Base Event",
    "Context": "ContosoWebClient",
    "Events": [
        {
            "EventId": "5678",
            "Severity": "Critical",
            "Message": "While attempting to establish a connection to 5678, the service denied access.",
            "MessageId": "BaseEvent.1.0.AccessDenied",
            "MessageArgs": [
                "5678"
            ]
        }
    ]
}

event_resource_type_system = {
    "@odata.type": "#Event.v1_7_0.Event",
    "Name": "Power event",
    "Context": "",
    "Events": [ {
        "EventType": "Other",
        "EventId": "0987",
        "Severity": "Ok",
        "Message": "A aggregation source of connection method Redfish located at http://127.0.0.1:5001 has been discovered.",
        "MessageId": "Power.1.0.CircuitPoweredOn",
        "MessageArgs": [ "Redfish", "http://127.0.0.1:5001" ],
        "OriginOfCondition": {
            "@odata.id": "/redfish/v1/Systems/1"
        }
    } ]
}

event_aggregation_source_discovered = {
    "@odata.type": "#Event.v1_7_0.Event",
    "Name": "AggregationSourceDiscovered",
    "Context": "",
    "Events": [ {
        "EventType": "Other",
        "EventId": "4594",
        "Severity": "Ok",
        "Message": "A aggregation source of connection method Redfish located at http://127.0.0.1:5001 has been discovered.",
        "MessageId": "Foo.1.0.AggregationSourceDiscovered",
        "MessageArgs": [ "Redfish", "http://127.0.0.1:5001" ],
        "OriginOfCondition": {
            "@odata.id": "/redfish/v1/AggregationService/ConnectionMethods/CXL"
        }
    } ]
}

aggregation_source = {
    "@Redfish.Copyright": "Copyright 2014-2021 SNIA. All rights reserved.",
    "@odata.id": "/redfish/v1/AggregationService/AggregationSources/afd9e24c-20d1-479e-be24-4ad6a62f7197",
    "@odata.type": "#AggregationSource.v1_2_afd9e24c-20d1-479e-be24-4ad6a62f7197.AggregationSource",
    "HostName": "http://localhost:8080",
    "Id": "afd9e24c-20d1-479e-be24-4ad6a62f7197",
    "Links": {
        "ConnectionMethod": {
            "@odata.id": "/redfish/v1/AggregationService/ConnectionMethods/CXL"
        },
        "ResourcesAccessed": [
        ]
    },
    "Name": "Agent afd9e24c-20d1-479e-be24-4ad6a62f7197"
}

test_fabric = {
    "@odata.id": "/redfish/v1/Fabrics/CXL",
    "@odata.type": "#Fabric.v1_2_2.Fabric",
    "Connections": {
        "@odata.id": "/redfish/v1/Fabrics/CXL/Connections"
    },
    "Description": "CXL Fabric",
    "Endpoints": {
        "@odata.id": "/redfish/v1/Fabrics/CXL/Endpoints"
    },
    "FabricType": "CXL",
    "Id": "CXL",
    "Name": "CXL Fabric",
    "Oem": {
        "Sunfish_RM": {
            "@odata.type": "#SunfishExtensions.v1_0_0.ResourceExtensions",
            "ManagingAgent": {
                "@odata.id": "/redfish/v1/AggregationService/AggregationSources/afd9e24c-20d1-479e-be24-4ad6a62f7197"
            }
        }
    },
    "Status": {
        "Health": "OK",
        "State": "Enabled"
    },
    "Switches": {
        "@odata.id": "/redfish/v1/Fabrics/CXL/Switches"
    },
    "Zones": {
        "@odata.id": "/redfish/v1/Fabrics/CXL/Zones"
    }
}

test_connection_cxl_fabric = {
    "@odata.id": "/redfish/v1/Fabrics/CXL/Connections/12",
    "@odata.type": "#Connection.v1_1_0.Connection",
    "ConnectionType": "Memory",
    "Description": "CXL Connection 12 Information",
    "Id": "12",
    "Links": {
        "InitiatorEndpoints": [
            {
                "@odata.id": "/redfish/v1/Fabrics/CXL/Endpoints/I2"
            }
        ],
        "TargetEndpoints": [
            {
                "@odata.id": "/redfish/v1/Fabrics/CXL/Endpoints/T2"
            }
        ]
    },
    "MemoryChunkInfo": [
        {
            "AccessCapabilities": [
                "Read",
                "Write"
            ],
            "MemoryChunk": {
                "@odata.id": "/redfish/v1/Chassis/PCXL2/MemoryDomains/1/MemoryChunks/1"
            }
        }
    ],
    "Status": {
        "Health": "OK",
        "HealthRollup": "OK",
        "State": "Enabled"
    }
}

test_response_connection_cxl_fabric = {
    "@odata.id": "/redfish/v1/Fabrics/CXL/Connections/12",
    "@odata.type": "#Connection.v1_1_0.Connection",
    "ConnectionType": "Memory",
    "Description": "CXL Connection 12 Information",
    "Id": "12",
    "Links": {
        "InitiatorEndpoints": [
            {
                "@odata.id": "/redfish/v1/Fabrics/CXL/Endpoints/I2"
            }
        ],
        "TargetEndpoints": [
            {
                "@odata.id": "/redfish/v1/Fabrics/CXL/Endpoints/T2"
            }
        ]
    },
    "MemoryChunkInfo": [
        {
            "AccessCapabilities": [
                "Read",
                "Write"
            ],
            "MemoryChunk": {
                "@odata.id": "/redfish/v1/Chassis/PCXL2/MemoryDomains/1/MemoryChunks/1"
            }
        }
    ],
    "Status": {
        "Health": "OK",
        "HealthRollup": "OK",
        "State": "Enabled"
    },
    "Oem": {
        "Sunfish_RM": {
            "@odata.type": "#SunfishExtensions.v1_0_0.ResourceExtensions",
            "ManagingAgent": {
                "@odata.id": "/redfish/v1/AggregationService/AggregationSources/afd9e24c-20d1-479e-be24-4ad6a62f7197"
            }
        }
    }
}

resource_event_no_context = {
    "@odata.type": "#Event.v1_7_0.Event",
    "Id": "2",
    "Name": "Fabric Created",
    "Context": "",
    "Events": [{
        "EventType": "Other",
        "EventId": "4595",
        "Severity": "OK",
        "Message": "New Resource Created ",
        "MessageId": "ResourceEvent.1.0.ResourceCreated",
        "MessageArgs": [],
        "OriginOfCondition": {
            "@odata.id": "/redfish/v1/Fabrics/CXL"
        }
    }]
}