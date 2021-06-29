# This code is for batch processing ns3 trace and PHY state logs for scenario 4a
# Author : Shyam Krishnan Venkateswaran
# Email: shyam1@gatech.edu
# Variables to take care of before each run will be tagged with #changeThisBeforeRun



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
csvFileName = 'scenario4a10May2021_noDelACK_1.csv'          #changeThisBeforeRun

# Following lists will be appended at the end of each iteration. The lists are ordered and correspond to each other in the correct order.
index_list = [] 
networkRTT_ms_list = []
timeToNextBeacon_ms_list = []
averageCurrent_mA_list = []
delACK = 0      # if delayed ACK was enabled in experiment, set this to 1. Else, 0.         #changeThisBeforeRun
TCP_indexToPick = -2            #changeThisBeforeRun

# Generating list of logs to import
# stateLog files must be named as 'stateLog#####.log', where ##### are 5 numbers 0-9
# asciiTrace files must be named as 'asciiTrace#####.tr', where ##### are 5 numbers 0-9
# The '#####' will be used as IDs to find corresponding log - trace pairs. 

# data_folder = Path("TI_ns3_noDelACK/")
data_folder = Path("TI_ns3_noDelACK_combined/")                                             #changeThisBeforeRun
ns3_sim_log_list_temp = list(data_folder.glob("**/*.log"))
ns3_sim_log_list = [str(x) for x in ns3_sim_log_list_temp]
ns3_ascii_log_list_temp = list(data_folder.glob("**/*.tr"))
ns3_ascii_log_list = [str(x) for x in ns3_ascii_log_list_temp]


ns3_sim_log_list.sort()

ns3_ascii_log_list.sort()
# ns3_sim_log_list = glob.glob("TI_ns3_noDelACK_combined\\*.log")
# ns3_ascii_log_list = glob.glob("TI_ns3_noDelACK_combined\\*.tr")
logCount = len(ns3_sim_log_list)


# For random log selection ------------------------------below - just delete this block for batch processing
chosenLog = randrange(logCount)
# chosenLog = 1
# print(f"Chosen log: {chosenLog}")

ns3_sim_log_list = [ns3_sim_log_list[chosenLog]]
ns3_ascii_log_list = [ns3_ascii_log_list[chosenLog]]
logCount = 1
print(f"Chosen log: {ns3_sim_log_list}")

# For random log selection ------------------------------Above


delACK_list = [delACK]*logCount

print(f"Number of logs to be processed: {logCount}")
# %%
# All configuration parameters, numerical values and adjustments are defined here. 

stateDict = {}                  # This is the master dict storing state names and current values in mA
durationDict = {}               # This dictionary contains the durations for manually added states in us (micro seconds)     
milliSecToPlot = 1024    # This sets how much data will be plotted and compared
timeUnits = milliSecToPlot*1000  
stateLogStartTime_us = 1.7*1e6          # PHY state log will be imported only after this time from start
time_interval_beacon_to_tcp_ack = 3000    # This is in uS. from experiments, when PSM is enabled, on average, the AP sends the TCP ACK 4 ms after the beacon is received in NetGear setup


advanceInTimeNs3_100uS = 0
beaconPreambleDuration_us = 192           #This will be used in cases with early termination


# State Dictionary definition - Current values are in Amperes
stateDict["IDLE"] =  0.12e-3                                        # IDLE state - will be assigned LPDS current after processing
stateDict["ON"] =  66e-3                                            # Used for Always on power modes - value from experiments
stateDict["BCN_RX"] =  45e-3                                        # For Beacon Rx - from datasheet
stateDict["TX"] = 232e-3                                            # This will be referenced in multiple Tx states but not used directly
stateDict["RX_FULL"] = 50e-3                                        # This will be referenced in multiple Rx states but not used directly
stateDict["BCN_RAMPUP"] =  4.5e-3                                   # Ramp up to beacon Rx from LPDS
stateDict["BCN_RAMPDOWN"] =  12.5e-3                                # Ramp down from Beacon Rx to LPDS
stateDict["BCN_RAMPUP_SLEEP"] =  32e-3                              # Ramp up to Beacon Rx from Sleep (10 mA)
stateDict["BCN_RAMPDOWN_SLEEP"] =  12.5e-3                          # Ramp down from Beacon Rx to Sleep (10 mA)
stateDict["BCN_MISS"] =  stateDict["BCN_RX"]                        # For beacon misses - same as beacon Rx
stateDict["BCN_MISS_RAMPUP"] =  4.5e-3                              # Same as BCN_RAMPUP - causality
stateDict["BCN_MISS_RAMPDOWN"] = stateDict["BCN_RX"]                # Beacon miss rampdown is set the Beacon Rx current. Duration is significantly longer. 
stateDict["ACK_802_11_RX"] = stateDict["RX_FULL"]                   # Wi-Fi ACK Rx current
stateDict["ACK_802_11_TX"] =  stateDict["TX"]                       # Set to Tx current
stateDict["UDP_TX"] =  stateDict["TX"]                              # Set to Tx current
stateDict["TCP_TX"] =  stateDict["TX"]                              # Set to Tx current
stateDict["UDP_TX_RAMPUP"] =  28e-3 
stateDict["ACK_802_11_RX_RAMPDOWN"] =  28e-3 
stateDict["TCP_ACK_RX"] = stateDict["RX_FULL"] 
stateDict["TCP_WAIT_ACK"] =  10e-3                                  # Sleep state while waiting for TCP ACK 
stateDict["TCP_TX_RAMPUP"] =  25e-3  
stateDict["TCP_TX_RAMPDOWN"] =  36e-3                               # This will be added after 802.11 ACK Rx
stateDict["TCP_ACK_RX_RAMPDOWN"] =  65e-3  
stateDict["TCP_RAMPUP_SLEEP_TO_TCP_ACK_RX"] =  20e-3  
    

# has to be taken care of ------ Below ****************
# TCP_WAIT_ACK_CURRENT = 50e-3    # Use only for no PSM - Active till TCP ACK
# TCP_WAIT_ACK_CURRENT = IDLE_CURRENT    # Use only for no PSM - LPDS till TCP ACK



# TCP_TX_RAMPDOWN_CURRENT = 28e-3       # Use this only for special case - TCP-Tx-No PSM-- LPDS--TCP ACK Rx
# durationDict["TCP_TX_rampDown"] = 6000        # Use this only for special case - TCP-Tx-No PSM-- LPDS--TCP ACK Rx  


# has to be taken care of ------ Above *********************


 


# Durations ------------------------- in micro seconds

durationDict["UDP_TX_rampUp"]               = 23000
durationDict["UDP_TX_rampDown"]             = 6000
durationDict["BCN_rampUp"]                  = 2600                                              # From LPDS
durationDict["BCN_rampDown"]                = 800                                               # From LPDS
durationDict["BCN_MISS_rampUp"]             = durationDict["BCN_rampUp"] 
durationDict["BCN_MISS_rampDown"]           = 7500
durationDict["BCN_rampUp_fromSleep"]        = durationDict["BCN_rampUp"]
durationDict["BCN_rampDown_toSleep"]        = durationDict["BCN_rampDown"]
durationDict["TCP_TX_rampUp"]               = 23500
durationDict["TCP_TX_rampDown"]             = 5500                                              # This will be added after 802.11 ACK Rx  
durationDict["TCP_ACK_RX_rampDown"]         = 1300
durationDict["TCP_SLEEP_TO_TCP_ACK_RX_rampUp"]        = 5000




enableAlwaysOn = False
useCase = 'TCP'
enable_TCP_PSM = True



# Beacon inflation parameters - this inflation is to match the beacon size in bytes. No other purpose
ns3_beaconSize = 147    # bytes
exp_beaconSize = 217   # bytes
TIM_elementPosition = 73      #in bytes - If earlyTermination is True, then beacon Rx will stop at this byte (TIM_elementPosition + 1 bytes will be received)
enableBeaconInflation = True   # Set it to False if inflation is not required
inflationConstant = exp_beaconSize*1.0/ns3_beaconSize

addPreambleToBeaconRx = True    # if true, the preamble duration will be added at the beginning of beacon Rx
earlyTermination = True
earlyTerminationFactor = 1.0
if earlyTermination:
    earlyTerminationFactor = 1.0*(TIM_elementPosition + 1)/exp_beaconSize
    inflationConstant = inflationConstant*1.0*earlyTerminationFactor


# Beacon misses
enableBeaconMiss = False
beaconMissProbability = 0.2


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
        for line in csv.reader(tsv, delimiter = " "):
            #print(line)
            currentTimeStamp = int(float(line[0])*1e6)
            if (currentTimeStamp < stateLogStartTime_us ):
                continue
            #print(currentTimeStamp)
            currentState = line[4]
            currentState = currentState.split("=")[1]
            currentDuration = line[-1]
            
            currentDuration = currentDuration.split("+",1)[1]
            #print(currentDuration)
            currentDuration = float(currentDuration.split("ns")[0])
            #print(currentDuration)
            #******************************************* approximating to precision of 1 microseconds
            currentDuration = int(currentDuration/1000)
            currentDuration = int(np.ceil(currentDuration))
            #print(f"{currentState}, {currentDuration}")
            if (currentDuration >0.0):
                stateVector.append(currentState)
                durationVector.append(currentDuration)
                timeStampVector.append(currentTimeStamp)
            
    # print(timeStampVector)
    # Importing ASCII trace as a dictionary
    ascii_ns3_traceDict = dict()
    with open(ns3_ascii_log) as file1:
        Lines = file1.readlines() 
        for line in Lines: 
            timeStamp = int(float(line.split(" ")[1])*1e6)
            ascii_ns3_traceDict[timeStamp]= line
            #print(timeStamp)


    #print(json.dumps(ascii_ns3_traceDict, indent=1))   
                        




    # %%
    # Tagging the log File. This is before current values are assigned
    # CCA_BUSY is changed to IDLE
    # If always ON mode is enabled, IDLE is replaced with ON
    # All adjacent but same states are combined
    # TCP, UDP states are identified and assigned


    stateVectorLength = len(stateVector)
    timeStampVectorModified = []
    stateVectorModified = []
    durationVectorModified = []
    for ii in range(stateVectorLength):
        
        # Replacing all CCA_BUSY with IDLE
        if stateVector[ii]== 'CCA_BUSY':
            stateVector[ii] = 'IDLE'
        if stateVector[ii]== 'IDLE' and enableAlwaysOn:
            stateVector[ii] = 'ON'
        # Finding BCN_RX, UDP_TX and 802.11 ACK receptions
        if timeStampVector[ii] in ascii_ns3_traceDict:

            tempASCIItrace = ascii_ns3_traceDict[timeStampVector[ii]]
            #print(f"At time {timeStampVector[ii]}, ASCII trace is \n {tempASCIItrace}")
            if stateVector[ii]== 'RX' and ("RxOk" in tempASCIItrace) and (tempASCIItrace.split(" ")[0]=="r") and ("MGT_BEACON" in tempASCIItrace):  
                stateVector[ii] = "BCN_RX"
            elif stateVector[ii]== 'RX' and ("CTL_ACK" in tempASCIItrace) and (tempASCIItrace.split(" ")[0]=="r") and ("RxOk" in tempASCIItrace):
                stateVector[ii] = 'ACK_802_11_RX'
            elif stateVector[ii]== 'TX' and ("CTL_ACK" in tempASCIItrace) and (tempASCIItrace.split(" ")[0]=="t") and ("Tx" in tempASCIItrace):
                stateVector[ii] = 'ACK_802_11_TX'       
            elif stateVector[ii]== 'TX' and ("UdpHeader" in tempASCIItrace) and (tempASCIItrace.split(" ")[0]=="t"):
                stateVector[ii] = 'UDP_TX'
            elif stateVector[ii]== 'TX' and ("TcpHeader" in tempASCIItrace) and (tempASCIItrace.split(" ")[0]=="t"):
                stateVector[ii] = 'TCP_TX'
                #print(f"TCP Tx found at t = {timeStampVector[ii]}")
            elif stateVector[ii]== 'RX' and ("TcpHeader" in tempASCIItrace) and (tempASCIItrace.split(" ")[0]=="r") and ("RxOk" in tempASCIItrace) and ("[ACK]" in tempASCIItrace):
                stateVector[ii] = 'TCP_ACK_RX'
                #print(f"TCP ACK found at t = {timeStampVector[ii]}")
            elif stateVector[ii] != 'IDLE':
                print(f"State not tagged at ii: {ii}: {stateVector[ii]}")
                print(f"tempASCIItrace:{tempASCIItrace}")



        # To combine adjacent same states  
        if ii == 0:
            #prevState = stateVector[ii]
            stateVectorModified.append(stateVector[ii])
            durationVectorModified.append(durationVector[ii])
            timeStampVectorModified.append(timeStampVector[ii])
        elif (stateVector[ii] == stateVectorModified[-1]):
            durationVectorModified[-1] = durationVectorModified[-1] + durationVector[ii]
        else:
            stateVectorModified.append(stateVector[ii])
            durationVectorModified.append(durationVector[ii])
            timeStampVectorModified.append(timeStampVector[ii])
    durationVectorModified = [int(i) for i in durationVectorModified]


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
    TCPindices = [i for i, xstate in enumerate(stateVectorModified) if xstate == "TCP_TX"]
    chosenTCP_TX_ii = TCPindices[TCP_indexToPick]                           
    chosenTCP_TX_TimeStamp = timeStampVectorModified[chosenTCP_TX_ii]
    chosenTCP_ACK_RX_ii = stateVectorModified.index('TCP_ACK_RX', chosenTCP_TX_ii)
    chosenTCP_ACK_RX_TimeStamp = timeStampVectorModified[chosenTCP_ACK_RX_ii]
    networkRTT_us = chosenTCP_ACK_RX_TimeStamp - chosenTCP_TX_TimeStamp
    nextBeacon_ii = stateVectorModified.index('BCN_RX', chosenTCP_TX_ii)
    nextBeacon_TimeStamp = timeStampVectorModified[nextBeacon_ii]
    timeToNextBeacon_us = nextBeacon_TimeStamp - chosenTCP_TX_TimeStamp
    firstTCP_TX_TimeStamp_inWindow = chosenTCP_TX_TimeStamp - timeStampVectorModified[0]
    # print(f"TCP Tx occurs {(firstTCP_TX_TimeStamp_inWindow)/1e6} seconds from Beginning of the window \nTo have TCP Tx exactly at 0.5 seconds in the window, the ns3 logs must be advanced in time by {firstTCP_TX_TimeStamp_inWindow - 0.5e6} us")


    advanceInTimeNs3_1uS = int(firstTCP_TX_TimeStamp_inWindow - 0.3e6)


    # %%
    # Adding the preamble duration to beacon Rx - can be commented out and code will work

    if addPreambleToBeaconRx:
        
        stateVectorLength = len(stateVectorModified)
        for ii in range(stateVectorLength-1):
            # Look for 'RX' state  
            isBeacon = False    # if it is a beacon reception, this will be True
            if stateVectorModified[ii] == "BCN_RX":
                isBeacon = True
            if isBeacon and (stateVectorModified[ii-1] == 'IDLE' or stateVectorModified[ii-1] == 'ON'):
                oldDuration = durationVectorModified[ii]
                durationVectorModified[ii] = int(durationVectorModified[ii] + beaconPreambleDuration_us )
                
                
                timeDiffAdded = durationVectorModified[ii] - oldDuration
                #if stateVectorModified[ii+1] == 'IDLE' or stateVectorModified[ii+1] == 'ON':
                # Remove the extra Beacon RX time from the next IDLE state if present, else print error/warning
                durationVectorModified[ii-1] = int( durationVectorModified[ii-1] - timeDiffAdded)
                timeStampVectorModified[ii] = int(timeStampVectorModified[ii] - timeDiffAdded)
            else:
                pass
                
                    

    # %%
    # Beacon period inflation to account for differences in beacon size between ns3 simulation and experimental results
    # The script will work if this block is commented out


    if (enableBeaconInflation):
        # print(f"Before beacon duration change: Total duration: {np.sum(durationVectorModified)}")
        # print(f"Beacon duration change factor: {inflationConstant}")
        #print(f"Before inflation: State vector modified: {stateVectorModified[:10]}\nDuration Vector modified: {durationVectorModified[:10]}\nTime stamp Vector modified: {timeStampVectorModified[:10]}")
        
        stateVectorLength = len(stateVectorModified)
        for ii in range(stateVectorLength-1):
            # Look for 'RX' state  
            isBeacon = False    # if it is a beacon reception, this will be True
            if stateVectorModified[ii] == "BCN_RX":
                isBeacon = True
            if isBeacon and (stateVectorModified[ii+1] == 'IDLE' or stateVectorModified[ii+1] == 'ON'):
                oldDuration = durationVectorModified[ii]
                durationVectorModified[ii] = int(( (durationVectorModified[ii] - beaconPreambleDuration_us )* inflationConstant) + beaconPreambleDuration_us)
                
                #print(f"original BCN Rx duration: {oldDuration}\nChanged beacon duration: {durationVectorModified[ii]}")
                
                timeDiffAdded = durationVectorModified[ii] - oldDuration
                #if stateVectorModified[ii+1] == 'IDLE' or stateVectorModified[ii+1] == 'ON':
                # Remove the extra Beacon RX time from the next IDLE state if present, else print error/warning
                durationVectorModified[ii+1] = int( durationVectorModified[ii+1] - timeDiffAdded)
                timeStampVectorModified[ii+1] = int(timeStampVectorModified[ii+1] + timeDiffAdded)
            else:
                pass
                #print(f'Warning: Did not add compensation time while inflating beacon at ii = {ii}')
                    
        # print(f"After beacon duration change: Total duration: {np.sum(durationVectorModified)}")
        # print(f"After beacon duration change: State vector modified: {stateVectorModified[:40]}\nDuration Vector modified: {durationVectorModified[:40]}\nTime stamp Vector modified: {timeStampVectorModified[:40]}")


    # %%
    # Accounting for beacon misses. 

    if (enableBeaconMiss):
        stateVectorLength = len(stateVectorModified)
        for ii in range(stateVectorLength-1):
            if stateVectorModified[ii] == "BCN_RX":
                
                tempState1  = random.choices(population = ['BCN_RX','BCN_MISS'], weights = [1 - beaconMissProbability,beaconMissProbability], k = 1) 
                stateVectorModified[ii] = tempState1[0]
                # print(stateVectorModified[ii])


    # %%
    # Accounting for PSM mode in TCP behavior

    if (enable_TCP_PSM):
        # print(f"Before PSM modification: Total duration: {np.sum(durationVectorModified)}")
        stateVector_old = stateVectorModified * 1
        durationVector_old = durationVectorModified * 1
        timeStampVector_old = timeStampVectorModified * 1
        stateVectorModified = []
        durationVectorModified = []
        timeStampVectorModified = []
        
        totalLen = len(stateVector_old)
        
        ii = 0
        while (True):
            if ii == totalLen:
                break
            if (stateVector_old[ii] == 'TCP_TX'):
                # Adding TCP_TX
                stateVectorModified.append(stateVector_old[ii])
                durationVectorModified.append(durationVector_old[ii])
                timeStampVectorModified.append(timeStampVector_old[ii])            
                ii = ii+1
                
                
                    
                # Adding IDLE states
                while (stateVector_old[ii] == 'IDLE'):
                    stateVectorModified.append(stateVector_old[ii])
                    durationVectorModified.append(durationVector_old[ii])
                    timeStampVectorModified.append(timeStampVector_old[ii])     
                    ii = ii+1
                    
                # Next is ACK_802_11_RX
                if (stateVector_old[ii] == 'ACK_802_11_RX'):
                    stateVectorModified.append(stateVector_old[ii])
                    durationVectorModified.append(durationVector_old[ii])
                    timeStampVectorModified.append(timeStampVector_old[ii])     
                    ii = ii+1
                    
                else:
                    print(f"Error. TCP Tx not followed by 802.11 ACK Rx at ii = {ii}")
    #             for tempCounter in range(8):
    #                 print(stateVector_old[ii-3 +tempCounter ])
                    
                # Adding all following IDLE states
                # while (stateVector_old[ii] == 'IDLE'):
                while (stateVector_old[ii] != 'TCP_ACK_RX'):   # Loop till 'TCP_ACK_RX'
                    stateVectorModified.append(stateVector_old[ii])
                    durationVectorModified.append(durationVector_old[ii])
                    timeStampVectorModified.append(timeStampVector_old[ii])     
                    ii = ii+1            
                
                # Next states should be 'TCP_ACK_RX', 'IDLE', 'ACK_802_11_TX', 'IDLE', 'BCN_RX', 'IDLE'
                if (stateVector_old[ii] == 'TCP_ACK_RX') and (stateVector_old[ii+1] == 'IDLE') and (stateVector_old[ii+2] == 'ACK_802_11_TX'):
                    tcp_ack_duration = durationVector_old[ii]
                    idle_duration = durationVector_old[ii+1]
                    wifi_ack_tx_duration = durationVector_old[ii+2]
                    # Adding these 3 as IDLE states
                    for tempCounter in range(3):
                        stateVectorModified.append('IDLE')
                        durationVectorModified.append(durationVector_old[ii])
                        timeStampVectorModified.append(timeStampVector_old[ii]) 
                        ii = ii + 1
                    
                    # Adding all following IDLE states - if there is a beacon miss, that is also added and skipped
                    while (stateVector_old[ii] == 'IDLE' or stateVector_old[ii] == 'BCN_MISS'):
                        stateVectorModified.append(stateVector_old[ii])
                        durationVectorModified.append(durationVector_old[ii])
                        timeStampVectorModified.append(timeStampVector_old[ii])     
                        ii = ii+1
                    
                    # Next should be BCN_RX
                    if (stateVector_old[ii] == 'BCN_RX'):
                        stateVectorModified.append(stateVector_old[ii])
                        durationVectorModified.append(durationVector_old[ii])
                        timeStampVectorModified.append(timeStampVector_old[ii])     
                        ii = ii+1
                    else:
                        print(f"Beacon not found at ii = {ii}")
                    # Following should be IDLE with duration at least = time_interval_beacon_to_tcp_ack + tcp_ack_duration + idle_duration + wifi_ack_tx_duration
                    requiredDuration = time_interval_beacon_to_tcp_ack + tcp_ack_duration + idle_duration + wifi_ack_tx_duration
                    if (stateVector_old[ii] == 'IDLE') and durationVector_old[ii] > requiredDuration:
                        # Adding intermediate IDLE between beacon and TCP ACK Rx
                        # stateVectorModified.append('IDLE')
                        stateVectorModified.append('ON')
                        durationVectorModified.append(time_interval_beacon_to_tcp_ack)
                        timeStampVectorModified.append(timeStampVector_old[ii]) 
                    
                        # Adding TCP ACK Rx
                        stateVectorModified.append('TCP_ACK_RX')
                        durationVectorModified.append(tcp_ack_duration)
                        timeStampVectorModified.append(timeStampVector_old[ii] + time_interval_beacon_to_tcp_ack)  
                        
                        # Adding IDLE between TCP ACK Rx and 802.11 ACK Tx
                        stateVectorModified.append('IDLE')
                        durationVectorModified.append(idle_duration)
                        timeStampVectorModified.append(timeStampVector_old[ii] + time_interval_beacon_to_tcp_ack + tcp_ack_duration)
                        
                        # Adding 802.11 ACK Tx
                        stateVectorModified.append('ACK_802_11_TX')
                        durationVectorModified.append(wifi_ack_tx_duration)
                        timeStampVectorModified.append(timeStampVector_old[ii] + time_interval_beacon_to_tcp_ack + tcp_ack_duration + idle_duration)
                        
                        # Adding the remaining IDLE duration till next state
                        stateVectorModified.append('IDLE')
                        durationVectorModified.append(durationVector_old[ii] - requiredDuration)
                        timeStampVectorModified.append(timeStampVector_old[ii] + requiredDuration)
                        ii = ii + 1
                    
                        
                    else:
                        print(f"ERROR!! IDLE duration not enough at ii = {ii}")
                        
                        
                
                else:
                    print(f"Error. TCP ACK, IDLE and 802.11 ACK not found perfectly at ii = {ii}")
    #                 for tempCounter in range(8):
    #                     print(stateVector_old[ii-3 +tempCounter ])
                
            else:
                stateVectorModified.append(stateVector_old[ii])
                durationVectorModified.append(durationVector_old[ii])
                timeStampVectorModified.append(timeStampVector_old[ii])
                ii = ii+1
        # print(f"After PSM modification: Total duration: {np.sum(durationVectorModified)}")
        
        # State Consolidation
        # To combine adjacent same states  
        # print(f"Before State Consolidation: Total duration: {np.sum(durationVectorModified)}")
        stateVector_old = stateVectorModified * 1
        durationVector_old = durationVectorModified * 1
        timeStampVector_old = timeStampVectorModified * 1
        stateVectorModified = []
        durationVectorModified = []
        timeStampVectorModified = []
        
        stateVectorLength = len(stateVector_old)

        for jj in range(stateVectorLength):
            if jj == 0:
                #prevState = stateVector[ii]
                stateVectorModified.append(stateVector_old[jj])
                durationVectorModified.append(durationVector_old[jj])
                timeStampVectorModified.append(timeStampVector_old[jj])
            elif (stateVector_old[jj] == stateVectorModified[-1]):
                durationVectorModified[-1] = durationVectorModified[-1] + durationVector_old[jj]
            else:
                stateVectorModified.append(stateVector_old[jj])
                durationVectorModified.append(durationVector_old[jj])
                timeStampVectorModified.append(timeStampVector_old[jj])
        durationVectorModified = [int(i) for i in durationVectorModified]
        #print(f"After State Consolidation: Total duration: {np.sum(durationVectorModified)}")


    # %%
    # Adding Beacon ramp up and down
    # For BCN_RX states, adding Ramp up and Ramp down if IDLE state is available

    # print(f"Before beacon rampUP down: Total duration: {np.sum(durationVectorModified)}")
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
            if (stateVectorRampUpDown[-1] == 'IDLE' and durationVectorRampUpDown[-1] >= durationDict["BCN_rampUp"]):
                durationVectorRampUpDown[-1] = durationVectorRampUpDown[-1] - durationDict["BCN_rampUp"]
                stateVectorRampUpDown.append('BCN_RAMPUP')
                durationVectorRampUpDown.append(durationDict["BCN_rampUp"])
                timeStampVectorRampUpDown.append(timeStampVectorModified[ii] - durationDict["BCN_rampUp"])
            elif (stateVectorRampUpDown[-1] == 'IDLE' and durationVectorRampUpDown[-1] < durationDict["BCN_rampUp"]):
                # insufficient IDLE state. Just  convert what is available
                stateVectorRampUpDown[-1] = 'BCN_RAMPUP'
                
            else:
                pass
                # print(f"Error at ii: {ii}. Could not add beacon RampUp")
            # Adding RX state
            stateVectorRampUpDown.append('BCN_RX')
            durationVectorRampUpDown.append(durationVectorModified[ii])
            timeStampVectorRampUpDown.append(timeStampVectorModified[ii])
            #Look to add BCN_RAMPDOWN
            if (stateVectorModified[ii+1] == 'IDLE' and durationVectorModified[ii+1] >= durationDict["BCN_rampDown"]):
                addedAlreadyLookAhead = True
                stateVectorRampUpDown.append('BCN_RAMPDOWN')
                durationVectorRampUpDown.append(durationDict["BCN_rampDown"])
                timeStampVectorRampUpDown.append(timeStampVectorModified[ii+1])
                # Adding next idle time after deduction
                stateVectorRampUpDown.append('IDLE')
                durationVectorRampUpDown.append(durationVectorModified[ii+1] - durationDict["BCN_rampDown"])
                timeStampVectorRampUpDown.append(timeStampVectorModified[ii+1]+ durationDict["BCN_rampDown"])
            elif (stateVectorModified[ii+1] == 'IDLE' and durationVectorModified[ii+1] < durationDict["BCN_rampDown"]):
                stateVectorModified[ii+1] == 'BCN_RAMPDOWN'

    # Beacon miss rampup and down -----------------------------------------
        elif (stateVectorModified[ii] == 'BCN_MISS'):
            # print('Found beacon miss!!!!!!!!!!!!!')
            
            if (stateVectorRampUpDown[-1] == 'IDLE' and durationVectorRampUpDown[-1] >= durationDict["BCN_MISS_rampUp"]):
                durationVectorRampUpDown[-1] = durationVectorRampUpDown[-1] - durationDict["BCN_MISS_rampUp"]
                stateVectorRampUpDown.append('BCN_MISS_RAMPUP')
                durationVectorRampUpDown.append(durationDict["BCN_MISS_rampUp"])
                timeStampVectorRampUpDown.append(timeStampVectorModified[ii] - durationDict["BCN_MISS_rampUp"])
            elif (stateVectorRampUpDown[-1] == 'IDLE' and durationVectorRampUpDown[-1] < durationDict["BCN_MISS_rampUp"]):
                # insufficient IDLE state. Just  convert what is available
                stateVectorRampUpDown[-1] = 'BCN_MISS_RAMPUP'
                
            else:
                pass
                # print(f"Error at ii: {ii}. Could not add beacon RampUp")
            
            stateVectorRampUpDown.append('BCN_MISS')
            durationVectorRampUpDown.append(durationVectorModified[ii])
            timeStampVectorRampUpDown.append(timeStampVectorModified[ii])
            
            if (stateVectorModified[ii+1] == 'IDLE' and durationVectorModified[ii+1] >= durationDict["BCN_MISS_rampDown"]):
                addedAlreadyLookAhead = True
                stateVectorRampUpDown.append('BCN_MISS_RAMPDOWN')
                durationVectorRampUpDown.append(durationDict["BCN_MISS_rampDown"])
                timeStampVectorRampUpDown.append(timeStampVectorModified[ii+1])
                # Adding next idle time after deduction
                stateVectorRampUpDown.append('IDLE')
                durationVectorRampUpDown.append(durationVectorModified[ii+1] - durationDict["BCN_MISS_rampDown"])
                timeStampVectorRampUpDown.append(timeStampVectorModified[ii+1]+ durationDict["BCN_MISS_rampDown"])
            elif (stateVectorModified[ii+1] == 'IDLE' and durationVectorModified[ii+1] < durationDict["BCN_MISS_rampDown"]):
                stateVectorModified[ii+1] == 'BCN_MISS_RAMPDOWN'      

    # # Beacon miss rampup and down -----------------------------------------            
        else:
            # Just some other state
            stateVectorRampUpDown.append(stateVectorModified[ii])
            durationVectorRampUpDown.append(durationVectorModified[ii])
            timeStampVectorRampUpDown.append(timeStampVectorModified[ii])
        



    # %%
    # For UDP_TX states, adding Ramp up and Ramp down if IDLE state is available
    if useCase =='UDP':
        print("Entered the UDP use Case")
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
            if (ii==0 or ii == stateVectorLength-1) and not(addedAlreadyLookAhead) :
                stateVectorRampUpDown.append(stateVectorModified[ii])
                durationVectorRampUpDown.append(durationVectorModified[ii])
                timeStampVectorRampUpDown.append(timeStampVectorModified[ii])
                continue


            if (stateVectorModified[ii] == 'UDP_TX'):
                print(f"Found UDP_Tx")
                if (stateVectorRampUpDown[-1] == 'IDLE' and durationVectorRampUpDown[-1] >= durationDict["UDP_TX_rampUp"]):
                    durationVectorRampUpDown[-1] = durationVectorRampUpDown[-1] - durationDict["UDP_TX_rampUp"]
                    stateVectorRampUpDown.append('UDP_TX_RAMPUP')
                    durationVectorRampUpDown.append(durationDict["UDP_TX_rampUp"])
                    timeStampVectorRampUpDown.append(timeStampVectorModified[ii] - durationDict["UDP_TX_rampUp"])
                else:
                    #pass
                    print(f"Error at ii: {ii}. Could not add UDP RampUp")
           
        #             for temp11 in range(5):
        #                 print(f"{ii-temp11}: {stateVectorRampUpDown[-1*(temp11+1)]}: {durationVectorRampUpDown[-1*(temp11+1)]}")            
                # Adding RX state
                stateVectorRampUpDown.append('UDP_TX')
                durationVectorRampUpDown.append(durationVectorModified[ii])
                timeStampVectorRampUpDown.append(timeStampVectorModified[ii])
                # If the next state is IDLE, the device is waiting for ACK. IT is put to ON mode
                if (stateVectorModified[ii+1] == 'IDLE'):
                    stateVectorModified[ii+1] = 'ON'

                #Look to add UDP_TX_RAMPDOWN
            if (stateVectorModified[ii] == 'ACK_802_11_RX'):
                stateVectorRampUpDown.append('ACK_802_11_RX')
                durationVectorRampUpDown.append(durationVectorModified[ii])
                timeStampVectorRampUpDown.append(timeStampVectorModified[ii])
                #print("found ack")
                if (stateVectorModified[ii+1] == 'IDLE' and durationVectorModified[ii+1] >= durationDict["UDP_TX_rampDown"] ):
                    addedAlreadyLookAhead = True
                    #print("Added UDP rampdown")
                    stateVectorRampUpDown.append('ACK_802_11_RX_RAMPDOWN')
                    durationVectorRampUpDown.append(durationDict["UDP_TX_rampDown"] )
                    timeStampVectorRampUpDown.append(timeStampVectorModified[ii+1])
                    # Adding next idle time after deduction
                    stateVectorRampUpDown.append('IDLE')
                    durationVectorRampUpDown.append(durationVectorModified[ii+1] - durationDict["UDP_TX_rampDown"] )
                    timeStampVectorRampUpDown.append(timeStampVectorModified[ii+1]+ durationDict["UDP_TX_rampDown"] )


                else:
                    pass
                    print(f"Error at ii: {ii}. Could not add UDP RampDown")



            else:
                # Just some other state
                stateVectorRampUpDown.append(stateVectorModified[ii])
                durationVectorRampUpDown.append(durationVectorModified[ii])
                timeStampVectorRampUpDown.append(timeStampVectorModified[ii])






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
                        
                        
                        
                            
# =============================================================================
#                             
#                 if ( stateCompare('TCP_TX_RAMPUP', stateVectorRampUpDown[-1]) and durationVectorRampUpDown[-1] >= durationDict["TCP_TX_rampUp"]): 
#                     durationVectorRampUpDown[-1] = durationVectorRampUpDown[-1] - durationDict["TCP_TX_rampUp"]
#                     stateVectorRampUpDown.append('TCP_TX_RAMPUP')
#                     durationVectorRampUpDown.append(durationDict["TCP_TX_rampUp"])
#                     timeStampVectorRampUpDown.append(timeStampVectorModified[ii] - durationDict["TCP_TX_rampUp"])
#                 else:
#                     pass
#                     print(f"Error at ii: {ii}. Could not add TCP RampUp")
# 
#                 stateVectorRampUpDown.append('TCP_TX')
#                 durationVectorRampUpDown.append(durationVectorModified[ii])
#                 timeStampVectorRampUpDown.append(timeStampVectorModified[ii])
# =============================================================================
                # Ramp Up has been added
                
                # If the next states are IDLE, the device is waiting for 802.11 ACK. It is put to ON mode
                for tempCounter in range(5):
                    if (stateVectorModified[ii+tempCounter+1] == 'IDLE'):
                        stateVectorModified[ii+tempCounter+1] = 'ON'
                    else:
                        break
                        # As soon as a non-IDLE state is found, it stops looking for IDLE states. It means an 802.11 ACK is found.
                
            elif (stateVectorModified[ii] == 'ACK_802_11_RX'):
                stateVectorRampUpDown.append('ACK_802_11_RX')
                durationVectorRampUpDown.append(durationVectorModified[ii])
                timeStampVectorRampUpDown.append(timeStampVectorModified[ii])
                for tempCounter in range(20):  # Look ahead and change all (20) the following IDLE states to TCP_WAIT_ACK till TCP_ACK is received. This is required in case of PSM
                    if (stateVectorModified[ii+tempCounter]) == 'TCP_ACK_RX':
                        break
                    if (stateVectorModified[ii+tempCounter] == 'IDLE'):
                        stateVectorModified[ii+tempCounter] = 'TCP_WAIT_ACK'   
                        # stateVectorModified[ii+tempCounter] = 'ON'    # Use this only for Case 4e   
                        
                    if (stateVectorModified[ii+tempCounter] == 'BCN_RAMPUP' or stateVectorModified[ii+tempCounter] == 'BCN_MISS_RAMPUP'):
                        stateVectorModified[ii+tempCounter] = 'BCN_RAMPUP_SLEEP'
                    if (stateVectorModified[ii+tempCounter] == 'BCN_RAMPDOWN'):
                        stateVectorModified[ii+tempCounter] = 'BCN_RAMPDOWN_SLEEP'
                # Adding ramp down after 802.11 ACK rx
                tempNextState = stateVectorModified[ii+1]
                if ((tempNextState == 'IDLE' or tempNextState == 'TCP_WAIT_ACK') and durationVectorModified[ii+1] >= durationDict["TCP_TX_rampDown"]):
                    addedAlreadyLookAhead = True
                    #print("Added UDP rampdown")
                    stateVectorRampUpDown.append('TCP_TX_RAMPDOWN')
                    durationVectorRampUpDown.append(durationDict["TCP_TX_rampDown"])
                    timeStampVectorRampUpDown.append(timeStampVectorModified[ii+1])
                    # Adding next idle time after deduction
                    stateVectorRampUpDown.append(tempNextState)
                    durationVectorRampUpDown.append(durationVectorModified[ii+1] - durationDict["TCP_TX_rampDown"])
                    timeStampVectorRampUpDown.append(timeStampVectorModified[ii+1]+ durationDict["TCP_TX_rampDown"])
                elif ((tempNextState == 'IDLE' or tempNextState == 'TCP_WAIT_ACK')  and durationVectorModified[ii+1] < durationDict["TCP_TX_rampDown"]):   # Available IDLE state is less than needed. Just change the available to TCP_ACK_RX_RAMPDOWN. No lookahead
                    stateVectorModified[ii+1] = 'TCP_TX_RAMPDOWN'
                    #print(f"Warning at ii: {ii}. TCP Tx RampDown added with less duration\ndurationVectorModified[ii+1] = {durationVectorModified[ii+1]} \n durationDict["TCP_TX_rampDown"]={durationDict["TCP_TX_rampDown"]}")
                else:
                    pass
                    #print(f"Error at ii: {ii}. Could not add TCP RampDown\ndurationVectorModified[ii+1] = {durationVectorModified[ii+1]} \n durationDict["TCP_TX_rampDown"]={durationDict["TCP_TX_rampDown"]}\nstateVectorModified[ii+1]= {stateVectorModified[ii+1]}")

    # durationDict["TCP_TX_rampDown"]

            # Adding RampDown After 802.11 ACK Tx    
            elif (stateVectorModified[ii] == 'ACK_802_11_TX'):
                stateVectorRampUpDown.append('ACK_802_11_TX')
                durationVectorRampUpDown.append(durationVectorModified[ii])
                timeStampVectorRampUpDown.append(timeStampVectorModified[ii])
                #print("found ack")
                if (stateVectorModified[ii+1] == 'IDLE' and durationVectorModified[ii+1] >= durationDict["TCP_ACK_RX_rampDown"]):
                    addedAlreadyLookAhead = True
                    #print("Added UDP rampdown")
                    stateVectorRampUpDown.append('TCP_ACK_RX_RAMPDOWN')
                    durationVectorRampUpDown.append(durationDict["TCP_ACK_RX_rampDown"])
                    timeStampVectorRampUpDown.append(timeStampVectorModified[ii+1])
                    # Adding next idle time after deduction
                    stateVectorRampUpDown.append('IDLE')
                    durationVectorRampUpDown.append(durationVectorModified[ii+1] - durationDict["TCP_ACK_RX_rampDown"])
                    timeStampVectorRampUpDown.append(timeStampVectorModified[ii+1]+ durationDict["TCP_ACK_RX_rampDown"])
                elif (stateVectorModified[ii+1] == 'IDLE' and durationVectorModified[ii+1] < durationDict["TCP_ACK_RX_rampDown"]):   # Available IDLE state is less than needed. Just change the available to TCP_ACK_RX_RAMPDOWN. No lookahead
                    stateVectorModified[ii+1] = 'TCP_ACK_RX_RAMPDOWN'
                    #print(f"Warning at ii: {ii}. TCP RampDown added with less duration\ndurationVectorModified[ii+1] = {durationVectorModified[ii+1]} \n durationDict["TCP_ACK_RX_rampDown"]={durationDict["TCP_ACK_RX_rampDown"]}")
                else:
                    pass
                    #print(f"Error at ii: {ii}. Could not add TCP RampDown\ndurationVectorModified[ii+1] = {durationVectorModified[ii+1]} \n durationDict["TCP_ACK_RX_rampDown"]={durationDict["TCP_ACK_RX_rampDown"]}\nstateVectorModified[ii+1]= {stateVectorModified[ii+1]}")

            elif (stateVectorModified[ii] == 'TCP_ACK_RX'):
                #print("found ack")
            
                # Adding RampUp
                if (stateVectorRampUpDown[-1] == 'TCP_WAIT_ACK'):
                    if (durationVectorRampUpDown[-1] >= durationDict["TCP_SLEEP_TO_TCP_ACK_RX_rampUp"]): 
                        durationVectorRampUpDown[-1] = durationVectorRampUpDown[-1] - durationDict["TCP_SLEEP_TO_TCP_ACK_RX_rampUp"]
                        stateVectorRampUpDown.append('TCP_RAMPUP_SLEEP_TO_TCP_ACK_RX')
                        durationVectorRampUpDown.append(durationDict["TCP_SLEEP_TO_TCP_ACK_RX_rampUp"])
                        timeStampVectorRampUpDown.append(timeStampVectorModified[ii] - durationDict["TCP_SLEEP_TO_TCP_ACK_RX_rampUp"])
                    else:
                        #print(f"Error at ii: {ii}. not enough time for Ramp up from Sleep to TCP ACK Rx. Added {durationVectorRampUpDown[-1]} us instead of {durationDict["TCP_SLEEP_TO_TCP_ACK_RX_rampUp"]} us.")
                        stateVectorRampUpDown[-1] = 'TCP_RAMPUP_SLEEP_TO_TCP_ACK_RX'
                    

                stateVectorRampUpDown.append('TCP_ACK_RX')
                durationVectorRampUpDown.append(durationVectorModified[ii])
                timeStampVectorRampUpDown.append(timeStampVectorModified[ii])
                if (stateVectorModified[ii+1] == 'IDLE') :  
                    stateVectorModified[ii+1] = 'ON'

                else:
                    pass
                    
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
    for ii in range(len(stateVectorRampUpDown)):
        #print(ii)
        if stateVectorRampUpDown[ii] in stateDict:
            tempCurrent = stateDict[stateVectorRampUpDown[ii]]
        else:
            print (f" Error at {ii}. Did not find State in Dict")
        # yet to account for beacon miss rampup from sleep
        
        #print(durationVector[ii])
        #print(f"{currentTimePointer}, {durationVectorRampUpDown[ii]}")
        ampereTimeSeries[currentTimePointer:currentTimePointer + durationVectorRampUpDown[ii]] = tempCurrent
        #print(ampereTimeSeries[currentTimePointer:durationVector[ii]])
        currentTimePointer = currentTimePointer + durationVectorRampUpDown[ii]


    # %%

    # *****************************************************************

    # Measuring the average current for this time window

    simAvgCurrent = np.sum(ampereTimeSeries[advanceInTimeNs3_1uS:advanceInTimeNs3_1uS+timeUnits])/timeUnits


    print(f"Average current consumed by simulation: {simAvgCurrent*1000} mA")
    print(f"Network RTT: {networkRTT_us} us =  {networkRTT_us/1000} ms\nTime to next beacon : {timeToNextBeacon_us} us = {timeToNextBeacon_us/1000} ms ")

    # Appending to RTT, time to next beacon and average current lists in the correct units
    networkRTT_ms_list.append(networkRTT_us/1000)
    timeToNextBeacon_ms_list.append(timeToNextBeacon_us/1000)
    averageCurrent_mA_list.append(simAvgCurrent*1000)

    # # Plotting
    # timeUnits = milliSecToPlot*1000           
    # xAxis = np.arange(0,timeUnits)
    # plt.figure(num=None, figsize=(14, 6), dpi=80, facecolor='w', edgecolor='k')
    # plt.plot(xAxis/1000,ampereTimeSeries[advanceInTimeNs3_1uS:advanceInTimeNs3_1uS+timeUnits]*1000, 'b')
    # #plt.plot(xAxis/1000, (experimentAmpereSeries[0:timeUnits])*1000, 'r')

    # plt.xlabel("Time (ms)")
    # plt.ylabel("Current (mA)")
    # plt.legend(["ns3"], loc = "upper right")
    # textString = "Scenario A \nNetwork RTT: " + str(networkRTT_us/1000) + " ms\nTime to next beacon: " + str(timeToNextBeacon_us/1000) + " ms\nDelayed ACK timer: " + str(delACK * 200) + " ms"
    
    # font = {'family': 'serif',
    #     'color':  'black',
    #     'weight': 'normal',
    #     'size': 12,
    #     }
    # plt.text(2, 190, textString, fontdict = font,
    #              bbox=dict(boxstyle="square",
    #                ec=(0, 0, 0),
    #                fc=(1., 1, 1),
    #                ))
    
    # Master Loop ends here
    # ----------------------------------------------------------------------------------------------------
# os.system('cls||clear')
print(f"\n\n----------------------------------------------------------------\nCompleted processing {logCount} simulations.")
print(f"Network RTT List in ms: {networkRTT_ms_list}")
print(f"Time to next beacon List in ms: {timeToNextBeacon_ms_list}")
print(f"Average current List in mA: {averageCurrent_mA_list}")

# writing to a csv file
# CSV file format
# networkRTT_ms, timeToNextBeacon_ms, delACK, averageCurrent_mA

dataFrameToWrite = pd.DataFrame(list(zip(index_list ,networkRTT_ms_list, timeToNextBeacon_ms_list, delACK_list, averageCurrent_mA_list)), columns= ['SimulationID','networkRTT_ms', 'timeToNextBeacon_ms', 'delACK', 'averageCurrent_mA'])
print(dataFrameToWrite)

dataFrameToWrite.to_csv(csvFileName, index  = False)
