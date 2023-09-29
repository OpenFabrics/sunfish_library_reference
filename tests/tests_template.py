# Copyright IBM Corp. 2023
# This software is available to you under a BSD 3-Clause License. 
# The full license terms are available here: https://github.com/OpenFabrics/sunfish_library_reference/blob/main/LICENSE

test_post_zones_1 = {
    "@odata.type": "#Zone.v1_6_1.Zone",
    "Id": "1",
    "Name": "CXL Zone 1",
    "Description": "CXL Zone 1",
    "Status": {
        "State": "Enabled",
        "Health": "OK"
    },
    "ZoneType": "ZoneOfEndpoints",
    "Links": {
        "Endpoints": [
            {
                "@odata.id": "/redfish/v1/Fabrics/CXL/Endpoints/I1"
            },
            {
                "@odata.id": "/redfish/v1/Fabrics/CXL/Endpoints/T1"
            },
            {
                "@odata.id": "/redfish/v1/Fabrics/CXL/Endpoints/1"
            }
        ]
    },
    "Oem": {},
    "@odata.id": "/redfish/v1/Fabrics/CXL/Zones/1"
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
    "@odata.type": "#Zone.v1_6_1.Zone",
    "Id": "1",
    "Name": "CXL Zone 1",
    "Description": "CXL Zone 1",
    "Status": {
        "State": "Disabled",
        "Health": "OK"
    },
    "ZoneType": "ZoneOfEndpoints",
    "Links": {
        "Endpoints": [
            {
                "@odata.id": "/redfish/v1/Fabrics/CXL/Endpoints/I1"
            },
            {
                "@odata.id": "/redfish/v1/Fabrics/CXL/Endpoints/T1"
            },
            {
                "@odata.id": "/redfish/v1/Fabrics/CXL/Endpoints/1"
            }
        ]
    },
    "Oem": {},
    "@odata.id": "/redfish/v1/Fabrics/CXL/Zones/1"
}


test_patch = {
    "Status": {
        "State": "Enabled",
        "Health": "OK"
    },
    "@odata.id": "/redfish/v1/Fabrics/CXL/Zones/1"
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