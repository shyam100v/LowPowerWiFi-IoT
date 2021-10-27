# This code is for batch processing ns3 trace and PHY state logs for PSM with uplink TCP traffic
# Author : Shyam Krishnan Venkateswaran
# Email: shyam1@gatech.edu
# Variables to take care of before each run will be tagged with #changeThisBeforeRun


# %%

import numpy as np
import matplotlib.pyplot as plt
import csv
from matplotlib.pyplot import figure
import json
import random
import glob     # for parsing directories
import os       # for clearing terminal in windows OS
import pandas as pd
from pathlib import Path       # to handle directories across OSs
from random import randrange



# %%

# File management

# Output CSV file name
csvFileName = 'trialOct25.csv'          #changeThisBeforeRun
StaNodeDeviceStringASCII = "NodeList/1/DeviceList/0"           # note: Make sure this is the STA node and interface of interest from ns3. Other network events will be ignored.
ApNodeDeviceStringASCII = "NodeList/0/DeviceList/1"           # note: Make sure this is the AP node and interface of interest from ns3. Other network events will be ignored.

# Following lists will be appended at the end of each iteration. The lists are ordered and correspond to each other in the correct order.
index_list = [] 
networkRTT_ms_list = []
timeToNextBeacon_ms_list = []
averageCurrent_mA_list = []
# TCP_indexToPick = -2            #changeThisBeforeRun

# Generating list of logs to import
# stateLog files must be named as 'stateLog#####.log', where ##### are 5 numbers 0-9
# asciiTrace files must be named as 'asciiTrace#####.tr', where ##### are 5 numbers 0-9
# The '#####' will be used as IDs to find corresponding log - trace pairs. 

data_folder = Path("logs/")                                             #changeThisBeforeRun
ns3_sim_log_list_temp = list(data_folder.glob("**/*.log"))
ns3_sim_log_list = [str(x) for x in ns3_sim_log_list_temp]
ns3_ascii_log_list_temp = list(data_folder.glob("**/*.tr"))
ns3_ascii_log_list = [str(x) for x in ns3_ascii_log_list_temp]


ns3_sim_log_list.sort()

ns3_ascii_log_list.sort()
logCount = len(ns3_sim_log_list)


# For random log selection ------------------------------below - just delete this block for batch processing
# chosenLog = randrange(logCount)
chosenLog = 0
print(f"Chosen log: {chosenLog}")

ns3_sim_log_list = [ns3_sim_log_list[chosenLog]]
ns3_ascii_log_list = [ns3_ascii_log_list[chosenLog]]
logCount = 1
print(f"Chosen log: {ns3_sim_log_list}")

# For random log selection ------------------------------Above


print(f"Number of logs to be processed: {logCount}")
# -----------------------------------------------------------
# -----------------------------------------------------------


# %%
# All configuration parameters, numerical values and adjustments are defined here. 

stateDict = {}                  # This is the master dict storing state names and current values in mA
durationDict = {}               # This dictionary contains the durations for manually added states in us (micro seconds)     
milliSecToPlot = 1024    # This sets how much data will be plotted
timeUnits = milliSecToPlot*1000  
stateLogStartTime_us = 0.2 * 1e6          # PHY state log will be imported only after this time from beginning
enableStateTransitions = True         # If enabled, state transitions will be added
enableBufferCurrent = False             # If enabled, different (higher) current will be used for SLEEP states with unACK'ed TCP packets, else - same as SLEEP



# State Dictionary definition - Current values are in Amperes

stateDict["SLEEP"] =  0.12e-3                                        # IDLE state - will be assigned LPDS current after processing
stateDict["ON"] =  66e-3                                            # Used for Always on power modes - value from experiments
stateDict["RX"] = 50e-3    
stateDict["IDLE"] =  stateDict["RX"]                                    # IDLE state - will be assigned Rx current after processing
stateDict["SLEEP_BUFFER"] =  10e-3                                  # Sleep state while waiting for TCP ACK 
# stateDict["BCN_RX"] =  45e-3                                        # For Beacon Rx - from datasheet
stateDict["BCN_RX"] =  stateDict["RX"]                                        # For Beacon Rx - changed for ICC paper
stateDict["TX"] = 232e-3                                            # This will be referenced in multiple Tx states but not used directly
stateDict["RX_FULL"] = stateDict["RX"]                                        # This will be referenced in multiple Rx states but not used directly
                                        


stateDict["ACK_802_11_RX"] = stateDict["RX_FULL"]                       # Wi-Fi ACK Rx current
stateDict["ACK_802_11_TX"] =  stateDict["TX"]                           # Set to Tx current
stateDict["TCP_TX"] =  stateDict["TX"]                                  # Set to Tx current
stateDict["TCP_ACK_RX"] = stateDict["RX_FULL"] 
stateDict["PSPOLL_TX"] =  stateDict["TX"]                               # Set to Tx current


stateDict["BCN_RAMPUP"] =  4.5e-3                                   # Ramp up to beacon Rx from LPDS
stateDict["BCN_RAMPDOWN"] =  12.5e-3                                # Ramp down from Beacon Rx to LPDS
stateDict["BCN_RAMPUP_BUFFER"] =  32e-3                              # Ramp up to Beacon Rx from Sleep (10 mA)
stateDict["BCN_RAMPDOWN_BUFFER"] =  12.5e-3                          # Ramp down from Beacon Rx to Sleep (10 mA)


stateDict["TCP_TX_RAMPUP"] =  25e-3  
stateDict["TCP_TX_RAMPDOWN"] =  36e-3                               # This will be added after 802.11 ACK Rx
stateDict["TCP_TX_RAMPUP_BUFFER"] =  36e-3                               # Not used yet - when STA wakes up to send another TCP packet with unACK'ed packets already
stateDict["TCP_TX_RAMPDOWN_BUFFER"] =  36e-3                               # This will be added after 802.11 ACK Rx when buffer takes extra current

stateDict["ACK_802_11_RX_RAMPDOWN"] = 28e-3 
stateDict["ACK_802_11_RX_RAMPDOWN_BUFFER"] = 36e-3 

stateDict["ACK_802_11_TX_RAMPDOWN"] = 65e-3 
# stateDict["ACK_802_11_RX_RAMPDOWN"] =  28e-3 



stateDict["TCP_RAMPUP_SLEEP_TO_TCP_ACK_RX"] =  20e-3  
    

# has to be taken care of ------ Below ****************
# TCP_WAIT_ACK_CURRENT = 50e-3    # Use only for no PSM - Active till TCP ACK
# TCP_WAIT_ACK_CURRENT = IDLE_CURRENT    # Use only for no PSM - LPDS till TCP ACK



# TCP_TX_RAMPDOWN_CURRENT = 28e-3       # Use this only for special case - TCP-Tx-No PSM-- LPDS--TCP ACK Rx
# durationDict["TCP_TX_rampDown"] = 6000        # Use this only for special case - TCP-Tx-No PSM-- LPDS--TCP ACK Rx  


# has to be taken care of ------ Above *********************


 


# Durations ------------------------- in micro seconds

durationDict["BCN_rampUp"]                  = 2600                                              # From LPDS
durationDict["BCN_rampDown"]                = 800                                               # From LPDS
durationDict["BCN_rampUp_fromSleepBuffer"]        = durationDict["BCN_rampUp"]
durationDict["BCN_rampDown_toSleepBuffer"]        = durationDict["BCN_rampDown"]

durationDict["TCP_TX_rampUp"]               = 23500
durationDict["TCP_TX_rampDown"]             = 5500                                              
durationDict["TCP_SLEEP_TO_TCP_ACK_RX_rampUp"] = 5000

durationDict["ACK_802_11_RX_rampDown"] = 5500 
durationDict["ACK_802_11_TX_rampDown"] = 1300 
# durationDict["ACK_802_11_RX_rampDown_toSleepBuffer"] = 5500 




enableAlwaysOn = False
useCase = 'TCP'




# %%
# Function definition for state comparison and priority assignment

def stateCompare(state1, state2):
    """
    Parameters
    ----------
    state1 : Name of first state as a string. 
    state2 : Name of first state as a string.
    Returns
    -------
    Returns boolean = current (state1) > current (state2)
    That is, True if current consumption of state1 is higher. 
    If stateCompare (state1, state2) returns True, state2 can be replaced with state1 IF NECESSARY.

    """
    
    return stateDict[state1] > stateDict[state2]
    
# %%
# ----------------------------------------------------------------------------------------------------10380
# Master Loop starts here


for logFilesCounter in range(logCount):
    
    logFilesCounter = 0
    # Only simulation logs are imported
    ns3_sim_log = ns3_sim_log_list[logFilesCounter]
  
    ns3_ascii_log = ns3_ascii_log_list[logFilesCounter]
    # Checking if log and trace files have the same number
    if (ns3_sim_log.split('.')[0][-5:] != ns3_ascii_log.split('.')[0][-5:]  ):
        print(f"Log and trace file numbers do not match at number = {logFilesCounter}. Aborting.")
    index_list.append(ns3_sim_log.split('.')[0][-5:])
    print(f"\nProcessing log file ({logFilesCounter+1}/{logCount})")
    
    

    stateVector = []
    durationVector = []
    timeStampVector = []
    with open(ns3_sim_log) as tsv:
        #for line in csv.reader(tsv, dialect="excel-tab"):
        prevState = 'None'
        for line in csv.reader(tsv, delimiter = ";"):
            # print(line)
            currentState = line[0].split("=")[1]

            currentTimeStamp = int(line[1].split("=")[1])
            # currentTimeStamp = np.ceil( currentTimeStamp/1000)
            
            
            currentDuration = int(line[2].split("=")[1])
            # currentDuration = np.ceil( currentDuration/1000)
            #Adding before rounding.
            currentTimeStamp = currentTimeStamp + currentDuration   

            currentDuration = int( currentDuration/1000)
            currentTimeStamp = int( currentTimeStamp/1000)


            # Note : currentTimeStamp is the time when the state completes. Not when it begins.

            

            if (currentTimeStamp < stateLogStartTime_us ):
                continue
            
            if currentState == "CCA_BUSY" and prevState == "SLEEP":
                # Bug with ns3 state logging system - Every SLEEP state is followed by a duplicate CCA_BUSY state - should be ignored
                # print (f"Found CCA_BUSY after SLEEP at time = {currentTimeStamp}; Skipping.")
                continue
            
            if currentState == "CCA_BUSY":
                currentState = "IDLE"

            if currentState == "SLEEP" and prevState == "IDLE":
                stateVector[-1] = "SLEEP"
                prevState = "SLEEP"

            if prevState == currentState:
                # Consequtive states that are the same - consolidating
                durationVector[-1] = int(durationVector[-1] + currentDuration)
                timeStampVector[-1] = int(timeStampVector[-1] + currentDuration)
                # print (f"Added {currentDuration} to previous state")
                continue

            prevState = currentState
            

            # #print(currentTimeStamp)
            # currentState = line[4]
            # currentState = currentState.split("=")[1]
            # currentDuration = line[-1]
            
            # currentDuration = currentDuration.split("+",1)[1]
            # #print(currentDuration)
            # currentDuration = float(currentDuration.split("ns")[0])
            # #print(currentDuration)
            # #******************************************* approximating to precision of 1 microseconds
            # currentDuration = int(currentDuration/1000)
            # currentDuration = int(np.ceil(currentDuration))
            # #print(f"{currentState}, {currentDuration}")
            # print (f"currentState={currentState}, StateStartedAt={currentTimeStamp-currentDuration}, currentTimeStamp={currentTimeStamp}, currentDuration={currentDuration}")
            if (currentDuration >0.0):
                stateVector.append(currentState)
                durationVector.append(int(currentDuration))
                timeStampVector.append(int(currentTimeStamp))
            
    # print(timeStampVector)
    # Importing ASCII trace as a dictionary
    ascii_ns3_traceDict = dict()
    with open(ns3_ascii_log) as file1:
        Lines = file1.readlines() 
        for line in Lines: 
            if (StaNodeDeviceStringASCII not in line ) and (ApNodeDeviceStringASCII not in line):
                # print (f"Node of interest not found in Line: {line}; Skipping this line")
                continue
            timeStamp = int (int(line.split(" ")[1]) / 1000)
            ascii_ns3_traceDict[timeStamp]= line
            #print(timeStamp)


    # print(json.dumps(ascii_ns3_traceDict, indent=1))   
                        




    # %%
    # Tagging the log File. This is before current values are assigned
    # CCA_BUSY is changed to IDLE
    # If always ON mode is enabled, IDLE is replaced with ON
    # All adjacent but same states are combined
    # TCP states are identified and assigned


    stateVectorLength = len(stateVector)
    timeStampVectorModified = []
    stateVectorModified = []
    durationVectorModified = []
    for ii in range(stateVectorLength):
        
        # # Replacing all CCA_BUSY with IDLE
        # if stateVector[ii]== 'CCA_BUSY':
        #     stateVector[ii] = 'IDLE'
        if stateVector[ii]== 'IDLE' and enableAlwaysOn:
            stateVector[ii] = 'ON'
        # Finding BCN_RX and 802.11 ACK receptions
        # print(f"timeStampVector[ii] = {timeStampVector[ii]}")
        if timeStampVector[ii] in ascii_ns3_traceDict:

            tempASCIItrace = ascii_ns3_traceDict[timeStampVector[ii]]
            # print(f"At time {timeStampVector[ii]}, ASCII trace is \n {tempASCIItrace}")
            if stateVector[ii]== 'RX' and ("RxOk" in tempASCIItrace) and (tempASCIItrace.split(" ")[0]=="r") and ("MGT_BEACON" in tempASCIItrace):  
                stateVector[ii] = "BCN_RX"
                # print (f"BCN RX found. Prev state is: {stateVector[ii - 1]}")
                # If previous state is IDLE, change it to SLEEP so that it will be combined with preceding SLEEP state. Else rampup cannot be added.
                if (ii > 0) and stateVector[ii - 1]== "IDLE":
                    # print (f"Changing prev IDLE to SLEEP")
                    stateVectorModified[-1] = "SLEEP"

            elif stateVector[ii]== 'TX' and (ApNodeDeviceStringASCII in tempASCIItrace) and ("TcpHeader" in tempASCIItrace) and ("RxOk" in tempASCIItrace):
                stateVector[ii] = 'TCP_TX'


            elif stateVector[ii]== 'TX' and (ApNodeDeviceStringASCII in tempASCIItrace) and ("CTL_PSPOLL" in tempASCIItrace) and ("RxOk" in tempASCIItrace):
                stateVector[ii] = 'PSPOLL_TX'


            elif stateVector[ii]== 'TX' and (ApNodeDeviceStringASCII in tempASCIItrace) and ("CTL_ACK" in tempASCIItrace) and ("RxOk" in tempASCIItrace):
                stateVector[ii] = 'ACK_802_11_TX'
            
            
            elif stateVector[ii]== 'RX' and ("CTL_ACK" in tempASCIItrace) and (tempASCIItrace.split(" ")[0]=="r") and ("RxOk" in tempASCIItrace):
                stateVector[ii] = 'ACK_802_11_RX'
                 

                #print(f"TCP Tx found at t = {timeStampVector[ii]}")
            elif stateVector[ii]== 'RX' and ("TcpHeader" in tempASCIItrace) and (tempASCIItrace.split(" ")[0]=="r") and ("RxOk" in tempASCIItrace) and ("[ACK]" in tempASCIItrace):
                stateVector[ii] = 'TCP_ACK_RX'
                #print(f"TCP ACK found at t = {timeStampVector[ii]}")
            elif stateVector[ii] != 'IDLE':
                print(f"State not tagged at ii: {ii}: {stateVector[ii]}")
                print(f"tempASCIItrace:{tempASCIItrace}")
        else:
            print (f"timeStampVector[ii]= {timeStampVector[ii]} not found in ASCII trace. State is {stateVector[ii]}")



        # To combine adjacent same states  
        # if ii == 0:
        #     #prevState = stateVector[ii]
        stateVectorModified.append(stateVector[ii])
        durationVectorModified.append(durationVector[ii])
        timeStampVectorModified.append(timeStampVector[ii])
        # elif (stateVector[ii] == stateVectorModified[-1]):
        #     durationVectorModified[-1] = durationVectorModified[-1] + durationVector[ii]
        # else:
        #     stateVectorModified.append(stateVector[ii])
        #     durationVectorModified.append(durationVector[ii])
        #     timeStampVectorModified.append(timeStampVector[ii])
    durationVectorModified = [int(i) for i in durationVectorModified]

    print (stateVectorModified)
    

    # %%
    # Combining same adjacent states

    # print (f"Before state consolidation: ")
    # print (f"stateVectorModified:{stateVectorModified}")
    # print (f"durationVectorModified:{durationVectorModified}")
    # print (f"timeStampVectorModified:{timeStampVectorModified}")

    stateVectorLength = len(stateVectorModified)
    timeStampVectorTemp = timeStampVectorModified
    stateVectorTemp = stateVectorModified 
    durationVectorTemp = durationVectorModified

    timeStampVectorModified = []
    stateVectorModified = []
    durationVectorModified = []

    for ii in range(stateVectorLength):
        # print (f"stateVectorTemp[ii]:{stateVectorTemp[ii]};stateVectorModified:{stateVectorModified}")
        if ii == 0:
            stateVectorModified.append(stateVectorTemp[ii])
            durationVectorModified.append(durationVectorTemp[ii])
            timeStampVectorModified.append(timeStampVectorTemp[ii])
        elif stateVectorTemp[ii] == stateVectorModified[-1]:
            durationVectorModified[-1] += durationVectorTemp[ii]
            timeStampVectorModified[-1] += timeStampVectorTemp[ii]
        else:
            stateVectorModified.append(stateVectorTemp[ii])
            durationVectorModified.append(durationVectorTemp[ii])
            timeStampVectorModified.append(timeStampVectorTemp[ii])

    # print (f"After state consolidation: ")
    # print (f"stateVectorModified:{stateVectorModified}")
    # print (f"durationVectorModified:{durationVectorModified}")
    # print (f"timeStampVectorModified:{timeStampVectorModified}")
    


            

    # %%
    # Find the timestamp of a chosen proper TCP Tx, and center it at 500 ms in our window. 
    # Find the network RTT for this TCP Tx
    # Find Time till next beacon

    
    # chosenTCP_TX_ii = stateVectorModified.index('TCP_TX')
    # chosenTCP_TX_TimeStamp = timeStampVectorModified[chosenTCP_TX_ii]
    # chosenTCP_ACK_RX_ii = stateVectorModified.index('TCP_ACK_RX', chosenTCP_TX_ii)
    # chosenTCP_ACK_RX_TimeStamp = timeStampVectorModified[chosenTCP_ACK_RX_ii]
    # networkRTT_us = chosenTCP_ACK_RX_TimeStamp - chosenTCP_TX_TimeStamp
    # nextBeacon_ii = stateVectorModified.index('BCN_RX', chosenTCP_TX_ii)
    # nextBeacon_TimeStamp = timeStampVectorModified[nextBeacon_ii]
    # timeToNextBeacon_us = nextBeacon_TimeStamp - chosenTCP_TX_TimeStamp
    # firstTCP_TX_TimeStamp_inWindow = chosenTCP_TX_TimeStamp - timeStampVectorModified[0]
    # # print(f"TCP Tx occurs {(firstTCP_TX_TimeStamp_inWindow)/1e6} seconds from Beginning of the window \nTo have TCP Tx exactly at 0.5 seconds in the window, the ns3 logs must be advanced in time by {firstTCP_TX_TimeStamp_inWindow - 0.5e6} us")



    # TCPindices = [i for i, xstate in enumerate(stateVectorModified) if xstate == "TCP_TX"]
    # chosenTCP_TX_ii = TCPindices[TCP_indexToPick]                           
    # chosenTCP_TX_TimeStamp = timeStampVectorModified[chosenTCP_TX_ii]
    # chosenTCP_ACK_RX_ii = stateVectorModified.index('TCP_ACK_RX', chosenTCP_TX_ii)
    # chosenTCP_ACK_RX_TimeStamp = timeStampVectorModified[chosenTCP_ACK_RX_ii]
    # networkRTT_us = chosenTCP_ACK_RX_TimeStamp - chosenTCP_TX_TimeStamp
    # nextBeacon_ii = stateVectorModified.index('BCN_RX', chosenTCP_TX_ii)
    # nextBeacon_TimeStamp = timeStampVectorModified[nextBeacon_ii]
    # timeToNextBeacon_us = nextBeacon_TimeStamp - chosenTCP_TX_TimeStamp
    # firstTCP_TX_TimeStamp_inWindow = chosenTCP_TX_TimeStamp - timeStampVectorModified[0]
    # # print(f"TCP Tx occurs {(firstTCP_TX_TimeStamp_inWindow)/1e6} seconds from Beginning of the window \nTo have TCP Tx exactly at 0.5 seconds in the window, the ns3 logs must be advanced in time by {firstTCP_TX_TimeStamp_inWindow - 0.5e6} us")


    # advanceInTimeNs3_1uS = int(firstTCP_TX_TimeStamp_inWindow - 0.3e6)

                
                
    # %%

    # handling 'ON' state for PS-POLL and multicast downlink mechanisms
    # Logic: Look for all beacons -> until a SLEEP state is found, change all IDLE to ON. Leave other states as they are.
    stateVectorTemp = stateVectorModified
    durationVectorTemp = durationVectorModified
    timeStampVectorTemp = timeStampVectorModified

    stateVectorLength = len(stateVectorModified)

    for ii in range(stateVectorLength):
        if (stateVectorModified[ii] == 'BCN_RX'):
            # Look for next sleep state
            for counter in range(20):
                if (ii + counter) >= stateVectorLength:
                    break
                if stateVectorModified[ii + counter] == 'SLEEP':
                    break
                elif stateVectorModified[ii + counter] == 'IDLE':
                    stateVectorModified[ii + counter] = 'ON'

    # %%
    # Adding Beacon ramp up and down
    # For BCN_RX states, adding Ramp up and Ramp down if IDLE state is available

    # print(f"Before beacon rampUP down: Total duration: {np.sum(durationVectorModified)}")
    if (enableStateTransitions):
        stateVectorRampUpDown = []
        durationVectorRampUpDown = []
        timeStampVectorRampUpDown = []
        addedAlreadyLookAhead = False

        stateVectorLength = len(stateVectorModified)
        for ii in range(stateVectorLength):
            if addedAlreadyLookAhead:
                addedAlreadyLookAhead = False
                continue
            if ii==0 or ii == stateVectorLength-1 and not(addedAlreadyLookAhead) :
                stateVectorRampUpDown.append(stateVectorModified[ii])
                durationVectorRampUpDown.append(durationVectorModified[ii])
                timeStampVectorRampUpDown.append(timeStampVectorModified[ii])
                continue
            if (stateVectorModified[ii] == 'BCN_RX'):
                # The state is BCN_RX. Look to add BCN_RAMPUP
                # print (f"stateVectorRampUpDown[-1] ={stateVectorRampUpDown[-1]}; durationVectorRampUpDown[-1] = {durationVectorRampUpDown[-1]}; Ramp up required = {durationDict['BCN_rampUp']}")
                isPreviousStateIDLEorSLEEP = (stateVectorRampUpDown[-1] == 'IDLE') or (stateVectorRampUpDown[-1] == 'SLEEP')
                if (  isPreviousStateIDLEorSLEEP and durationVectorRampUpDown[-1] >= durationDict["BCN_rampUp"]):
                    durationVectorRampUpDown[-1] = durationVectorRampUpDown[-1] - durationDict["BCN_rampUp"]
                    stateVectorRampUpDown.append('BCN_RAMPUP')
                    durationVectorRampUpDown.append(durationDict["BCN_rampUp"])
                    timeStampVectorRampUpDown.append(timeStampVectorModified[ii] - durationDict["BCN_rampUp"])
                elif (isPreviousStateIDLEorSLEEP and durationVectorRampUpDown[-1] < durationDict["BCN_rampUp"]):
                    # insufficient IDLE state. Just  convert what is available
                    stateVectorRampUpDown[-1] = 'BCN_RAMPUP'
                    
                else:
                    pass
                    print(f"Error at ii: {ii}. Could not add beacon RampUp")
                # Adding RX state
                stateVectorRampUpDown.append('BCN_RX')
                durationVectorRampUpDown.append(durationVectorModified[ii])
                timeStampVectorRampUpDown.append(timeStampVectorModified[ii])
                
                
                #Look to add BCN_RAMPDOWN
                isNextStateIDLEorSLEEP = (stateVectorModified[ii+1] == 'IDLE') or (stateVectorModified[ii+1] == 'SLEEP')
                if (isNextStateIDLEorSLEEP and durationVectorModified[ii+1] >= durationDict["BCN_rampDown"]):
                    addedAlreadyLookAhead = True
                    stateVectorRampUpDown.append('BCN_RAMPDOWN')
                    durationVectorRampUpDown.append(durationDict["BCN_rampDown"])
                    timeStampVectorRampUpDown.append(timeStampVectorModified[ii+1])
                    # Adding next idle time after deduction
                    stateVectorRampUpDown.append('SLEEP')           #shyam - note
                    durationVectorRampUpDown.append(durationVectorModified[ii+1] - durationDict["BCN_rampDown"])
                    timeStampVectorRampUpDown.append(timeStampVectorModified[ii+1]+ durationDict["BCN_rampDown"])
                elif (isNextStateIDLEorSLEEP and durationVectorModified[ii+1] < durationDict["BCN_rampDown"]):
                    stateVectorModified[ii+1] == 'BCN_RAMPDOWN'

        
        
            else:
                # Just some other state
                stateVectorRampUpDown.append(stateVectorModified[ii])
                durationVectorRampUpDown.append(durationVectorModified[ii])
                timeStampVectorRampUpDown.append(timeStampVectorModified[ii])

    else:
        stateVectorRampUpDown = stateVectorModified
        durationVectorRampUpDown = durationVectorModified
        timeStampVectorRampUpDown = timeStampVectorModified    
    

        
    # %%

    # If case is TCP and sleep buffer has different current, change sleep to sleep/idle buffer and consolidate states.



    # %%
    # For TCP_TX states, adding Ramp up, intermediate, and Ramp down if IDLE state is available. Sleep state beacon ramp ups and downs are also updated here
    if useCase == 'TCP':
        stateVectorModified = stateVectorRampUpDown * 1
        durationVectorModified = durationVectorRampUpDown * 1
        timeStampVectorModified = timeStampVectorRampUpDown * 1
        stateVectorRampUpDown = []
        durationVectorRampUpDown = []
        timeStampVectorRampUpDown = []
        addedAlreadyLookAhead = False

        stateVectorLength = len(stateVectorModified)
        for ii in range(stateVectorLength):
            if addedAlreadyLookAhead:
                addedAlreadyLookAhead = False
                continue
    #         if (ii==0 or ii == stateVectorLength-1) and not(addedAlreadyLookAhead) :
    #             stateVectorRampUpDown.append(stateVectorModified[ii])
    #             durationVectorRampUpDown.append(durationVectorModified[ii])
    #             timeStampVectorRampUpDown.append(timeStampVectorModified[ii])
    #             continue
        #   

            if (stateVectorModified[ii] == 'TCP_TX'):
                # Adding RampUp
                # if (stateVectorRampUpDown[-1] == 'IDLE' and durationVectorRampUpDown[-1] >= durationDict["TCP_TX_rampUp"]): 
                if (enableStateTransitions):

                    remainingRampUpDuration = durationDict["TCP_TX_rampUp"]
                    temp_stateVector = []
                    temp_durationVector = []
                    temp_timeStampVector = []
                    while (remainingRampUpDuration > 0):
                        if (durationVectorRampUpDown[-1] <= remainingRampUpDuration):
                            remainingRampUpDuration = remainingRampUpDuration - durationVectorRampUpDown[-1]
                            #print(stateVectorRampUpDown)
                            if stateCompare('TCP_TX_RAMPUP', stateVectorRampUpDown[-1]):
                                stateVectorRampUpDown[-1] = "TCP_TX_RAMPUP"
                            # Adding the previous state to temp vectors so that they can be popped
                            temp_stateVector.append(stateVectorRampUpDown[-1])
                            temp_durationVector.append(durationVectorRampUpDown[-1])
                            temp_timeStampVector.append(timeStampVectorRampUpDown[-1])
                            # Popping the last states in the vectors
                            stateVectorRampUpDown.pop()
                            durationVectorRampUpDown.pop()
                            timeStampVectorRampUpDown.pop()
                        else:
                            durationVectorRampUpDown[-1] = durationVectorRampUpDown[-1] - remainingRampUpDuration
                            timeStampVectorRampUpDown.append(timeStampVectorRampUpDown[-1] + durationVectorRampUpDown[-1])
                            stateVectorRampUpDown.append('TCP_TX_RAMPUP')
                            durationVectorRampUpDown.append(remainingRampUpDuration)
                            remainingRampUpDuration = 0     # so that loop ends
                            temp_stateVector.reverse()
                            temp_durationVector.reverse()
                            temp_timeStampVector.reverse()
                            
                            stateVectorRampUpDown.extend(temp_stateVector)
                            durationVectorRampUpDown.extend(temp_durationVector)
                            timeStampVectorRampUpDown.extend(temp_timeStampVector)
                    stateVectorRampUpDown.append('TCP_TX')
                    durationVectorRampUpDown.append(durationVectorModified[ii])
                    timeStampVectorRampUpDown.append(timeStampVectorModified[ii])                            
                    # Ramp Up has been added            
                            
                        

                # Until ACK_802_11_RX is found, set to ON if IDLE
                for tempCounter in range(5):
                    if (stateVectorModified[ii+tempCounter+1] == 'ACK_802_11_RX'):
                        break
                    elif (stateVectorModified[ii+tempCounter+1] == 'IDLE'):
                        stateVectorModified[ii+tempCounter+1] = 'ON'
                        print (f"Changed IDLE to ON after TCP Tx")
                
                # following is required if Buffer current is extra
                if  (enableBufferCurrent):
                    for tempCounter in range(20):  # Look ahead and change all (20) the following IDLE states to SLEEP_BUFFER till TCP_ACK is received. This is required in case of PSM
                        if (stateVectorModified[ii+tempCounter]) == 'TCP_ACK_RX':
                            break
                        if (stateVectorModified[ii+tempCounter] == 'IDLE'  or  stateVectorModified[ii+tempCounter] == 'SLEEP'):
                            stateVectorModified[ii+tempCounter] = 'SLEEP_BUFFER'   
                            # stateVectorModified[ii+tempCounter] = 'ON'    # Use this only for Case 4e   
                            
                        if (stateVectorModified[ii+tempCounter] == 'BCN_RAMPUP'):
                            stateVectorModified[ii+tempCounter] = 'BCN_RAMPUP_BUFFER'
                        if (stateVectorModified[ii+tempCounter] == 'BCN_RAMPDOWN'):
                            stateVectorModified[ii+tempCounter] = 'BCN_RAMPDOWN_BUFFER'

                        
                
            elif (stateVectorModified[ii] == 'ACK_802_11_RX'):  
                # This can be ACK for any packet - so should be handled as general case
                stateVectorRampUpDown.append('ACK_802_11_RX')
                durationVectorRampUpDown.append(durationVectorModified[ii])
                timeStampVectorRampUpDown.append(timeStampVectorModified[ii])

                if (enableStateTransitions):
                    tempNextState = stateVectorModified[ii+1]
                    transitionState = 'None'
                    print(f"next states: {stateVectorModified[ii+1], stateVectorModified[ii+2]}; Duration: {durationVectorModified[ii+1], durationVectorModified[ii+2]}")
                    if (tempNextState == 'SLEEP'):
                        transitionState = 'ACK_802_11_RX_RAMPDOWN'
                    elif (tempNextState == 'SLEEP_BUFFER'):
                        transitionState = 'ACK_802_11_RX_RAMPDOWN_BUFFER'
                    else:
                        print(f"Did not add rampdown after ACK_802_11_RX - next state was {tempNextState} for {durationVectorModified[ii+1]}")
                    
                    
                    if (transitionState != 'None') and (durationVectorModified[ii+1] >= durationDict["ACK_802_11_RX_rampDown"]):
                        addedAlreadyLookAhead = True
                        stateVectorRampUpDown.append(transitionState)
                        durationVectorRampUpDown.append(durationDict["ACK_802_11_RX_rampDown"])
                        timeStampVectorRampUpDown.append(timeStampVectorModified[ii+1])
                        # Adding next idle time after deduction
                        stateVectorRampUpDown.append(tempNextState)
                        durationVectorRampUpDown.append(durationVectorModified[ii+1] - durationDict["ACK_802_11_RX_rampDown"])
                        timeStampVectorRampUpDown.append(timeStampVectorModified[ii+1]+ durationDict["ACK_802_11_RX_rampDown"])
                    elif (transitionState != 'None') and (durationVectorModified[ii+1] < durationDict["ACK_802_11_RX_rampDown"]):
                        stateVectorModified[ii+1] = transitionState
                    else:
                        pass



            # Adding RampDown After 802.11 ACK Tx    
            elif (stateVectorModified[ii] == 'ACK_802_11_TX'):
                stateVectorRampUpDown.append('ACK_802_11_TX')
                durationVectorRampUpDown.append(durationVectorModified[ii])
                timeStampVectorRampUpDown.append(timeStampVectorModified[ii])
                #print("found ack")
                if (stateVectorModified[ii+1] == 'SLEEP' and durationVectorModified[ii+1] >= durationDict["ACK_802_11_TX_rampDown"]):
                    addedAlreadyLookAhead = True
                    stateVectorRampUpDown.append('ACK_802_11_TX_RAMPDOWN')
                    durationVectorRampUpDown.append(durationDict["ACK_802_11_TX_rampDown"])
                    timeStampVectorRampUpDown.append(timeStampVectorModified[ii+1])
                    # Adding next idle time after deduction
                    stateVectorRampUpDown.append('SLEEP')
                    durationVectorRampUpDown.append(durationVectorModified[ii+1] - durationDict["ACK_802_11_TX_rampDown"])
                    timeStampVectorRampUpDown.append(timeStampVectorModified[ii+1]+ durationDict["ACK_802_11_TX_rampDown"])
                elif (stateVectorModified[ii+1] == 'SLEEP' and durationVectorModified[ii+1] < durationDict["ACK_802_11_TX_rampDown"]):   # Available IDLE state is less than needed. Just change the available to ACK_802_11_TX_RAMPDOWN. No lookahead
                    stateVectorModified[ii+1] = 'ACK_802_11_TX_RAMPDOWN'
                    #print(f"Warning at ii: {ii}. TCP RampDown added with less duration\ndurationVectorModified[ii+1] = {durationVectorModified[ii+1]} \n durationDict["ACK_802_11_TX_rampDown"]={durationDict["ACK_802_11_TX_rampDown"]}")
                else:
                    pass
                    print(f"Error at ii: {ii}. Could not add TCP RampDown\ndurationVectorModified[ii+1] = {durationVectorModified[ii+1]} \n durationDict['ACK_802_11_TX_rampDown']={durationDict['ACK_802_11_TX_rampDown']}\nstateVectorModified[ii+1]= {stateVectorModified[ii+1]}")

                    
            else:
                # Just some other state
                stateVectorRampUpDown.append(stateVectorModified[ii])
                durationVectorRampUpDown.append(durationVectorModified[ii])
                timeStampVectorRampUpDown.append(timeStampVectorModified[ii])


    # %%
    # Assigning current values

    totalDuration = int(np.sum(durationVectorRampUpDown))
    #print(totalDuration)
    ampereTimeSeries = np.zeros(totalDuration)
    #print(ampereTimeSeries.shape)
    currentTimePointer = 0
    # print (f"Final stateVectorRampUpDown: {stateVectorRampUpDown}")
    # print (f"Final durationVectorRampUpDown: {durationVectorRampUpDown}")
    for ii in range(len(stateVectorRampUpDown)):
        print (f"State: {stateVectorRampUpDown[ii]}; Duration: {durationVectorRampUpDown[ii]}")
        if stateVectorRampUpDown[ii] in stateDict:
            tempCurrent = stateDict[stateVectorRampUpDown[ii]]
        else:
            print (f" Error at {ii}. Did not find State {stateVectorRampUpDown[ii]} in Dict")
        
        
        #print(durationVector[ii])
        #print(f"{currentTimePointer}, {durationVectorRampUpDown[ii]}")
        ampereTimeSeries[currentTimePointer:currentTimePointer + durationVectorRampUpDown[ii]] = tempCurrent
        #print(ampereTimeSeries[currentTimePointer:durationVector[ii]])
        currentTimePointer = currentTimePointer + durationVectorRampUpDown[ii]


    # %%

    # *****************************************************************

    # Measuring the average current for this time window

    simAvgCurrent = np.sum(ampereTimeSeries[:timeUnits])/timeUnits


    print(f"Average current consumed by simulation: {simAvgCurrent*1000} mA")
    # print(f"Network RTT: {networkRTT_us} us =  {networkRTT_us/1000} ms\nTime to next beacon : {timeToNextBeacon_us} us = {timeToNextBeacon_us/1000} ms ")

    # Appending to RTT, time to next beacon and average current lists in the correct units
    # networkRTT_ms_list.append(networkRTT_us/1000)
    # timeToNextBeacon_ms_list.append(timeToNextBeacon_us/1000)
    averageCurrent_mA_list.append(simAvgCurrent*1000)

    # # Plotting
    timeUnits = milliSecToPlot*1000           
    xAxis = np.arange(0,timeUnits)
    plt.figure(num=None, figsize=(14, 6), dpi=80, facecolor='w', edgecolor='k')
    plt.plot(xAxis/1000,ampereTimeSeries[:timeUnits]*1000, 'b')


    plt.xlabel("Time (ms)")
    plt.ylabel("Current (mA)")
    plt.legend(["ns3"], loc = "upper right")
    # textString = "Scenario A \nNetwork RTT: " + str(networkRTT_us/1000) + " ms\nTime to next beacon: " + str(timeToNextBeacon_us/1000) + " ms\n"
    
    font = {'family': 'serif',
        'color':  'black',
        'weight': 'normal',
        'size': 12,
        }
    # plt.text(2, 190, textString, fontdict = font,
                #  bbox=dict(boxstyle="square",
                #    ec=(0, 0, 0),
                #    fc=(1., 1, 1),
                #    ))
    
    # Master Loop ends here
    # ----------------------------------------------------------------------------------------------------
# os.system('cls||clear')

print(f"\n\n----------------------------------------------------------------\nCompleted processing {logCount} simulations.")
print(f"Network RTT List in ms: {networkRTT_ms_list}")
print(f"Time to next beacon List in ms: {timeToNextBeacon_ms_list}")
print(f"Average current List in mA: {averageCurrent_mA_list}")

# writing to a csv file
# CSV file format
# networkRTT_ms, timeToNextBeacon_ms, averageCurrent_mA

dataFrameToWrite = pd.DataFrame(list(zip(index_list ,networkRTT_ms_list, timeToNextBeacon_ms_list, averageCurrent_mA_list)), columns= ['SimulationID','networkRTT_ms', 'timeToNextBeacon_ms', 'averageCurrent_mA'])
print(dataFrameToWrite)

# dataFrameToWrite.to_csv(csvFileName, index  = False)

# %%
