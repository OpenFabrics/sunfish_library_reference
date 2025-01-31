# Copyright Notice:
# License: BSD 3-Clause License. For full text see link: https://github.com/DMTF/Redfish-Interface-Emulator/blob/master/LICENSE.md

import json
import copy
import requests

def get_memDomains(service_URI,memInventory):
    listFabrics = ""
    listEndpts = ""
    listMemDomains = ""
    listMemChunks = ""
    listChassis = ""
    tmpDomain = {}
    tmpChunk = {}
    tmpFabric=""
    tmpStart=0
    rb="/redfish/v1"
    headers = {"Content-type":"application/json" }

    print("get all memory domains")
    postID=rb + "/Fabrics"
    print(service_URI+postID)
    print("----")
    r = requests.get(service_URI+postID, headers=headers)
    print(r)
    data = json.loads(r.text)
    #print(json.dumps(data, indent =4 ))
    listFabrics = copy.deepcopy(data["Members"])
    #print(listFabrics)                   # grab list of fabrics
    for k,v in enumerate(listFabrics):   # for each fabric in list
        tmpFabric=v["@odata.id"].split("/")[-1]
        print("searching fabric ",tmpFabric)
        memInventory[tmpFabric]={}      #make a dict with fabric ID
        # grab list of MemoryDomains
        postID=rb + "/Chassis" +"/" + tmpFabric +"/MemoryDomains"
        print(postID)
        r = requests.get(service_URI+postID, headers=headers)
        print(r)
        data = json.loads(r.text)
        #print(json.dumps(data, indent =4 ))
        listMemDomains = copy.deepcopy(data["Members"])
        #print(listMemDomains)                   
        for k,v in enumerate(listMemDomains):   # for each memDomain in list
            tmpDomain={}
            tmpDomNum = v["@odata.id"].split("/")[-1]
            tmpMaxChunkID=0
            # grab memory domain details
            postID=rb + "/Chassis" +"/" + tmpFabric +"/MemoryDomains" + "/" +tmpDomNum
            print("searching ",postID)
            r = requests.get(service_URI+postID, headers=headers)
            print(r)
            data = json.loads(r.text)
            #print(json.dumps(data, indent =4 )) 

            # extract important details of each domain
            tmpDomain["fabricID"]=tmpFabric
            tmpDomain["memDomain"]=tmpDomNum
            tmpDomain["maxChunkID"]=tmpMaxChunkID
            tmpDomain["memDomURI"]=data["@odata.id"]
            tmpDomain["size"]=data["GenZ"]["max_data"]
            tmpDomain["maxChunks"]=data["GenZ"]["maxChunks"]
            tmpDomain["minChunkSize"]=data["GenZ"]["minChunkSize"]
            tmpDomain["block_enabled"]=data["AllowsBlockProvisioning"]
            tmpDomain["chunk_enabled"]=data["AllowsMemoryChunkCreation"]
            tmpDomain["memSource"]=data["Links"]["MediaControllers"]["@odata.id"]
            # trace the memory source to its endpoint
            postID=tmpDomain["memSource"]
            print("searching ",postID)
            r = requests.get(service_URI + postID, headers=headers)
            print(r)
            sourceData = json.loads(r.text)
            print(json.dumps(sourceData, indent=4))
            tmpDomain["EndptURI"]=sourceData["Links"]["Endpoints"][0]["@odata.id"] 
            tmpDomain["MemoryChunks"] = {}
            memInventory[tmpFabric][tmpDomNum] = {}
            memInventory[tmpFabric][tmpDomNum]= copy.deepcopy(tmpDomain)

            #  now extract the chunks assigned to this domain
            postID=data["MemoryChunks"]["@odata.id"]
            print("searching ", postID)
            r = requests.get(service_URI+postID, headers=headers)
            print(r)
            if "200" in str(r):                 #found memory chunks collection
                data = json.loads(r.text)
                #print(data)
                print(json.dumps(data, indent =4 ))
                listMemChunks = copy.deepcopy(data["Members"])
                #print(listMemChunks)                   
                for k,v in enumerate(listMemChunks):   # for each memory chunk in list
                    tmpChunk={}
                    tmpStart=0
                    tmpChunkNum = v["@odata.id"].split("/")[-1]
                    print("tmpChunkNum =",tmpChunkNum)
                    print("tmpDom_chunknum =",tmpDomain["maxChunkID"])
                    # track highest chunkID number found
                    if int(tmpChunkNum) > tmpMaxChunkID:
                        tmpMaxChunkID = int(tmpChunkNum)
                    # grab memory chunk details
                    postID="/" + v["@odata.id"]
                    print("searching ",postID)
                    r = requests.get(service_URI+postID, headers=headers)
                    print(r)
                    data = json.loads(r.text)
                    #print(json.dumps(data, indent =4 )) 
                    # extract important details of each chunk
                    tmpStart = data["AddressRangeOffsetMiB"]*(2**20)
                    tmpChunk["fabricID"]=tmpFabric
                    tmpChunk["memDomain"]=tmpDomNum
                    tmpChunk["chunkID"]=data["Id"]
                    # following endpoint extraction is PoC specific!!
                    tmpChunk["EndptURI"]=data["Links"]["Endpoints"][0]["@odata.id"] 
                    tmpChunk["size_in_bytes"]=data["MemoryChunkSizeMiB"]*(2**20)
                    tmpChunk["start_in_bytes"]=data["AddressRangeOffsetMiB"]*(2**20)
                    tmpChunk["mediaType"]=data["AddressRangeType"]
                    tmpChunk["use_status"]="busy"   # ["free","busy"] bookkeeping status
                    #print(tmpChunk)
                    # update the max ChunkID found for the memory domain
                    memInventory[tmpFabric][tmpDomNum]["maxChunkID"] = tmpMaxChunkID
                    # put the chunks found into the DB for the memory domain
                    memInventory[tmpFabric][tmpDomNum]["MemoryChunks"][tmpStart] = \
                            copy.deepcopy(tmpChunk)
    return

#  basic utilities
def get_fabrics(service_URI):
    listFabrics = []
    rb="/redfish/v1"
    headers = {"Content-type":"application/json" }

    print(f"get all Fabrics")
    postID=rb + "/Fabrics"
    print(f"{service_URI+postID}\n----")
    r = requests.get(service_URI+postID, headers=headers)
    if r.status_code != 200:
        return listFabrics
    data = json.loads(r.text)
    #print(f"{json.dumps(data, indent =4 )}")
    listFabrics = copy.deepcopy(data["Members"])
    return listFabrics

def get_endPts(service_URI,fabric_uri):
    listEndpts = []
    headers = {"Content-type":"application/json" }
    endPoints_uri=fabric_uri+"/Endpoints"

    print(f"searching fabric {endPoints_uri}")
    # grab list of Endpoints
    #print(f"--- GET {endPoints_uri}")
    r = requests.get(service_URI+endPoints_uri, headers=headers)
    if r.status_code != 200:
        return listEndpts
    data = json.loads(r.text)
    #print(f"{json.dumps(data, indent =4 )}")
    listEndpts = copy.deepcopy(data["Members"])
    return listEndpts

def get_fabricAdapters(service_URI,endPt_uri):
    listFabricAdapters = []
    headers = {"Content-type":"application/json" }
    #print(f"--- GET {endPt_uri}")
    r = requests.get(service_URI+endPt_uri, headers=headers)
    if r.status_code != 200:
        return listFabricAdapters
    data = json.loads(r.text)
    #print(f"{json.dumps(data, indent =4 )}")
    try:
        if "ConnectedEntities" in data:
            for entity in data["ConnectedEntities"]:
                if entity["EntityType"] == "FabricBridge":
                    FA_uri = entity["EntityLink"]["@odata.id"]
                    print(f"FabricAdapter found at {FA_uri}")
                    listFabricAdapters.append(entity["EntityLink"])
        else:
            print(f"couldn't find a ConnectedEntities in this Endpoint")
            return listFabricAdapters

    except:
        print(f"something went wrong with extracting ConnectedEntity in this Endpoint")
        return listFabricAdapters

    return listFabricAdapters

def get_MDs(service_URI,FA_uri):
    listMDs = []
    headers = {"Content-type":"application/json" }
    print(f"--- GET {FA_uri}")
    r = requests.get(service_URI+FA_uri, headers=headers)
    if r.status_code != 200:
        print(f"Can't GET {FA_uri}, code is {r.status_code}")
        return listMDs
    data = json.loads(r.text)
    #print(f"{json.dumps(data, indent =4 )}")
    try:
        if "Links" in data:
            for entity in data["Links"]:
                if entity == "MemoryDomains":
                    for MD_link in data["Links"]["MemoryDomains"]:
                        #print(f"MD_link found is {MD_link}")
                        listMDs.append(MD_link)
            return listMDs

    except:
        print(f"something went wrong with extracting MemoryDomains in this Endpoint")
        return listMDs

    return listMDs


def get_Memories(service_URI,MD_uri):

    listMemories = []
    headers = {"Content-type":"application/json" }
    #print(f"--- GET {MD_uri}")
    r = requests.get(service_URI+MD_uri, headers=headers)
    if r.status_code != 200:
        print(f"Can't GET {MD_uri}, code is {r.status_code}")
        return listMemories
    data = json.loads(r.text)
    #print(f"{json.dumps(data, indent =4 )}")
    try:
        if "InterleavableMemorySets" in data:
            for entity in data["InterleavableMemorySets"]:
                if "MemorySet" in entity:
                    for memSetLink in entity["MemorySet"]: # walk the LIST of memory links
                        listMemories.append(memSetLink)
            return listMemories

    except:
        print(f"something went wrong with extracting Memory in this MemoryDomain")
        return listMemories

    return listMemories

def sum_Memory(service_URI,Memory_uri):
    # this routine sums memory capacity of a 'memory' object
    # It categorizes the capacity into byte-addressable, volatile, and non-volatile buckets
    # It ignores 'Block' mode storage
    # It assumes that if MemoryType or MemoryMedia properties are set, they establish
    #   the homogeneous nature of the memory device
    # If the device has Regions defined, their description may over-rule MemoryType or MemoryMedia
    #
    tmpMemCap = {}
    mem_type = ""
    mem_classification = ""
    mem_capacity = 0
    volatile_capacity = 0
    nonVolatile_capacity = 0
    other_capacity = 0
    headers = {"Content-type":"application/json" }
    print(f"--- SUM {Memory_uri}")
    r = requests.get(service_URI+Memory_uri, headers=headers)
    if r.status_code != 200:
        print(f"Can't GET {Memory_uri}, code is {r.status_code}")
        return tmpMemCap
    data = json.loads(r.text)
    #print(f"{json.dumps(data, indent =4 )}")
    try:
        # MemoryType takes precedence, if defined
        if "MemoryType" in data:
            mem_type = data["MemoryType"]
        # else MemoryMedia sets mem_type, if defined and homogeneous
        elif "MemoryMedia" in data:
            if len(data["MemoryMedia"]) > 1: 
                for mediaType in data["MemoryMedia"]:
                    if mem_type == "":
                        mem_type = mediaType
                    elif mem_type != mediaType:
                        mem_type = "heterogeneous"
            else:
                mem_type = data["MemoryMedia"][0]
        else:
            mem_type = "Undefined"

        if "CapacityMiB" in data:
            mem_capacity = data["CapacityMiB"]
            
        if "Regions" in data:
            # save all Regions for client side analysis
            tmpMemCap["Regions"] = data["Regions"]
            for entity in data["Regions"]:
                # categorize and summarize capacity across all Regions
                if "MemoryClassification" in entity:
                    # verify all Regions are homogeneous
                    if mem_classification =="":
                        mem_classification = entity["MemoryClassification"] 
                    elif mem_classification != entity["MemoryClassification"]:
                        mem_classification = "heterogeneous"
                    # check capacity of this Region
                    if "SizeMiB" in entity:
                        # if no size in Region, no capacity assumed
                        if entity["MemoryClassification"] == "Volatile":
                            volatile_capacity=volatile_capacity + entity["SizeMiB"]
                        elif entity["MemoryClassification"] == "ByteAccessiblePersistent":
                            nonVolatile_capacity=nonVolatile_capacity + entity["SizeMiB"]
                        else:
                            other_capacity=other_capacity + entity["SizeMiB"]
                    else:  # no size in Region is an error, no Region capacity counted
                        pass 

                else:  # no MemoryClassification in Region is an error, no mem_classification possible
                    pass
                
            if  mem_type == "NVDIMM_N"or mem_type == "DRAM":
                mem_type = "Volatile"
            elif  mem_type == "NAND"or mem_type == "NVDIMM_F":
                mem_type = "nonVolatile"
            elif  mem_type == "NVDIMM_P" or mem_type == "IntelOptane":
                mem_type = "heterogeneous"
            elif mem_type == "undefined" or mem_type == "heterogeneous" :
                if mem_classification == "Volatile":
                    mem_type = "Volatile"
                elif mem_classification == "ByteAccessiblePersistent":
                    mem_type = "nonVolatile"
                elif mem_classification == "heterogeneous":
                    mem_type = "heterogeneous"

            # reconcile mem_type with capacity
            tmpMemCap["MemoryType"] = mem_type
            capacity_sum = volatile_capacity + nonVolatile_capacity + other_capacity
            if capacity_sum > 0:
                # there were Regions with capacity given, use only those capacities
                # log the capacities found by type
                if volatile_capacity >0 :
                    tmpMemCap["volatile_capacity"] = volatile_capacity
                if nonVolatile_capacity >0 :
                    tmpMemCap["nonVolatile_capacity"] = nonVolatile_capacity
                if other_capacity >0 :
                    tmpMemCap["other_capacity"] = other_capacity

                if mem_type == "Volatile":
                    tmpMemCap["CapacityMiB"] = volatile_capacity
                elif mem_type == "nonVolatile":
                    tmpMemCap["CapacityMiB"] = nonVolatile_capacity

            else:    # no option but to use CapacityMiB of Memory object
                tmpMemCap["CapacityMiB"] = mem_capacity # could be 0

            print(f"Memory found:\n {json.dumps(tmpMemCap,indent = 4)}")
            return tmpMemCap

    except:
        print(f"something went wrong with extracting Memory capacity from this Memory")
        return tmpMemCap

    return tmpMemCap

def create_MD_pools(service_URI,memoryDomainsList):

    headers = {"Content-type":"application/json" }
    MD_memCap = {}
    try:
        if True:
            MD_counter = 0
            for memDomainMember in memoryDomainsList:
                MD_key="MD_pool"+str(MD_counter)
                MD_memCap[MD_key]={}
                MD_uri = memDomainMember["@odata.id"]
                MD_memCap[MD_key]["MD_memType"]=""
                MD_memCap[MD_key]["MD_memCapacity"]=0
                MD_memCap[MD_key]["MD_uri"] = MD_uri

                #MD_memCap[MD_key]["block_enabled"]=data["AllowsBlockProvisioning"]
                #MD_memCap[MD_key]["chunk_enabled"]=data["AllowsMemoryChunkCreation"]
                # 
                MD_memories=[]
                tmp_MD_capacity = 0
                mCount=0
                print(f"find and sum memory in memDomain {MD_uri}")
                # get the Memories feeding the MemoryDomain
                MD_memories.extend(get_Memories(service_URI,MD_uri))
                tmpMemoryCap = {}
                for MemoryMember in MD_memories:
                    mem_key = "memDev" + str(mCount)
                    Memory_uri = MemoryMember["@odata.id"]
                    print(f"mem device {Memory_uri}")
                    tmpMemoryCap = sum_Memory(service_URI,Memory_uri)
                    MD_memCap[MD_key][mem_key] = tmpMemoryCap
                    MD_memCap[MD_key][mem_key]["Mem_uri"]=Memory_uri
                    mCount = mCount+1
                    if MD_memCap[MD_key]["MD_memType"] == "":
                        MD_memCap[MD_key]["MD_memType"] = tmpMemoryCap["MemoryType"]
                    elif MD_memCap[MD_key]["MD_memType"] != tmpMemoryCap["MemoryType"]:
                        MD_memCap[MD_key]["MD_memType"] = "heterogeneous"
                    if MD_memCap[MD_key]["MD_memType"] != "heterogeneous":
                        tmp_MD_capacity = tmp_MD_capacity + tmpMemoryCap["CapacityMiB"]

                MD_memCap[MD_key]["MD_memCapacity"] = tmp_MD_capacity
                MD_counter = MD_counter+1
                # now aggregate capacity 
            return MD_memCap
        else:
            print ("unrecognized cmd")


    except:
        print(f"something went wrong with collecting Memory pools for each MemoryDomain ")
        return MD_memCap

    return MD_memCap

def sort_chunks(memInventory):
    tmpFabricID=""

    for k,v in memInventory.items():  #for every fabric found
        tmpFabricID=k               # grab the fabric name
        for memDomNum, memDomain in v.items():  # for every MD found
            unsorted_chunks={}          # sort the memory chunks in each MD
            sorted_chunks={}
            unsorted_chunks=copy.deepcopy(memInventory[tmpFabricID][memDomNum]["MemoryChunks"])
            sorted_chunks=dict(sorted(unsorted_chunks.items(), key=lambda item: item[0]))
            memInventory[tmpFabricID][memDomNum]["MemoryChunks"] = copy.deepcopy(sorted_chunks)
    return

def make_free_list(memInventory,freeList,busyList):
    tmpFabricID=""
    freeList=[]
    busyList=[]
    tmpChunk={}

    for k,v in memInventory.items():  #for every fabric found
        tmpFabricID=k               # grab the fabric name
        for memDomNum, memDomain in v.items():  # for every MD found
            sorted_chunks={}
            sorted_chunks=copy.deepcopy(memInventory[tmpFabricID][memDomNum]["MemoryChunks"])
            for chunk_start, chunk_body in sorted_chunks.items():  # for every block found
                if chunk_body["use_status"] == 'free':
                    freeList.append(chunk_body)
                if chunk_body["use_status"] == 'busy':
                    busyList.append(chunk_body)
            
        print("busyList ---", json.dumps(busyList,indent=4))
        print("freeList ---", json.dumps(freeList,indent=4))
        print_free_list(freeList)
        print_free_list(busyList)
    return

def print_free_list(freeList):
    f_id="GenZxxx"
    md_id="0"
    stat="none"
    ch_id="0"
    size=0
    start=0
    ep_id="0"
    wildcards={}

    hdr="\nStatus\tMemoryDomain\tChunk\tSize\t\tStart\t\tEndpt\tFabric"
    print("\n-------------------------------------------------------------\n",hdr)
    for index,block in enumerate(freeList):
        stat=block["use_status"]
        md_id=block["memDomain"]
        ch_id=block["chunkID"]
        size=block["size_in_bytes"]
        start=block["start_in_bytes"]
        ep_id=block["EndptURI"].split("/")[-1]
        f_id=block["fabricID"]
        print(stat,"\t",md_id,"/t",ch_id,"/t",size,"/t",start,"/t",ep_id,"/t",f_id)


    return
def create_chunk(service_URI,headers,memInventory,fabricID,domainNum,size_in_MiB):
    print("creating chunk of ",size_in_MiB," MBytes")
    reqSize=size_in_MiB * (2**20)
    found=False
    newChunkID=""
    wildcards={}
    ofmf_body={}
    tmpList=[]

    for chunk_start, chunk_body in memInventory[fabricID][domainNum]["MemoryChunks"].items():
        if chunk_body["size_in_bytes"] >= reqSize:
            if chunk_body["use_status"] == 'free':
                found=True
                newChunkID=str(memInventory[fabricID][domainNum]["maxChunkID"] + 1)
                tmpList=memInventory[fabricID][domainNum]["memDomURI"].split("/")
                print(tmpList)
                rb="/" + tmpList[1]+"/"+tmpList[2] +"/"
                c_id=tmpList[4]
                md_id=tmpList[6]
                mc_id=newChunkID
                # build the new chunk here
                # call the template
                # transfer necessary details to template
                wildcards = {"rb":rb, "c_id":c_id,"md_id":md_id, "mc_id":mc_id }
                ofmf_body = copy.deepcopy(get_MDChunks_instance(wildcards)) 
                #tmpStr = md_path + "/" + md_index + "/MemoryChunks/" + mch_index
                #tmpMemChunk["@odata.id"]=tmpStr
                #  update the associated Endpoint URI 
                #ep_id = allAgentNodes["nodes"][nodeID]["redfishIDs"]["ep_id"]
                #tmpStr = rb+"Fabrics/"+f_id+"/Endpoints/"+ep_id
                tmpStr = memInventory[fabricID][domainNum]["EndptURI"]
                ofmf_body["Links"]["Endpoints"].append({"@odata.id":tmpStr})
                ofmf_body["AddressRangeOffsetMiB"] = int(chunk_start/(2**20))
                ofmf_body["MemoryChunkSizeMiB"] = int(reqSize/(2**20))
                #  add the necessary Oem details from (or for?) zephyr
                #  verify these are defaults that agent overwrites?
                ofmf_body["Oem"]["class"] = 2
                ofmf_body["Oem"]["type"] = 1
                ofmf_body["Oem"]["flags"] = 0
                print("new chunk --")
                print(json.dumps(ofmf_body, indent=4))
                #  just write the new memory chunk POST file for later use
                json_file=""
                json_file=("./iPOSTmemChunk_"+md_id+"_"+mc_id+".json")
                print()
                print("posting file ", json_file)
                # hack for testing
                with open(json_file,"w") as jdata:
                    json.dump(ofmf_body,jdata, indent=4)
                    jdata.close()
                break       # no need to search other free space options

    # post the new chunk, if found
    if found:
        print("found space for new chunk ",newChunkID)
        # 
        postID=ofmf_body["@odata.id"]
        print ("POST")
        print(service_URI+postID)
        r = requests.post(service_URI+postID, data=json.dumps(ofmf_body),\
                    headers=headers)
        print(r)
        data = json.loads(r.text)
        print(json.dumps(data, indent =4 ))

        
    else:
        print("no free space chunk large enough in that memory domain")

    return

def find_free_mem(memInventory):
    # routine finds free memory ranges in a domain, fills them with
    # 'free' chunks, and consolidates all free chunks into as few contiguous
    # free chunks as possible

    tmpFabricID=""
    print("find and consolidate free space")


    for fabricID,fabric_inventory in memInventory.items():  #for every fabric found
        for memDomNum, memDomain in fabric_inventory.items():  # for every MD found
            print("collecting mem domain ",memDomNum)
            sorted_chunks={}
            tmp_chunks={}
            new_chunk={}
            domSize=memInventory[fabricID][memDomNum]["size"]
            sorted_chunks=copy.deepcopy(memInventory[fabricID][memDomNum]["MemoryChunks"])
            print("sorted_chunks = ")
            print(sorted_chunks)

            if not bool(sorted_chunks):
                print("domain ",memDomNum," is empty")
                # simply create a free chunk the size of the domain
                new_start=0
                new_chunk["fabricID"]=memDomain["fabricID"]
                new_chunk["chunkID"]="none"
                new_chunk["memDomain"]=memDomNum
                new_chunk["EndptURI"]=memDomain["EndptURI"]
                new_chunk["size_in_bytes"]=memDomain["size"]
                new_chunk["start_in_bytes"]=0
                new_chunk["mediaType"]="Volatile"
                new_chunk["use_status"]="free"
                print("domain ", memDomNum, "has free space of",\
                        new_chunk["size_in_bytes"], " Bytes")
                # add this free chunk to the memory domain DB
                tmp_chunks[new_start]=copy.deepcopy(new_chunk)
                print(json.dumps(tmp_chunks, indent = 4))
                # done with this memory domain, so update its chunk list
                memInventory[fabricID][memDomNum]["MemoryChunks"]=copy.deepcopy(tmp_chunks)


            else:
                print("domain ",memDomNum," chunks")
                last_start=0
                last_end= (-1)
                last_status="none"
                last_chunkID=0
                for chunkID, chunkBody in sorted_chunks.items(): # for every chunk found
                    print(json.dumps(chunkBody, indent = 4))
                    current_status=chunkBody["use_status"]
                    current_start=chunkBody["start_in_bytes"]
                    current_size=chunkBody["size_in_bytes"]
                    current_end=current_start + current_size -1
                    if current_start > (last_end+1): # there's a gap
                        print("found a gap")
                        memGap = current_start - (last_end +1)
                        if last_status =="free":
                            print("expand previous free block")
                            last_size = tmp_chunks[last_chunkID]["size_in_bytes"]
                            tmp_chunks[last_chunkID]["size_in_bytes"] = \
                                    last_size + memGap
                        else:
                            print("add new free block")
                            new_start=(last_end+1)
                            new_chunk={}
                            new_chunk["fabricID"]=memDomain["fabricID"]
                            new_chunk["chunkID"]="none"
                            new_chunk["memDomain"]=memDomNum
                            new_chunk["EndptURI"]=memDomain["EndptURI"]
                            new_chunk["size_in_bytes"]=memGap
                            new_chunk["start_in_bytes"]=last_end+1
                            new_chunk["mediaType"]="Volatile"
                            new_chunk["use_status"]="free"
                            # add this free chunk to the memory domain DB
                            tmp_chunks[new_start]=copy.deepcopy(new_chunk)
                            # copy the current chunk to the memory domain DB
                            tmp_chunks[current_start]=copy.deepcopy(chunkBody)

                    else:
                        print("no gap")
                        # copy this chunk over to the tmp_chunks
                        tmp_chunks[chunkID]=copy.deepcopy(chunkBody)

                    # save this chunk's details for next chunk iteration
                    last_end=current_end 
                    last_start=current_start
                    last_status=chunkBody["use_status"]
                    last_chunkID=chunkID

                # check if there is free space after the last used or free chunk
                if last_end < (domSize-1):  # need to pad to end of domain
                    print("need end free block")
                    print("add new free block")
                    memGap = domSize-(last_end+1)
                    new_start=(last_end+1)
                    new_chunk={}
                    new_chunk["fabricID"]=memDomain["fabricID"]
                    new_chunk["chunkID"]="none"
                    new_chunk["memDomain"]=memDomNum
                    new_chunk["EndptURI"]=memDomain["EndptURI"]
                    new_chunk["size_in_bytes"]=memGap
                    new_chunk["start_in_bytes"]=last_end+1
                    new_chunk["mediaType"]="Volatile"
                    new_chunk["use_status"]="free"
                    # add this free chunk to the memory domain DB
                    tmp_chunks[new_start]=copy.deepcopy(new_chunk)

                print("done with memdomain ",memDomNum)

            memInventory[fabricID][memDomNum]["MemoryChunks"] = copy.deepcopy(tmp_chunks)
    return

def myCLI(service_URI):
    postFile=""
    myCMD=""
    memInventory={}
    tmpMemInventory={}
    fabricsList=[]
    endPtsList=[]
    fabricAdaptersList=[]
    memoryDomainsList=[]
    memoriesList=[]
    memoryCap={}
    memoryPool={}
    tmpMemoryPool={}
    tmpMemoryCap={}
    MD_memories=[]
    MD_memCap={}
    mCount=0
    
    print(service_URI)

    headers = {"Content-type":"application/json" }

    while myCMD != "q":
        myCMD = input("Sun_utils> ")
        print()
        print()
        print()
        print(f"-----------------------------------------")
        print(myCMD)
        if myCMD == "q":
            print ("quit")
        elif myCMD == "get_mem":
            tmpMemInventory={}
            fabricsList = get_fabrics(service_URI)
            #print(f"fabrics found: \n{json.dumps(fabricsList, indent = 4)}")
            # find all the fabric adapter endpoints on all the fabrics
            for fabricMember in fabricsList:
                fabric_uri = fabricMember["@odata.id"]
                fabric_name = fabric_uri.split("/")[-1]
                tmpMemInventory[fabric_name]={}
                endPtsList = get_endPts(service_URI, fabric_uri)
                tmpMemInventory[fabric_name]["endPts"]=endPtsList
                print(f"endpoints found: \n{json.dumps(endPtsList, indent = 4)}")
                for endPtMember in endPtsList:
                    endPt_uri = endPtMember["@odata.id"]
                    fabricAdaptersList.extend(get_fabricAdapters(service_URI,endPt_uri))
                tmpMemInventory[fabric_name]["fabricAdapters"]=fabricAdaptersList
            #print(f"fabric adapters found: \n{json.dumps(fabricAdaptersList, indent = 4)}")
            # find all the MemoryDomains associated with all the Fabric Adapters
            for fabricAdapterMember in fabricAdaptersList:
                FA_uri = fabricAdapterMember["@odata.id"]
                memoryDomainsList.extend(get_MDs(service_URI,FA_uri))
            #print(f"memory domains found: \n{json.dumps(memoryDomainsList, indent =4)}")
            for memDomainMember in memoryDomainsList:
                MD_uri = memDomainMember["@odata.id"]
                memoriesList.extend(get_Memories(service_URI,MD_uri))
            #print(f"memories found: \n{json.dumps(memoriesList, indent =4)}")
            for MemoryMember in memoriesList:
                Memory_uri = MemoryMember["@odata.id"]
                tmpMemoryCap = (sum_Memory(service_URI,Memory_uri))
                memoryCap[mCount]=tmpMemoryCap
                mCount = mCount+1
            #print(f"memory capacity found: \n{json.dumps(memoryCap, indent =4)}")

            print(f"\n\n-------------\nmemory per MemoryDomain")
            #  now re-run the memoryDomains and create memoryPool / memoryDomain
            MD_memCap = create_MD_pools(service_URI,memoryDomainsList)
            print(f"tmpMemInventory:\n{json.dumps(tmpMemInventory, indent=4)}")
            print(f"MD capacity:\n{json.dumps(MD_memCap, indent =4)}")
            print(f"done get_mem")
        else:
            print ("unrecognized cmd")

    return

