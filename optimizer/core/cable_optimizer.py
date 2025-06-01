from django.http import request
from datetime import datetime
from datetime import datetime
import time, os
import pandas as pd
import numpy as np
from numpy import array, dtype
import json 

# import concurrent.futures # this is for multi processing

global cabledata, drumdata
# global free_Wbs, isReqfromApp         
rev_no = 10

free_Wbs = True
isReqfromApp = False

dataSource = 'xlfile' # later: or MobileApp (****)!option for direct onscreen-edit will be explored later
cableType ='*'        # later: Provision to run selectively by user to be built !
    

# Placeholder until full refactor; this will be replaced by a proper "pure function" version

# def run_optimizer_main(settings: dict, cable_data: list[dict], drum_data: list[dict]) -> dict:
#     """
#     Accepts structured input from the API:
#     - settings: dictionary of config options
#     - cable_data: list of cable rows (each as dict)
#     - drum_data: list of drum rows (each as dict)

#     Returns:
#     - Dictionary containing ds_report (summary + report tables)
#     """


#     # Convert list-of-dict to DataFrame
#     cable_df = pd.DataFrame(cable_data)
#     drum_df = pd.DataFrame(drum_data)
#     result = control_panel(cable_df, drum_df)
#     return result




def control_panel(users_cable_data, users_drum_data, ds_settings):
    
    startTimer = time.time()
    
    drum_Schedule = []
    startTimer = time.time()     
    try:
        cabledata, drumdata = users_cable_data, users_drum_data
        
        getindex = np.arange(cabledata.shape[0])                    # arr.shape[0] => no. of rows in arr; np.arange(n) => create array of n integer from 0 to n-1
        cable_data =  array(cabledata.to_numpy())[:, 1:4]           # get a slice from cloumn 1 to 3 (note for 3 need to set 4)
        cable_data = np.insert(cable_data, 0, getindex, axis=1)     # insert a new column as its index           
        
        getindex = np.arange(drumdata.shape[0])                     # arr.shape[0] => no. of rows in arr; np.arange(n) => create array of n integer from 0 to n-1
        drum_data =  array(drumdata.to_numpy())[:, 1:3]             # get a slice from cloumn 1 to 2 (note for 2 need to set 3)
        drum_data = np.insert(drum_data, 0, getindex, axis=1)       # insert a new column as its index                  
        
        cab_cat = cable_data[:, 2]
        drum_cat = drum_data[:, 1]
        wbs_arr = cable_data[:, 3]     # get slices       
        
        uniqCab_cat = list(dict.fromkeys(list(cab_cat)))            # unique cable Types
        uniqDrum_cat = list(dict.fromkeys(drum_cat))                # unique drum Types
        uniq_Wbs = list(dict.fromkeys(wbs_arr))                      # unique wbs
        
        ds.drumAllocator('', dataSource, cableType, isReqfromApp, cable_data, drum_data, uniqCab_cat, uniqDrum_cat, uniq_Wbs, drum_Schedule)
      
    except:       
        return {'error':'Failed to read from the file, check if the input file format is correct.'}          
 
    # Generation of Output -------------------
    #      Data format
            # 0.  [  [Cable Spec, Drum Input Seq No, Drum Tag, Drum Length, Left over],
            # 1.    [Cable Input Seq. No1,Seq. No2 ..]
            # 2.    [Cable Tag1,tag2 …],
            # 3.    [Cable length1, length2, ….],
            # 4.    [WBS1,wbs2,….],
            # 5.    [Pull Card No1, pc no2, …],
            # 6.    Rev]   ]
    
    jsonOutput =[] 
    dr_array = array(drumdata.to_numpy())
    cable_array = array(cabledata.to_numpy())
            
    for i_type in range(len(drum_Schedule)):
        for i_dr in range(len(drum_Schedule[i_type])):            
            dr_index = drum_Schedule[i_type][i_dr][0]   # Note: drum input sequence = dr_index + 1              
            dr_tag = dr_array[dr_index, 0]
            cable_spec = dr_array[dr_index, 1]
            dr_length = drum_data[dr_index, 2]                                             
            dr_lo = drum_Schedule[i_type][i_dr][1][0]
            
            allotted_cab= drum_Schedule[i_type][i_dr][1][1] # Note: cable input sequence = each of the element no + 1 
            cableTag = []
            cabInputSeq = []
            cableLength = []
            wbsNo =[]
            pullCardNo =[]     
            
            for i in range(len(allotted_cab)):
                cabInputSeq.append(allotted_cab[i])
                cableTag.append(cable_array[allotted_cab[i], 0])
                cableLength.append(cable_array[allotted_cab[i], 1])
                wbsNo.append(cable_array[allotted_cab[i], 3])
                pullCardNo.append("PC_" + cable_array[allotted_cab[i], 0])
            
            jsonOutput.append([[cable_spec, dr_index, dr_tag, dr_length, dr_lo], cabInputSeq, cableTag, cableLength, wbsNo, pullCardNo, rev_no]) 
            
 
    ds_report =  generateReport(cable_array, dr_array, jsonOutput)      
    # writetoExcel(ds_report, jsonOutput)    
    
    ds_report["ds"] = jsonOutput
    ds_report["computeTime"] = str(round((time.time()-startTimer),3))+'s'    
    return ds_report        
   

class ds():
    
    def drumAllocator(appDataFromSite, dataSource, cableType, isReqfromApp, cable_data, drum_data, uniqCab_cat, uniqDrum_cat, uniq_Wbs, drum_Schedule): # **appDataFromSite = [cabTagfromAPP, cutLengthfromAPP, drumTagfromAPP]
         
        if isReqfromApp :# when a specific cable type is to be worked out 

            sqlStr = "SELECT cabSeqIndex, cabSegNo, cabDesignLen, cabsegLen, cabCutLength, wBS, drumTag \
                    FROM cableTable WHERE cabSpec= '" + cableType + "' AND cabCutLength = 0 "

            getCabDatafromSQL = rwModule.getTablefromSQL('','cableTable', sqlStr); getCabDatafromSQL.pop(0)

            cabSliceIndex = list(list(zip(*getCabDatafromSQL))[0])
            cabSliceLength = list(list(zip(*getCabDatafromSQL))[2])
            cabSliceLength =  list(map(int, cabSliceLength)) # converting a float list to an integer list in pythonic way

            # for later: (1) Make sure drumTags are unique (data Validation) 
            # (2) check if the current cable received from siteApp is updated in database, if not update

            # get details of drums where some cables are already cut earlier
            sqlStr = "SELECT drumTag, cabCutLength, cabTag FROM cableTable WHERE cabCutLength > 0"
            drumCutDetails = rwModule.getTablefromSQL('','cableTable', sqlStr)
            drumCutDetails.pop(0)

            # get details of all drums for this cableType
            sqlStr = "SELECT drumTag, drumSeqIndex, manufLength FROM drumTable WHERE cabSpec = '" + cableType + "'"
            getdrumDatafromSQL =rwModule.getTablefromSQL('','drumTable', sqlStr) 

            drumsliceTAG =  list(list(zip(*getdrumDatafromSQL))[0]);   drumsliceTAG.pop(0)
            drumsliceIndex = list(list(zip(*getdrumDatafromSQL))[1]);  drumsliceIndex.pop(0)
            drumsliceLength = list(list(zip(*getdrumDatafromSQL))[2]); drumsliceLength.pop(0)

            drumsliceLength =  list(map(int, drumsliceLength))
            
            # deduct all previously cut lengths from the drums 
            for i in range(len(drumCutDetails)):
                i_index = drumsliceTAG.index(drumCutDetails[i][0])
                drumsliceLength[i_index] = drumsliceLength[i_index] - int(drumCutDetails[i][1])      

                
            drumFiller(drumsliceIndex, drumsliceLength, cabSliceIndex, cabSliceLength, cableType)     



            # filtDrumIndex, filtDrumLen = getReqDrum(appDataFromSite[3])               # get drums 
            # filtCabIndex,filtCabLen = getReqCable(appDataFromSite[3], uniqWbs[0])     # get cables [send just a default wbs (but it doesn't matter)]            


            # ------------------Manage Cut Lengths here----------------------------------------------------------------------------------
            # delete cables those are cut and re adjust the drum substructing the cut lengths
            # check if the requested cut length is already updated in data base, if not update database with current required Cut length!
            #-----------------------------------------------------------------------------------------------------------------------------        
            
            # drumFiller(filtDrumIndex, filtDrumLen, filtCabIndex, filtCabLen, reqCableType, dateTimeStamp)

            # for the first time when all cable-types needs to be computed, define cableType as * dringing call this function
        else: # if the request from engineering console with either cable type = '*' or a specific cableType
            if cableType == "*": # for later: add [rovision to run Pnp for a specific cableType from Engg. console
                
                # populateInput(dataSource) # This function is built with global list to avoid multiple SQL server call
                
           

                for cable_type in uniqCab_cat:                                              # get drum details for each cable
                    if cable_type in uniqDrum_cat:                                          # if the matching drum is available then do it, else take next cable type
                        filtDrumIndex, filtDrumLen = getReqDrum(cable_type, drum_data)
                    else: continue

                    if free_Wbs :                                                             # if free allocation accross all wbs
                        filtCabIndex,filtCabLen = getReqCable(cable_type, 'na', cable_data)  # send a 'na' as wbs
                        
                        
                        
                        dS_for_this_CableType = drumFiller(filtDrumIndex, filtDrumLen, filtCabIndex, filtCabLen, cable_type)
                        # later: create a new thread that will process this python array in JASON output to reduce overall processing time
                        # print (cable_type,"====>", dS_for_this_CableType)
                        drum_Schedule.append(dS_for_this_CableType)
                                            
                    else:                    # if WBS wise drum allocation is required
                        for wbs in uniq_Wbs:
                            filtCabIndex,filtCabLen=getReqCable(cableType, wbs)
                            dS_for_this_CableType = drumFiller(filtDrumIndex, filtDrumLen, filtCabIndex, filtCabLen, cable_type)
                            drum_Schedule.append(dS_for_this_CableType)
                                                        
        # print("Final DrumSchedule",drum_Schedule)

def getReqCable(cableType, wbs, cable_data):

    cabWbsArr = (cable_data[:, 3] == wbs)                      # make a boolean array that matches with required wbs type
    cabTypeArr = (np.array(cable_data[:, 2]) == cableType)     # make a boolean array that matches with required cable type
    
    if wbs=='na': filter_arr = np.array(cabTypeArr)                
    else        : filter_arr = np.array(cabWbsArr*cabTypeArr)
    
    filtCabIndex = np.array(cable_data[:, 0])[filter_arr]
    filtCabLen = np.array(cable_data[:, 1])[filter_arr]
 
    return(filtCabIndex, filtCabLen)


def getReqDrum(cable_type, drum_data):
    # drumIndex = np.where(np.array(drumLen)>0)            # 
    drumIndex = np.array(drum_data[:, 0])                  # Slice out drum index (as they appear in excel)
    drumType = (np.array(drum_data[:, 1]) == cable_type)   # make a boolean array that matches with required wbs type
    
    filtDrumIndex = np.array(drumIndex)[drumType]
    filtDrumLen = np.array(drum_data[:, 2])[drumType]
    return(filtDrumIndex,filtDrumLen)

#--------------------------------------------------------------------------------------------------
def createDPTable(target, cabIndex, cabLen, cabletype): # this is part of the modified memory optimised algo
    
    searchTable = [0 for x in range((target + 1))]

    auxTable =[]
    auxPoiter = 0
    searchTable[cabLen[0]] = 1
    auxTable.append(cabLen[0])

    for i in range(1, len(cabLen)):

        if searchTable[cabLen[i]] == 0: searchTable[cabLen[i]] = i + 1
    
        auxTable.sort()
        auxPoiter = len(auxTable)
        for j in range(0, auxPoiter):
            tmpLen = auxTable[j] + cabLen[i]
            if tmpLen < target :
                if searchTable[tmpLen] == 0:
                    searchTable[tmpLen] = i + 1
                    auxTable.append(tmpLen)
                
            elif tmpLen == target:
                searchTable[tmpLen] = i + 1
                return searchTable, auxTable   # when there is no wastage
            else : break
          
        auxTable.append(cabLen[i])
    
    return searchTable, auxTable # when there is a wastage


def modifiedSearchAlgo(target, cabIndex, cabLen, cabletype):# solve SSP with DP (as a seed to GA)

    searchTable, auxTable = createDPTable(target, cabIndex, cabLen, cabletype) # outsoure searchTable and auxTable

    wastage = 0
    result = [] 
    newTarget = target - wastage

    while searchTable[newTarget] == 0:
        wastage += 1
        newTarget = target - wastage
        

    while newTarget > 0:
        itraddr = searchTable[newTarget] - 1
        result.append(cabIndex[itraddr ])
        newTarget = newTarget - cabLen[itraddr]
        
    return [wastage, result]

#############################################################################################
def drumFiller(filtDrumIndex, filtDrumLen, cabIndex, cabLen, cable_type):
    
    dS_for_this_CableType = []
    
    for i in range(len(filtDrumLen)):
       
        dS_for_this_CableType.append([filtDrumIndex[i], modifiedSearchAlgo(filtDrumLen[i], cabIndex, cabLen, cable_type)])
        
        # print("New Algo: (Drum seq ",filtDrumIndex[i], ", CabType: ", cable_type,")", drum_Schedule[i][1])
        # print('{} : {}'.format("Overall_Time_New: ", (time.perf_counter() - startOverall)*1000),"ms") 
        # newtime = (time.perf_counter() - startOverall)
        # print("------------------------------------------------------------------------------------------")     
        # print(drumSchedule[i])

        # delete the allocated cables for the next round
        cabIndextoRemove = dS_for_this_CableType[i][1][1]
        tempcabInfo=[[],[]]

        for indx in range(len(cabIndex)):      # note : listA_minus_listB = [item for item in listA if item not in set(listB)]
           
            if cabIndex[indx] not in cabIndextoRemove:
                tempcabInfo[0].append(cabIndex[indx])
                tempcabInfo[1].append(cabLen[indx])

        cabIndex= tempcabInfo[0].copy()
        cabLen = tempcabInfo[1].copy()
        if len(cabLen) == 0: break

    # print ("---------printing COMPLETE drum schedule:----------------------------------------")
    # print (dS_for_this_CableType)
    
    return dS_for_this_CableType

    # rwModule.insertStoredDS(drumSchedule, cableType, dateTimeStamp)         
       

# call allocator according to 'cableType' and 'WBS'
def drumAllocator(appDataFromSite, dataSource, cableType, isReqfromApp): # **appDataFromSite = [cabTagfromAPP, cutLengthfromAPP, drumTagfromAPP]
    dateTimeStamp= datetime.now()
   
    if isReqfromApp :# when a specific cable type is to be worked out 

        sqlStr = "SELECT cabSeqIndex, cabSegNo, cabDesignLen, cabsegLen, cabCutLength, wBS, drumTag \
                FROM cableTable WHERE cabSpec= '" + cableType + "' AND cabCutLength = 0 "

        getCabDatafromSQL = rwModule.getTablefromSQL('','cableTable', sqlStr); getCabDatafromSQL.pop(0)

        cabSliceIndex = list(list(zip(*getCabDatafromSQL))[0])
        cabSliceLength = list(list(zip(*getCabDatafromSQL))[2])
        cabSliceLength =  list(map(int, cabSliceLength)) # converting a float list to an integer list in pythonic way

     # for later: (1) Make sure drumTags are unique (data Validation) 
     # (2) check if the current cable received from siteApp is updated in database, if not update

        # get details of drums where some cables are already cut earlier
        sqlStr = "SELECT drumTag, cabCutLength, cabTag FROM cableTable WHERE cabCutLength > 0"
        drumCutDetails = rwModule.getTablefromSQL('','cableTable', sqlStr)
        drumCutDetails.pop(0)

        # get details of all drums for this cableType
        sqlStr = "SELECT drumTag, drumSeqIndex, manufLength FROM drumTable WHERE cabSpec = '" + cableType + "'"
        getdrumDatafromSQL =rwModule.getTablefromSQL('','drumTable', sqlStr) 

        drumsliceTAG =  list(list(zip(*getdrumDatafromSQL))[0]);   drumsliceTAG.pop(0)
        drumsliceIndex = list(list(zip(*getdrumDatafromSQL))[1]);  drumsliceIndex.pop(0)
        drumsliceLength = list(list(zip(*getdrumDatafromSQL))[2]); drumsliceLength.pop(0)

        drumsliceLength =  list(map(int, drumsliceLength))
        
        # deduct all previously cut lengths from the drums 
        for i in range(len(drumCutDetails)):
            i_index = drumsliceTAG.index(drumCutDetails[i][0])
            drumsliceLength[i_index] = drumsliceLength[i_index] - int(drumCutDetails[i][1])      

            
        drumFiller(drumsliceIndex, drumsliceLength, cabSliceIndex, cabSliceLength, cableType, dateTimeStamp)     



        # filtDrumIndex, filtDrumLen = getReqDrum(appDataFromSite[3])               # get drums 
        # filtCabIndex,filtCabLen = getReqCable(appDataFromSite[3], uniqWbs[0])     # get cables [send just a default wbs (but it doesn't matter)]
        


        # ------------------Manage Cut Lengths here----------------------------------------------------------------------------------
        # delete cables those are cut and re adjust the drum substructing the cut lengths
        # check if the requested cut length is already updated in data base, if not update database with current required Cut length!
        #-----------------------------------------------------------------------------------------------------------------------------
        
        

        
        # drumFiller(filtDrumIndex, filtDrumLen, filtCabIndex, filtCabLen, reqCableType, dateTimeStamp)


    # for the first time when all cable-types needs to be computed, define cableType as * dringing call this function
    else: # if the request from engineering console with either cable type = '*' or a specific cableType
        if cableType == "*": # for later: add [rovision to run Pnp for a specific cableType from Engg. console
            
            populateInput(dataSource) # This function is built with global list to avoid multiple SQL server call
            
            # uniqDrumType = list(dict.fromkeys(drumCat))  # unique drum Type
            drumCat = 2
            uniqDrumType = list(set(drumCat))

            for cableType in uniqCabTypes:                                # get drum details for each cable
                if cableType in uniqDrumType:                             # if the matching drum is available then do it, else take next cable type
                    filtDrumIndex, filtDrumLen = getReqDrum(cableType)
                else: continue

                if freeWbs :                                                            # if free allocation accross all wbs
                    filtCabIndex,filtCabLen = getReqCable(cableType, uniqWbs[0])          # send a default wbs (doesn't matter)
                    drumFiller(filtDrumIndex, filtDrumLen, filtCabIndex, filtCabLen, cableType, dateTimeStamp)
                
                 
                else:                   
                                                                                      # if WBS wise drum allocation is required
                    for wbs in uniqWbs:
                        filtCabIndex,filtCabLen=getReqCable(cableType, wbs)
                        drumFiller(filtDrumIndex, filtDrumLen, filtCabIndex, filtCabLen, cableType, dateTimeStamp)


startOverall = time.perf_counter()

###################################################################################################################

def generateReport(cable_data, drum_data, jsonOutput):
    report = []    
       
    getindex = np.arange(cable_data.shape[0])                    # arr.shape[0] => no. of rows in arr; np.arange(n) => create array of n integer from 0 to n-1
    cable_data =  np.array(cable_data)[:, 0:4]                   # get a slice from cloumn 1 to 3 (note for 3 need to set 4)
    cable_data = np.insert(cable_data, 0, getindex, axis=1)      # insert a new column as its index
       
    
    getindex = np.arange(drum_data.shape[0])                     # arr.shape[0] => no. of rows in arr; np.arange(n) => create array of n integer from 0 to n-1
    drum_data =  np.array(drum_data)[:, 0:3]                     # get a slice from cloumn 1 to 2 (note for 2 need to set 3)
    drum_data = np.insert(drum_data, 0, getindex, axis=1)        # insert a new column as its index
    
     
    
    uniqCab_cat = list(dict.fromkeys(np.array(cable_data)[:, 3]))
    uniqDrum_cat = list(dict.fromkeys(np.array(drum_data)[:, 2]))
    uniq_Wbs = list(dict.fromkeys(np.array(cable_data)[:, 4]))
    
    
    
    no_of_cables = len(np.array(cable_data)[:, 2])
    cable_length = sum(np.array(cable_data)[:, 2])
    
      
    no_of_drums = len(np.array(drum_data)[0:, 3])
    drum_length = sum(np.array(drum_data)[0:, 3])
      
    
    no_of_type_of_cables = len(uniqCab_cat)
    no_of_WBS = len(uniq_Wbs)
    no_of_type_of_drums = len(uniqDrum_cat)
    
    
    
    # allottedDrums1 = np.array(jsonOutput, dtype=object)[0:,0]        # extracting drum sequence - step 1
    # allottedDrums1 = list(np.array(list(allottedDrums1))[0:,1])       # extracting drum sequence - step 2
    # allottedDrums1 = list(map(int, allottedDrums1))                   # convert string to integer
    
   
    allottedDrums = np.array(jsonOutput, dtype=object)[0:,0]        # extracting drum sequence - step 1
    allottedDrums = np.array(list(allottedDrums))[0:,1]       # extracting drum sequence - step 2
    allottedDrums = allottedDrums.astype(int) 
   
   
   
    
    allot_dr_list =np.array(jsonOutput, dtype=object)[0:,0].tolist()
    df_allot_dr = pd.DataFrame(allot_dr_list)
    df_allot_dr_grouped = df_allot_dr.groupby([0], as_index=False)[[3, 4]].agg(['sum']).reset_index()
    allot_dr_summary = np.array(df_allot_dr_grouped).tolist()
      
    # allot_dr_summary = df.groupby([0], as_index=False)[[3, 4]].agg(['sum']).reset_index()
    # allot_dr_summary = np.array(pd.DataFrame(allot_dr_list).groupby([0], as_index=False)[3,4].agg(['sum']).reset_index()).tolist() # deprecared 
            
    allotted_cab_arr = np.array(jsonOutput, dtype=object)[0:,1].flatten()
    # allottedCab = list(np.concatenate(allotted_cab_arr).flat)            # ****convert a list of list to another list
    allottedCab = np.array(np.concatenate(allotted_cab_arr).flat)
    #
    
    tmp_bool = np.in1d(np.array(cable_data, dtype=object)[0:,0], allottedCab)  # "np.in1d" allows filtering 2d array with another 1d array
    # allot_cab_list = np.array(cable_data, dtype=object)[tmp_bool].tolist()
   
    allot_cab_list = np.array(cable_data, dtype=object)[tmp_bool]
   
      
    allt_cab = pd.DataFrame(cable_data, dtype=object)[tmp_bool]
    allot_cab_summary = np.array(allt_cab.groupby([4,3], as_index=False).agg(Total = (2, "sum")).reset_index())
    allot_cab_summary = np.array(pd.DataFrame(allot_cab_summary).groupby([2], as_index=False).agg(Total = (3, "sum")).reset_index())
    allot_cab_summary = allot_cab_summary.tolist()
    
    
    #---
    no_of_allotted_cables = len(allottedCab) 
    
    allotted_cable_length = np.array(jsonOutput, dtype=object)[0:,3].flatten()
    allotted_cable_length = sum(list(np.concatenate(allotted_cable_length).flat))
    
    
    no_of_drums_used = len(allottedDrums)
 
    allottedDrum_length = np.array(jsonOutput, dtype=object)[0:,0]
    allottedDrum_length = list(np.array(list(allottedDrum_length))[0:,3])
    allottedDrum_length = list(map(int, allottedDrum_length)) 
    allottedDrum_length = sum(allottedDrum_length)
    
    leftOver_cable_length = np.array(jsonOutput, dtype=object)[0:,0].flatten()
    leftOver_cable_length = list(np.array(list(leftOver_cable_length))[0:,4])
    leftOver_cable_length = list(map(int, leftOver_cable_length)) 
    leftOver_cable_length = sum(leftOver_cable_length)   
        
    unAllotted_cables = list(set(np.array(cable_data, dtype=object)[0:,0]) - set(allottedCab))
    tmp_bool = np.in1d(np.array(cable_data, dtype=object)[0:,0], unAllotted_cables)  # "np.in1d" allows filtering 2d array with another 1d array
    unAllot_cab_list = np.array(cable_data, dtype=object)[tmp_bool]
    
    unallt_cab = pd.DataFrame(cable_data, dtype=object)[tmp_bool]
    unAllot_cab_summary = np.array(unallt_cab.groupby([4,3],as_index=False).agg(Total = (2, "sum")).reset_index())
    unAllot_cabType_summary = np.array(pd.DataFrame(unAllot_cab_summary).groupby([2],as_index=False).agg(Total = (3, "sum")).reset_index())
    
    unAllot_cab_summary = unAllot_cab_summary.tolist()              # WBS wise summary
    unAllot_cabType_summary = unAllot_cabType_summary.tolist()      # Overall Summary (not currently being reported)
    
    no_of_unAllotted_cables = len(unAllotted_cables)
    unAllotted_cables_length = sum(unAllot_cab_list[0:, 2])
  
    
    unAllotted_drums = list(set(np.array(drum_data, dtype=object)[0:,0]) - set(allottedDrums))
    tmp_bool = np.in1d(np.array(drum_data, dtype=object)[0:,0], unAllotted_drums)  # "np.in1d" allows filtering 2d array with another 1d array
    unAllot_dr_list = np.array(drum_data, dtype=object)[tmp_bool]
        
    
    unAllot_dr_type_summary = np.array(pd.DataFrame(unAllot_dr_list).groupby([2],as_index=False).agg(Total = (3, "sum")).reset_index())
    unAllot_dr_type_summary = unAllot_dr_type_summary.tolist()
        
    no_of_full_spare_drums = len(unAllot_dr_list[0:,3])
    full_spare_drum_length = sum(unAllot_dr_list[0:,3])
    
    dr_with_Lo = np.array(jsonOutput, dtype=object)[0:,0].flatten()
    tmp_bool = np.array(list(map(int, (np.array(list(dr_with_Lo))[0:,4])))) > 0
    dr_with_Lo = (dr_with_Lo)[tmp_bool]
    
    
    no_of_partial_spare_drums = dr_with_Lo.shape[0]
    partial_spare_drum_length = list(np.array(list(dr_with_Lo))[0:,4])
    partial_spare_drum_length = sum(list(map(int, partial_spare_drum_length)))
    
     
    
    cabType_with_NO_drum = len(list(set(np.array(uniqCab_cat)) - set(np.array(uniqDrum_cat))))
    
       
    wastage = 0
    wastage_indicator = 0
    no_of_joints = 0
    
    
    # creating a python dictionary manually below. This will be parse into a jason object using 'json.dumps()'. 
    
    ds_stat = {
        "no_of_cables": int(no_of_cables),
        "cable_length": int(cable_length),
        "no_of_type_of_cables": int(no_of_type_of_cables),
        "no_of_WBS": int(no_of_WBS),
        "no_of_drums": int(no_of_drums),
        "drum_length": int(drum_length),
        "no_of_type_of_drums": int(no_of_type_of_drums),
        "no_of_unAllotted_cables": int(no_of_unAllotted_cables),
        "unAllotted_cables_length": int(unAllotted_cables_length),
        "cabType_with_NO_drum": int(cabType_with_NO_drum),
        "no_of_allotted_cables": int(no_of_allotted_cables),
        "allotted_cable_length": int(allotted_cable_length),
        "no_of_drums_used": int(no_of_drums_used),
        "no_of_full_spare_drums": int(no_of_full_spare_drums),
        "full_spare_drum_length": int(full_spare_drum_length),
        "no_of_partial_spare_drums": int(no_of_partial_spare_drums),
        "partial_spare_drum_length": int(partial_spare_drum_length),
        "no_of_joints": int(no_of_joints),
        "wastage": int(wastage),
        "wastage_indicator": int(wastage_indicator)        
        }

    unAllot_cab_list = unAllot_cab_list.tolist()    #convert nu,py array to a list and convert to json
    # unAllot_cab_list = json.dumps(unAllot_cab_list)
    
    unAllot_dr_list = unAllot_dr_list.tolist()
    # unAllot_dr_list = json.dumps(unAllot_dr_list)
    
    #  add drum tag to allotted cable list
    
    
    
    matching_dr_tag = np.array(np.array(new_func(jsonOutput, dtype=object))[0:, 2:3]).ravel() # get the corresponding drum index and tag 
        
    dr_col_index = np.zeros(allottedCab.shape[0], dtype = int)
    dr_col_tag = np.zeros(allottedCab.shape[0], dtype = object)

    k = 0 

 
    for i in range(allotted_cab_arr.shape[0]):
        for _ in range(len(allotted_cab_arr[i])):
            dr_col_index[k] = allottedDrums[i]
            dr_col_tag[k] = matching_dr_tag[i]
            k += 1
          
    
    order_allottedCab = np.argsort(allottedCab) # get the order of cable index
 
    # we are taking advantage of the fact that allot_cab_list is in strictly (exclusively) ascending order. This is because we have not altered the cable input array received from excel
    allot_cab_list = np.column_stack((allot_cab_list, dr_col_tag[order_allottedCab]))               #  reorder the index with "dr_col_tag[order_allottedCab])" 
    allot_cab_list = np.column_stack((allot_cab_list, dr_col_index[order_allottedCab])).tolist()
    
    # print('output: ', allot_cab_list)                                                             
        
    
    # cable_data.to_json(orient='records', lines=False)   
       
    ds_report = {        
        "statistics": ds_stat,                
        "unallot_cab_summary" : unAllot_cab_summary,
        "unallot_cab_list" : unAllot_cab_list,        
        "allot_cab_summary" : allot_cab_summary,
        "allot_cab_list": allot_cab_list,        
        "unallt_dr_summary": unAllot_dr_type_summary,
        "unallot_dr_list": unAllot_dr_list,        
        "allot_dr_summary": allot_dr_summary,
        "allot_dr_list" : allot_dr_list       
       }

            
    return ds_report

def new_func(jsonOutput, dtype=object):
    return np.array(jsonOutput, dtype=object)[0:, 0].tolist()
 
