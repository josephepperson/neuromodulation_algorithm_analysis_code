import sys
import os.path as o
import pandas as pd

import concurrent.futures

import matplotlib.pyplot as plot

sys.path.append(o.abspath(o.join(o.dirname(sys.modules[__name__].__file__), "..")))

from colorama import Fore
from colorama import Style

import numpy as np
import scipy.stats as stats
import time
import math

from mongoengine import *
from RePlayAnalysisCore3.RePlayStudy import RePlayStudy
from RePlayAnalysisCore3.RePlayParticipant import RePlayParticipant

from RePlayAnalysisCore3.VNS.RePlayVNSParameters import RePlayVNSParameters
st = time.time()

font = {'family' : 'normal',
        'weight' : 'normal',
        'size'   : 22}

plot.rc('font', **font)

#Connect to the database
connect(host="")

#Get the study object
study_obj = RePlayStudy.GetStudy()

#Iterate over each participant in the database
all_participants = RePlayParticipant.objects()

#Create lists of exercises and games to ignore and find
exercisesToIgnore = ["ReTrieve", "Clapping","Generic bidirectional movement"]
participantsToFind = ["001-002-00001",
                      "001-002-00002",
                      "001-002-00003",
                      "001-002-00004",
                      "001-002-00006",
                      "001-002-00007",
                      "001-002-00008",
                      "001-002-00009",
                      "001-002-00011",
                      "001-002-00012",
                      "001-002-00013",
                      "001-002-00016",
                      "001-002-00017",
                      "001-002-00018",
                      "001-002-00019",
                      "001-002-00022",
                      "001-002-00027",
                      "001-002-00028",
                      "001-003-00003",
                      "001-003-00004",
                      "001-003-00005",
                      "001-003-00006",
                      "001-003-00007",
                      "001-003-00011",
                      "001-003-00012",
                      "001-003-00015",
                      "001-003-00016",
                      "001-003-00017",
                      "001-003-00018",
                      "001-003-00025",
                      "001-003-00102",
                      "001-003-00104"]

autoEnabled = True
thresholdEnabled = True
manualEnabled = True
periodicEnabled = True
randomEnabled = True
VNS_active = True

if autoEnabled:
    VNS_active = True

def getAlgorithmResultsPerParticipant(participantID):
    
    #Create counters and lists to store data
    auto_header = True
    periodic_header = True
    threshold_header = True

    numberOfManualStims = 0
    numberOfAutoStims = 0
    numberOfThresholdStims = 0
    numberOfPeriodicStims = 0
    numberOfPeriodicContStims = 0
    numberOfRandomStims = 0
    numberOfExercises = 0
    numberOfSessions = 0
    dynamicSettings = [0.35,
                       0.45,
                       0.55,
                       0.65,
                       0.75,
                       0.85,
                       0.95]
    thresholdSettings = [1,
                         2,
                         4,
                         8,
                         16,
                         32,
                         64]
    periodicSettings = [6,
                        6.67,
                        7.5,
                        10,
                        12,
                        15,
                        20]

    #Iterate over each participant
    for participant_index, current_participant in enumerate(all_participants):

        #Check if this participant is in the list of participants to find
        if (current_participant.uid != participantID):
            continue
        
        #Get the visits for this participant
        visits = current_participant.children
        
        #order visits by start time
        visits = sorted(visits, key=lambda x: x.start_time, reverse=False)
        
        #Iterate over each visit
        for visit_index, thisVisit in enumerate(visits):
            
            # skip early visits while prescription was still being developed
            # include only one week (3 visits) of data per participant
            if visit_index < 2:
                continue
            if visit_index > 4:
                continue

            print(thisVisit.start_time)
            
            #Get the activities and start time for this visit
            visitDateTime = thisVisit.start_time
            activities = thisVisit.children
            
            #order activities by start time
            activities = sorted(activities, key=lambda x: x.start_time, reverse=False)

            #Iterate over each activity
            for index, activity in enumerate(activities):
                
                #Try running analysis on this activity
                try:
                                        
                    periodicDateList = []
                    periodicParticipantIDList = []
                    periodicGameNameList = []
                    periodicExerciseNameList = []
                    periodicShiftList = []
                    periodicStimulationRateList = []
                    periodicHistoricalSelectivityList = []
                    periodicLookbackSelectivityList = []
                    periodicSettingList = []
                    periodicTypeList = []
                    periodicStimTotalList = []
                    periodicGameLengthList = []
                    periodicStartTimeList = []

                    autoDateList = []
                    autoParticipantIDList = []
                    autoGameNameList = []
                    autoExerciseNameList = []
                    autoStimulationRateList = []
                    autoHistoricalSelectivityList = []
                    autoLookbackSelectivityList = []
                    autoSettingList = []
                    autoTypeList = []
                    autoStimTotalList = []
                    autoGameLengthList = []
                    autoStartTimeList = []

                    thresholdDateList = []
                    thresholdParticipantIDList = []
                    thresholdGameNameList = []
                    thresholdExerciseNameList = []
                    thresholdStimulationRateList = []
                    thresholdHistoricalSelectivityList = []
                    thresholdLookbackSelectivityList = []
                    thresholdSettingList = []
                    thresholdTypeList = []
                    thresholdStimTotalList = []
                    thresholdGameLengthList = []
                    thresholdStartTimeList = []

                    #Create lists to store data slices
                    auto_stim_signal_list = []

                    auto_stim_VNS_signal_list = []
                    periodic_stim_signal_list = []

                    threshold_stim_signal_list = []
                    threshold_stim_VNS_signal_list = []

                    dynamic_algorithm_signals = []
                    dynamic_algorithm_trigger_timestamps = []

                    print(f"{current_participant.uid} | Participant {Fore.GREEN}{participant_index+1}{Style.RESET_ALL} of {len(all_participants)} | Visit {Fore.RED}{visit_index+1}{Style.RESET_ALL} of {len(visits)} - {visitDateTime} | Activity {Fore.BLUE}{index+1}{Style.RESET_ALL} of {len(activities)}")
    
                    #Print the game name to the console
                    print(activity.GetGameName())

                    if activity.GetGameName() == "Manual Stimulation":
                        continue

                    #Check if this exercise is one to ignore
                    if (activity.GetExerciseName() not in exercisesToIgnore):
                        
                        #Get the game signal and timestamps
                        print(f"{participantID}:Found an exercise to examine: {activity.GetExerciseName()}")
                        # print(f"{participantID}:Getting game signal for activity...")
                        (game_signal_actual, game_signal_timestamps, _, _, _, _) = activity.GetGameSignal(use_real_world_units = True)
                        gain = activity.GetGain()
                        print(f"{participantID}:Done.")

                        # set a reasonable max value to allow
                        maximumValueAllowed = 100000
                        
                        if np.max(np.abs(game_signal_actual)) > maximumValueAllowed:
                            print(f"{participantID}:Found an exercise with a max value greater than {maximumValueAllowed}. Skipping this exercise.\n")
                            continue
                        
                        if index < len(activities) - 1:
                            lastActivity = False
                        else:
                            lastActivity = True

                        if math.isnan(gain):
                            noiseFloor = 0.001
                        else:
                            noiseFloor = 1.5*gain/100

                        for index, parameter in enumerate(dynamicSettings):

                            #Set VNS parameters for signal analysis
                            New_VNS_Parameters = RePlayVNSParameters(Enabled = True, 
                                Minimum_ISI = 5.5, 
                                Desired_ISI = 15, 
                                Selectivity = parameter, 
                                CompensatorySelectivity = float("NaN"), 
                                TyperSharkLookbackSize = 5.0, 
                                LookbackWindow = 5, 
                                SmoothingWindow = 0.3,
                                NoiseFloor = noiseFloor, 
                                TriggerOnPositive = True, 
                                TriggerOnNegative = True, 
                                SelectivityControlledByDesiredISI = False, 
                                Stage1_Smoothing = 1, 
                                Stage2_Smoothing = 0, 
                                Stage1_Operation = 3, 
                                Stage2_Operation = 3, 
                                VNS_AlgorithmParameters_SaveVersion = 0, 
                                LookbackWindowExpirationPolicy = 2, 
                                LookbackWindowCapacity = 3000, 
                                SmoothingKernelSize = 0.084)
                            
                            #Calculate the VNS signal
                            print(f"{participantID}:Getting VNS signal for activity...")
                            vns_signal, _, _, _, vns_trigger_ts = activity.CalculateVNSSignal(custom_parameters = New_VNS_Parameters)
                            
                            print(f"{participantID}:Done.")

                            dynamic_algorithm_signals.append(vns_signal)
                            dynamic_algorithm_trigger_timestamps.append(vns_trigger_ts)
                            
                        #Set parameters for signal analysis
                        #windowSize indicates the number of seconds before and after the stimulation to analyze
                        windowSize = 10
                        startingIndexShift = windowSize*60
                        windowIndexTotal = startingIndexShift*2                       
                        
                        # create a list of indexes that represent a periodic stimulation algorithm where a stimulation takes place every 10 seconds of the game signal

                        if periodicEnabled:
                            
                            if lastActivity:
                                listofzeros = [0] * 18000
                                periodic_vns_signal = vns_signal + listofzeros
                            else:
                                listofzeros = [0] * 3600
                                periodic_vns_signal = vns_signal + listofzeros

                            for index, interval in enumerate(periodicSettings):

                                interval_samples = int(interval*60)
                                
                                for intervalShift in np.arange(0, interval_samples, 120):
                                    current_signal_length = len(periodic_vns_signal)
                                    current_signal_length_sec = current_signal_length/60
                                    #get the number of stimulations that will occur for the current signal
                                    numberOfStims = int(current_signal_length/interval_samples)
                                    #create a list of stimulation times for the current signal
                                    stimulationTimes = []
                                    #create a list of stimulation times for the current VNS signal
                                    stimulationTimesVNS = []
                                    #iterate through the number of stimulations
                                    for k in range(numberOfStims):
                                        #append the stimulation time to the list of stimulation times
                                        stimulationTimes.append(k*interval_samples+intervalShift)
                                        #append the stimulation time to the list of stimulation times
                                        stimulationTimesVNS.append(k*interval_samples+intervalShift)
                                    
                                    print(f"{participantID}:Starting periodic stimulation analysis. There are {len(stimulationTimes)} stimulations in this signal.")
                                    #Iterate over each periodic stim   
                                    for stim in stimulationTimes:
                                        
                                        # ignore stimulations that are within 30 seconds of the start of the signal to ensure plenty of activity is taking place
                                        if stim < 60*30:
                                            print("Stim is too close to the beginning of the signal. Skipping this stimulation.")
                                            continue
                                        stim_index = stim
                                        stim_value = abs(periodic_vns_signal[stim_index])
                                        print(f"{participantID}:Stim at {stim_index} with value {stim_value}")
                                        
                                        #Use the stimulation time to get the signal before and after the stimulation
                                        stim_start_index = stim_index - startingIndexShift
                                        stim_end_index = stim_index + startingIndexShift
                                        if (stim_start_index < 0):
                                            stim_start_index = 0
                                        if (stim_end_index > len(periodic_vns_signal)):
                                            stim_end_index = len(periodic_vns_signal)
                                        stim_signal = periodic_vns_signal[stim_start_index:stim_end_index]

                                        #Check if the signal is the correct length
                                        if(len(stim_signal) != windowIndexTotal):
                                            print(f"{participantID}:Length of signal is not correct!")
                                            continue

                                        #Add the signals to the lists
                                        periodic_stim_signal_list.append(stim_signal)
                                            
                                        periodicParticipantIDList.append(current_participant.uid)
                                        periodicGameNameList.append(activity.GetGameName())
                                        periodicExerciseNameList.append(activity.GetExerciseName())
                                        periodicShiftList.append(intervalShift)
                                        periodicStimulationRateList.append(numberOfStims/(current_signal_length_sec/60))
                                        periodicDateList.append(visitDateTime)
                                        periodicTypeList.append('periodic')
                                        periodicSettingList.append(interval)
                                        periodicStimTotalList.append(numberOfStims)
                                        periodicGameLengthList.append(current_signal_length_sec/60)
                                        periodicStartTimeList.append(activity.start_time)
                                        stimMax = np.max(stim_signal[600-60:600+60])
                                        stimMin = np.min(stim_signal[600-60:600+60])
                                        
                                        # calculate selectivity for the game signal
                                        if stim_index > 3000:
                                            if stim_value >= 0:
                                                vns_signal_positive = periodic_vns_signal[stim_index-3000:stim_index]
                                                vns_signal_positive = np.asarray(vns_signal_positive, dtype = np.float)
                                                vns_signal_positive = vns_signal_positive[vns_signal_positive >= noiseFloor]
                                                if vns_signal_positive.size > 0:
                                                    periodicLookbackSelectivityList.append(stats.percentileofscore(vns_signal_positive,stimMax))
                                                else:
                                                    periodicLookbackSelectivityList.append(0)
                                            else:
                                                vns_signal_negative = periodic_vns_signal[stim_index-3000:stim_index]
                                                vns_signal_negative = np.asarray(vns_signal_negative, dtype = np.float)
                                                vns_signal_negative = vns_signal_negative[vns_signal_negative <= -noiseFloor]
                                                if vns_signal_positive.size > 0:
                                                    periodicLookbackSelectivityList.append(stats.percentileofscore(abs(vns_signal_negative),abs(stimMin)))
                                                else:
                                                    periodicLookbackSelectivityList.append(0)
                                        else:
                                            if stim_value >= 0:
                                                vns_signal_positive = periodic_vns_signal[0:stim_index]
                                                vns_signal_positive = np.asarray(vns_signal_positive, dtype = np.float)
                                                vns_signal_positive = vns_signal_positive[vns_signal_positive >= noiseFloor]
                                                if vns_signal_positive.size > 0:
                                                    periodicLookbackSelectivityList.append(stats.percentileofscore(vns_signal_positive,stimMax))
                                                else:
                                                    periodicLookbackSelectivityList.append(0)
                                            else:
                                                vns_signal_negative = periodic_vns_signal[0:stim_index]
                                                vns_signal_negative = np.asarray(vns_signal_negative, dtype = np.float)
                                                vns_signal_negative = vns_signal_negative[vns_signal_negative <= -noiseFloor]
                                                if vns_signal_positive.size > 0:
                                                    periodicLookbackSelectivityList.append(stats.percentileofscore(abs(vns_signal_negative),abs(stimMin)))
                                                else:
                                                    periodicLookbackSelectivityList.append(0)
                                            
                                        if stim_value >= 0:
                                            periodic_vns_signal = np.asarray(periodic_vns_signal, dtype = np.float)
                                            vns_signal_positive = periodic_vns_signal[periodic_vns_signal >= noiseFloor]
                                            if vns_signal_positive.size > 0:
                                                periodicHistoricalSelectivityList.append(stats.percentileofscore(vns_signal_positive,stimMax))
                                            else:
                                                periodicHistoricalSelectivityList.append(0)
                                        else:
                                            periodic_vns_signal = np.asarray(periodic_vns_signal, dtype = np.float)
                                            vns_signal_negative = periodic_vns_signal[periodic_vns_signal <= -noiseFloor]
                                            if vns_signal_positive.size > 0:
                                                periodicHistoricalSelectivityList.append(stats.percentileofscore(abs(vns_signal_negative),abs(stimMin)))
                                            else:
                                                periodicHistoricalSelectivityList.append(0)
                    
                                        numberOfPeriodicStims = numberOfPeriodicStims + 1
                                
                            # create dataframe to dump list of lists into
                            periodic_stim_signal_list_df = pd.DataFrame()
                            
                            print(f"{participantID}:Writing lists to new columns of periodic stimulation dataframes...")
                            periodic_stim_signal_list_df['start_time'] = periodicStartTimeList
                            periodic_stim_signal_list_df['participant_ID'] = periodicParticipantIDList
                            periodic_stim_signal_list_df['game_name'] = periodicGameNameList
                            periodic_stim_signal_list_df['exercise_name'] = periodicExerciseNameList
                            periodic_stim_signal_list_df['stim_rate'] = periodicStimulationRateList
                            periodic_stim_signal_list_df['hist_sel'] = periodicHistoricalSelectivityList
                            periodic_stim_signal_list_df['selectivity'] = periodicLookbackSelectivityList
                            periodic_stim_signal_list_df['total_stims'] = periodicStimTotalList
                            periodic_stim_signal_list_df['game_length'] = periodicGameLengthList
                            periodic_stim_signal_list_df['date'] = periodicDateList
                            periodic_stim_signal_list_df['shift'] = periodicShiftList
                            periodic_stim_signal_list_df['algo_type'] = periodicTypeList
                            periodic_stim_signal_list_df['algo_setting'] = periodicSettingList
                            
                            # create or append dataframe to csv
                            periodic_stim_signal_list_df.to_csv(f"periodic_game_signal_{participantID}_df.csv", mode = 'a', header = periodic_header)
                            
                            periodic_header = False

                            print(f"\n{participantID}:Finished periodic stimulation analysis for this activity...\n") 

                        if thresholdEnabled:

                            for index, threshold_value in enumerate(thresholdSettings):

                                _, _, _,result_vns_trigger_timestamps,stimValueList = calcStims_FixedThreshold(vns_signal, game_signal_timestamps, noiseFloor, threshold_value)
                                print(f"{participantID}:Starting threshold stimulation analysis. There are {len(stimValueList)} stimulations in this signal.")

                                if len(stimValueList) != 0:

                                    #Iterate over each threshold stimulation    
                                    for stim in result_vns_trigger_timestamps:
                                        
                                        #Get the stimulation time, index, and value
                                        stim_time = stim
                                        stim_index = np.argmin(np.abs(np.asarray(game_signal_timestamps) - stim_time))
                                        
                                        if stim_index < 60*30:
                                            print("Stim is too close to the beginning of the signal. Skipping this stimulation.")
                                            continue
                                        
                                        stim_value = vns_signal[stim_index]
                                        print(f"{participantID}:Stim at {stim_time} with value {stim_value}")
                                        
                                        #Use the stimulation time to get the signal before and after the stimulation
                                        stim_start_index = stim_index - startingIndexShift
                                        stim_end_index = stim_index + startingIndexShift
                                        if (stim_start_index < 0):
                                            stim_start_index = 0
                                        if (stim_end_index > len(vns_signal)):
                                            stim_end_index = len(vns_signal)
                                        stim_signal = vns_signal[stim_start_index:stim_end_index]
                                        stim_VNS_signal = vns_signal[stim_start_index:stim_end_index]
                                        
                                        #Check if the signal is the correct length and within the maximum value allowed
                                        if(len(stim_signal) != windowIndexTotal):
                                            print(f"{participantID}:Length of signal is not correct!")
                                            continue
                                        
                                        #Add the signals to the lists
                                        threshold_stim_signal_list.append(stim_signal)
                                        threshold_stim_VNS_signal_list.append(stim_VNS_signal)
                                        thresholdParticipantIDList.append(current_participant.uid)
                                        thresholdGameNameList.append(activity.GetGameName())
                                        thresholdExerciseNameList.append(activity.GetExerciseName())
                                        thresholdStimulationRateList.append(len(result_vns_trigger_timestamps)/(activity.duration/60)) 
                                        thresholdDateList.append(visitDateTime)
                                        thresholdTypeList.append('threshold')
                                        thresholdSettingList.append(threshold_value)
                                        thresholdStimTotalList.append(len(stimValueList))
                                        thresholdGameLengthList.append(activity.duration/60)
                                        thresholdStartTimeList.append(activity.start_time)
                                        stimMax = np.max(stim_signal[600-60:600+60])
                                        stimMin = np.min(stim_signal[600-60:600+60])
                                        
                                        if stim_index > 3000:
                                            if stim_value >= 0:
                                                vns_signal_positive = vns_signal[stim_index-3000:stim_index]
                                                vns_signal_positive = np.asarray(vns_signal_positive, dtype = np.float)
                                                vns_signal_positive = vns_signal_positive[vns_signal_positive >= noiseFloor]
                                                thresholdLookbackSelectivityList.append(stats.percentileofscore(vns_signal_positive,stimMax))
                                            else:
                                                vns_signal_negative = vns_signal[stim_index-3000:stim_index]
                                                vns_signal_negative = np.asarray(vns_signal_negative, dtype = np.float)
                                                vns_signal_negative = vns_signal_negative[vns_signal_negative <= -noiseFloor]
                                                thresholdLookbackSelectivityList.append(stats.percentileofscore(abs(vns_signal_negative),abs(stimMin)))
                                        else:
                                            if stim_value >= 0:
                                                vns_signal_positive = vns_signal[0:stim_index]
                                                vns_signal_positive = np.asarray(vns_signal_positive, dtype = np.float)
                                                vns_signal_positive = vns_signal_positive[vns_signal_positive >= noiseFloor]
                                                thresholdLookbackSelectivityList.append(stats.percentileofscore(vns_signal_positive,stimMax))
                                            else:
                                                vns_signal_negative = vns_signal[0:stim_index]
                                                vns_signal_negative = np.asarray(vns_signal_negative, dtype = np.float)
                                                vns_signal_negative = vns_signal_negative[vns_signal_negative <= -noiseFloor]
                                                thresholdLookbackSelectivityList.append(stats.percentileofscore(abs(vns_signal_negative),abs(stimMin)))
                                            
                                        if stim_value >= 0:
                                            vns_signal = np.asarray(vns_signal, dtype = np.float)
                                            vns_signal_positive = vns_signal[vns_signal >= noiseFloor]
                                            thresholdHistoricalSelectivityList.append(stats.percentileofscore(vns_signal_positive,stimMax))
                                        else:
                                            vns_signal = np.asarray(vns_signal, dtype = np.float)
                                            vns_signal_negative = vns_signal[vns_signal <= -noiseFloor]
                                            thresholdHistoricalSelectivityList.append(stats.percentileofscore(abs(vns_signal_negative),abs(stimMin)))

                                        numberOfThresholdStims = numberOfThresholdStims + 1
                                        # thresholdStimRate.append(len(vns_trigger_ts)/(activity.duration/60))
                                else:
                                    #If no stims reached the threshold ... 
                                    thresholdStartTimeList.append(activity.start_time)
                                    thresholdParticipantIDList.append(current_participant.uid)
                                    thresholdGameNameList.append(activity.GetGameName())
                                    thresholdExerciseNameList.append(activity.GetExerciseName())
                                    thresholdStimulationRateList.append(0) 
                                    thresholdHistoricalSelectivityList.append(0)
                                    thresholdLookbackSelectivityList.append(0)
                                    thresholdStimTotalList.append(0)
                                    thresholdGameLengthList.append(activity.duration/60)
                                    thresholdDateList.append(visitDateTime)
                                    thresholdTypeList.append('threshold')
                                    thresholdSettingList.append(threshold_value)

                            threshold_stim_signal_list_df = pd.DataFrame()
                            
                            print(f"{participantID}:Writing lists to new columns of algorithm dataframes...")
                            threshold_stim_signal_list_df['start_time'] = thresholdStartTimeList
                            threshold_stim_signal_list_df['participant_ID'] = thresholdParticipantIDList
                            threshold_stim_signal_list_df['game_name'] = thresholdGameNameList
                            threshold_stim_signal_list_df['exercise_name'] = thresholdExerciseNameList
                            threshold_stim_signal_list_df['stim_rate'] = thresholdStimulationRateList
                            threshold_stim_signal_list_df['hist_sel'] = thresholdHistoricalSelectivityList
                            threshold_stim_signal_list_df['selectivity'] = thresholdLookbackSelectivityList
                            threshold_stim_signal_list_df['total_stims'] = thresholdStimTotalList
                            threshold_stim_signal_list_df['game_length'] = thresholdGameLengthList
                            threshold_stim_signal_list_df['date'] = thresholdDateList
                            threshold_stim_signal_list_df['algo_type'] = thresholdTypeList
                            threshold_stim_signal_list_df['algo_setting'] = thresholdSettingList
                            
                            threshold_stim_signal_list_df.to_csv(f"threshold_game_signal_{participantID}_df.csv", mode='a', header=threshold_header) 
                            
                            threshold_header = False

                            print(f"\n{participantID}:Finished algorithm stimulation analysis for this activity\n")

                        if autoEnabled:

                            for index, full_VNS_signal in enumerate(dynamic_algorithm_signals):

                                print(f"{participantID}:Starting automatic stimulation analysis. There are {len(vns_trigger_ts)} stimulations in this signal.")
                                #Iterate over each automatic stimulation    
                                for stim in dynamic_algorithm_trigger_timestamps[index]:
                                    
                                    #Get the stimulation time, index, and value
                                    stim_time = stim
                                    stim_index = np.argmin(np.abs(np.asarray(game_signal_timestamps) - stim_time))
                                    
                                    if stim_index < 60*30:
                                        print("Stim is too close to the beginning of the signal. Skipping this stimulation.")
                                        continue
                                    
                                    stim_value = full_VNS_signal[stim_index]
                                    print(f"{participantID}:Stim at {stim_time} with value {stim_value}")
                                    
                                    #Use the stimulation time to get the signal before and after the stimulation
                                    stim_start_index = stim_index - startingIndexShift
                                    stim_end_index = stim_index + startingIndexShift
                                    if (stim_start_index < 0):
                                        stim_start_index = 0
                                    if (stim_end_index > len(full_VNS_signal)):
                                        stim_end_index = len(full_VNS_signal)
                                    stim_signal = full_VNS_signal[stim_start_index:stim_end_index]
                                    stim_VNS_signal = full_VNS_signal[stim_start_index:stim_end_index]
                                    
                                    #Check if the signal is the correct length and within the maximum value allowed
                                    if(len(stim_signal) != windowIndexTotal):
                                        print(f"{participantID}:Length of signal is not correct!")
                                        continue
                                    
                                    #Add the signals to the lists
                                    auto_stim_signal_list.append(stim_signal)
                                    auto_stim_VNS_signal_list.append(stim_VNS_signal)
                                    autoParticipantIDList.append(current_participant.uid)
                                    autoGameNameList.append(activity.GetGameName())
                                    autoExerciseNameList.append(activity.GetExerciseName())
                                    autoStimulationRateList.append(len(dynamic_algorithm_trigger_timestamps[index])/(activity.duration/60)) 
                                    autoDateList.append(visitDateTime)
                                    autoTypeList.append('dynamic')
                                    autoSettingList.append(dynamicSettings[index])
                                    autoStimTotalList.append(len(vns_trigger_ts))
                                    autoGameLengthList.append(activity.duration/60)
                                    autoStartTimeList.append(activity.start_time)
                                    stimMax = np.max(stim_signal[600-60:600+60])
                                    stimMin = np.min(stim_signal[600-60:600+60])
                                    
                                    if stim_index > 3000:
                                        if stim_value >= 0:
                                            vns_signal_positive = full_VNS_signal[stim_index-3000:stim_index]
                                            vns_signal_positive = np.asarray(vns_signal_positive, dtype = np.float)
                                            vns_signal_positive = vns_signal_positive[vns_signal_positive >= noiseFloor]
                                            autoLookbackSelectivityList.append(stats.percentileofscore(vns_signal_positive,stimMax))
                                        else:
                                            vns_signal_negative = full_VNS_signal[stim_index-3000:stim_index]
                                            vns_signal_negative = np.asarray(vns_signal_negative, dtype = np.float)
                                            vns_signal_negative = vns_signal_negative[vns_signal_negative <= -noiseFloor]
                                            autoLookbackSelectivityList.append(stats.percentileofscore(abs(vns_signal_negative),abs(stimMin)))
                                    else:
                                        if stim_value >= 0:
                                            vns_signal_positive = full_VNS_signal[0:stim_index]
                                            vns_signal_positive = np.asarray(vns_signal_positive, dtype = np.float)
                                            vns_signal_positive = vns_signal_positive[vns_signal_positive >= noiseFloor]
                                            autoLookbackSelectivityList.append(stats.percentileofscore(vns_signal_positive,stimMax))
                                        else:
                                            vns_signal_negative = full_VNS_signal[0:stim_index]
                                            vns_signal_negative = np.asarray(vns_signal_negative, dtype = np.float)
                                            vns_signal_negative = vns_signal_negative[vns_signal_negative <= -noiseFloor]
                                            autoLookbackSelectivityList.append(stats.percentileofscore(abs(vns_signal_negative),abs(stimMin)))
                                        
                                    if stim_value >= 0:
                                        full_VNS_signal = np.asarray(full_VNS_signal, dtype = np.float)
                                        vns_signal_positive = full_VNS_signal[full_VNS_signal >= noiseFloor]
                                        autoHistoricalSelectivityList.append(stats.percentileofscore(vns_signal_positive,stimMax))
                                    else:
                                        full_VNS_signal = np.asarray(full_VNS_signal, dtype = np.float)
                                        vns_signal_negative = full_VNS_signal[full_VNS_signal <= -noiseFloor]
                                        autoHistoricalSelectivityList.append(stats.percentileofscore(abs(vns_signal_negative),abs(stimMin)))

                                    numberOfAutoStims = numberOfAutoStims + 1
                                    # autoStimRate.append(len(vns_trigger_ts)/(activity.duration/60))
                                
                            auto_stim_signal_list_df = pd.DataFrame()
                            
                            print(f"{participantID}:Writing lists to new columns of algorithm dataframes...")
                            auto_stim_signal_list_df['start_time'] = autoStartTimeList
                            auto_stim_signal_list_df['participant_ID'] = autoParticipantIDList
                            auto_stim_signal_list_df['game_name'] = autoGameNameList
                            auto_stim_signal_list_df['exercise_name'] = autoExerciseNameList
                            auto_stim_signal_list_df['stim_rate'] = autoStimulationRateList
                            auto_stim_signal_list_df['hist_sel'] = autoHistoricalSelectivityList
                            auto_stim_signal_list_df['selectivity'] = autoLookbackSelectivityList
                            auto_stim_signal_list_df['total_stims'] = autoStimTotalList
                            auto_stim_signal_list_df['game_length'] = autoGameLengthList
                            auto_stim_signal_list_df['date'] = autoDateList
                            auto_stim_signal_list_df['algo_type'] = autoTypeList
                            auto_stim_signal_list_df['algo_setting'] = autoSettingList
                            
                            auto_stim_signal_list_df.to_csv(f"auto_game_signal_{participantID}_df.csv", mode='a', header=auto_header) 
                            
                            auto_header = False

                            print(f"\n{participantID}:Finished algorithm stimulation analysis for this activity\n")
                
                    else:
                        print(f"{participantID}:This is not an approved activity. Continuing...\n")
                        continue    
                        
                    numberOfExercises = numberOfExercises + 1
                
                #Log any errors that occur during the processing of the activities        
                except Exception as Argument:

                    print(Argument)
                    
                    # creating/opening a file
                    f = open("errorlog.txt", "a")
                
                    # writing in the file
                    f.write(str(Argument) + "\n\n")
                    
                    # closing the file
                    f.close()
                    print(f"\n{participantID}:####### Something went wrong during single activity analysis. Continuing... ########\n")
                    continue  

            numberOfSessions = numberOfSessions + 1

    if manualEnabled:
        print(f"\n{participantID}:Total Manual Stimulations: {numberOfManualStims}")
    if autoEnabled:
        print(f"\n{participantID}:Total Automatic Stimulations: {numberOfAutoStims}")
    if thresholdEnabled:
        print(f"\n{participantID}:Total Automatic Stimulations: {numberOfThresholdStims}")
    if periodicEnabled:
        print(f"\n{participantID}:Total Periodic Stimulations: {numberOfPeriodicStims}")
        
    print(f"\n{participantID}:Total Persistent Periodic Stimulations: {numberOfPeriodicContStims}")
    if randomEnabled:
        print(f"\n{participantID}:Total Persistent Random Stimulations: {numberOfRandomStims}")

    et = time.time()
    elapsed = (et - st)/60
    print(f"{participantID}:Elapsed time: {elapsed}")

# Create a fixed threshold that must be passed for stim

def calcStims_FixedThreshold(vns_signal, game_timestamps, noisefloor = None, static_threshold = 1):

    #Create some variables to store the results of this function
    result_vns_trigger_idx = []
    result_vns_trigger_timestamps = []

    result_positive_threshold = []
    result_negative_threshold = []
    
    stimValueList=[]

    #Get the noise threshold for the current exercise
    noise_floor = noisefloor
    last_trigger_time = None
        
    #Now iterate over the signal and determine when stimulation triggers should occur
    for idx, current_value in enumerate(vns_signal):

        #Take a slice of the array from that point until the current point
        entireSignal = np.asarray(vns_signal, dtype = np.float)

        #Separate the positive and negative sides of the signal
        positive_movements = entireSignal[entireSignal > noise_floor]
        negative_movements = entireSignal[entireSignal < -noise_floor]
        
        #Add these new thresholds to the result arrays
        result_positive_threshold.append(noise_floor*static_threshold)
        result_negative_threshold.append(-noise_floor*static_threshold)

        #Check to see if either the positive or negative threshold has been exceeded
        trigger_vns = False
        if (current_value >= noise_floor*static_threshold) and (len(positive_movements) > 120):
            trigger_vns = True
        elif (current_value <= -noise_floor*static_threshold) and (len(negative_movements) > 120):
            trigger_vns = True
        
        #Now, if we are attempting to trigger VNS, let's make sure the timeout has expired
        current_time = game_timestamps[idx]
        elapsed_time_since_last_trigger = 0
        if last_trigger_time is not None:
            elapsed_time_since_last_trigger = current_time - last_trigger_time
        
        #If the timeout has indeed expired, and if we should trigger, then mark this time as a VNS trigger
        if ((not last_trigger_time) or 
            (elapsed_time_since_last_trigger >= 5.5)):

            if (trigger_vns):
                last_trigger_time = current_time
                result_vns_trigger_idx.append(idx)
                result_vns_trigger_timestamps.append(current_time)
                stimValueList.append(current_value)

    return (result_positive_threshold, result_negative_threshold, result_vns_trigger_idx,result_vns_trigger_timestamps,stimValueList)
    
def main():
    with concurrent.futures.ProcessPoolExecutor() as executor:
        executor.map(getAlgorithmResultsPerParticipant, participantsToFind)
        executor.shutdown(wait=True)
        
    print("Done! Disconnecting from database...")
    disconnect()

if __name__ == '__main__':
    main()