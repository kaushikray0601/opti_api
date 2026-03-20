"""Core optimizer orchestration.

The active API path is `control_panel -> allocate_drum_schedule -> report_builder`.
The legacy compatibility code further below is intentionally kept for reference/parity
and should not receive new feature work.
"""

from datetime import datetime
import time
import numpy as np

from optimizer.core.dp_engine import (
    create_dp_table,
    fill_drums_sequentially,
    modified_search_algo,
)
from optimizer.core.ds_settings_parser import DSSettingsError, unpack_ds_settings
from optimizer.core.input_normalizer import (
    OptimizerInputError,
    normalize_optimizer_inputs,
)
from optimizer.core.preorder_planner import PlanInputs, PreOrderPlanningError, build_preorder_plan
from optimizer.core.report_builder import build_report, build_schedule_output

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

    try:
        parsed_settings = unpack_ds_settings(ds_settings)
        if parsed_settings.is_pre_order:
            plan_inputs = build_preorder_plan(users_cable_data, parsed_settings)
        else:
            normalized_input = normalize_optimizer_inputs(
                users_cable_data,
                users_drum_data,
            )
            plan_inputs = _build_post_order_plan(normalized_input)
    except (OptimizerInputError, DSSettingsError, PreOrderPlanningError) as exc:
        return {"error": str(exc)}

    jsonOutput = build_schedule_output(
        plan_inputs.cable_rows,
        plan_inputs.drum_rows,
        plan_inputs.drum_data,
        plan_inputs.drum_schedule,
        rev_no,
    )

    ds_report = generateReport(
        plan_inputs.cable_rows,
        plan_inputs.drum_rows,
        jsonOutput,
    )
    ds_report["ds"] = jsonOutput
    ds_report["computeTime"] = str(round((time.time() - startTimer), 3)) + "s"
    return ds_report


def _build_post_order_plan(normalized_input):
    return PlanInputs(
        cable_rows=normalized_input.cable_rows,
        drum_rows=normalized_input.drum_rows,
        drum_data=normalized_input.drum_data,
        drum_schedule=allocate_drum_schedule(normalized_input),
    )


def allocate_drum_schedule(normalized_input):
    drum_schedule = []

    for current_cable_type in normalized_input.unique_cable_types:
        drum_group = normalized_input.drums_by_type.get(current_cable_type)
        if drum_group is None:
            continue

        filtDrumIndex, filtDrumLen = drum_group
        if free_Wbs:
            cable_group = normalized_input.cables_by_type.get(current_cable_type)
            if cable_group is None:
                continue
            filtCabIndex, filtCabLen = cable_group
            dS_for_this_CableType = drumFiller(
                filtDrumIndex,
                filtDrumLen,
                filtCabIndex,
                filtCabLen,
                current_cable_type,
            )
            drum_schedule.append(dS_for_this_CableType)
        else:
            for wbs in normalized_input.unique_wbs:
                filtCabIndex, filtCabLen = getReqCable(
                    current_cable_type,
                    wbs,
                    normalized_input.cable_data,
                )
                dS_for_this_CableType = drumFiller(
                    filtDrumIndex,
                    filtDrumLen,
                    filtCabIndex,
                    filtCabLen,
                    current_cable_type,
                )
                drum_schedule.append(dS_for_this_CableType)

    return drum_schedule
   

# Legacy compatibility surface retained from the pre-refactor code path.
# Keep it stable for reference only; route all new work through `control_panel`.
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
def createDPTable(target, cabIndex, cabLen, cabletype):
    return create_dp_table(target, cabIndex, cabLen, cabletype)


def modifiedSearchAlgo(target, cabIndex, cabLen, cabletype):
    return modified_search_algo(target, cabIndex, cabLen, cabletype)

#############################################################################################
def drumFiller(filtDrumIndex, filtDrumLen, cabIndex, cabLen, cable_type):
    return fill_drums_sequentially(
        filtDrumIndex,
        filtDrumLen,
        cabIndex,
        cabLen,
        cable_type,
    )

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
    return build_report(cable_data, drum_data, jsonOutput)

def new_func(jsonOutput, dtype=object):
    return np.array(jsonOutput, dtype=object)[0:, 0].tolist()
 
