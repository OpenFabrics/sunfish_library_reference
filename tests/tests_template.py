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
        "State": "Disabled",
        "Health": "OK"
    }
}

test_update_exception = {
    "@odata.id": "/redfish/v1/Systems/-1",
    "@odata.type": "#ComputerSystem.1.00.0.ComputerSystem",
    "Id": "1234",
    "Name": "Compute Node 1234",
    "SystemType": "Physical",
    "Manufacturer": "Manufacturer Name",
    "Model": "Model Name",
    "SKU": "",
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
    "@odata.type": "#EventDestination.v1_13_2.EventDestination",
    "Destination": "http://localhost:8080",
    "EventFormatType": "Event",
    "RegistryPrefixes": [
        "ResourceEvent"
    ]
}
sub2 = {
    "@odata.type": "#EventDestination.v1_13_2.EventDestination",
    "Destination": "http://localhost:8080",
    "EventFormatType": "Event",
    "ExcludeRegistryPrefixes": [
        "ResourceEvent"
    ]
}
sub3 = {
    "@odata.type": "#EventDestination.v1_13_2.EventDestination",
    "Destination": "http://localhost:8080",
    "EventFormatType": "Event",
    "RegistryPrefixes": [
        "ResourceEvent"
    ],
    "ExcludeMessageIds": [
        "ResourceEvent.1.0.ResourceCreated"
    ]
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
            "MessageId": "ResourceEvent.1.0.ResourceCreated",
            "MessageArgs": [
            ]
        }
    ]
}