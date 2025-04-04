#! /bin/bash
set -e
# reset the Sunfish Server resources
echo  "curl -X POST -H "Content-Type: application/json" localhost:5000/ResetResources"
 curl -X POST -H "Content-Type: application/json" localhost:5000/ResetResources

# reset the sideloader Agent Server (the FM agent) resources
 echo  "curl -X POST -H "Content-Type: application/json" localhost:5001/ResetResources"
 curl -X POST -H "Content-Type: application/json" localhost:5001/ResetResources

# reset the appliance_manager Agent Server (the AM agent) resources
#if not using a 2nd Agent API, won't need to reset it
 echo  "curl -X POST -H "Content-Type: application/json" localhost:5002/ResetResources"
 curl -X POST -H "Content-Type: application/json" localhost:5002/ResetResources


echo "register sideloader (proxy for H3) agent"
curl -X POST -H "Content-Type: application/json" -d@register_H3_API.json localhost:5000/EventListener

echo "retrieve H3 API UUID assigned to sideloader agent"
curl -X GET -H "Content-Type: application/json"  localhost:5001/redfish/v1/EventService/Subscriptions/SunfishServer | jq | tee ./H3_Subscriber_ID.json

echo "extract sideloader UUID"
H3_UUID=$(jq -r '.Context' H3_Subscriber_ID.json)
echo $H3_UUID

echo "find AggregationSource $H3_UUID in Sunfish Resources"
ag_src_file="../../sc24_sunfish_server/Resources/AggregationService/AggregationSources/$H3_UUID/index.json"
echo $ag_src_file

real_H3_host='http://125.227.151.211:27700'
echo $real_H3_host
sideloader_hostname=$(jq -r '.HostName' $ag_src_file)
echo $sideloader_hostname

# Update the HostName value using sed (in place)
sed -i "s|$sideloader_hostname|$real_H3_host|" $ag_src_file 

# File containing the proper upload event format
upload_template="upload_H3_API.json"

# Key and new value
new_value=$H3_UUID
echo $new_value
# Update the value using sed
# note: the following updates all UUID-formated values, had better be only one!
sed  "s/........-....-....-....-............/$new_value/" $upload_template > temp.json
cat temp.json
# temp.json file now contains the correct UUID to use in the 'resource created' event.
echo "trigger upload of H3 inventory via an event from sideloader Agent "
curl -X POST -H "Content-Type: application/json" -d@temp.json localhost:5000/EventListener
# just a final read of the Sunfish Fabrics collection to validate there is now a CXL Fabric 
echo 'curl -X GET -H "Content-Type: application/json"  localhost:5001/redfish/v1/Fabrics | jq '
curl -X GET -H "Content-Type: application/json"  localhost:5000/redfish/v1/Fabrics | jq 
