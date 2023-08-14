import sys
import os.path as o
import pandas as pd

import concurrent.futures

import matplotlib.pyplot as plot

sys.path.append(o.abspath(o.join(o.dirname(sys.modules[__name__].__file__), "..")))

from colorama import Fore
from colorama import Style

import numpy as np
from scipy.signal import find_peaks
import scipy.stats as stats
import time
from datetime import datetime
import math

from mongoengine import *
from datetime import timedelta
from datetime import datetime
from RePlayAnalysisCore3.RePlayStudy import RePlayStudy
from RePlayAnalysisCore3.RePlayParticipant import RePlayParticipant
from RePlayAnalysisCore3.VNS.RePlayVNSParameters import RePlayVNSParameters
from PS_2023_TriggeringPaper import config
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
exercisesToIgnore = ["Typing (left handed words)", "Typing (right handed words)", "Typing", "ReTrieve", "Clapping","Generic bidirectional movement"]
participantsToFind = ["001-002-00001","001-002-00002","001-002-00003","001-002-00004"]

autoEnabled = True
manualEnabled = True
periodicEnabled = True
randomEnabled = True
VNS_active = True

if autoEnabled:
    VNS_active = True

def getAlgorithmResultsPerParticipant(participantID):
    
    #Create counters and lists to store data
    aheader = True
    pheader = True
    rheader = True
    mheader = True
    numberOfManualStims = 0
    numberOfAutoStims = 0
    numberOfPeriodicStims = 0
    numberOfPeriodicContStims = 0
    numberOfRandomStims = 0
    numberOfExercises = 0
    numberOfSessions = 0

    #Iterate over each participant
    for participant_index, current_participant in enumerate(all_participants):

        #Check if this participant is in the list of participants to find
        if (current_participant.uid != participantID):
            continue
        
        #Get the visits for this participant
        visits = current_participant.children
        
        #Iterate over each visit
        for visit_index, thisVisit in enumerate(visits):
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

                    manualDateList = []
                    manualParticipantIDList = []
                    manualGameNameList = []
                    manualExerciseNameList = []
                    manualStimulationRateList = []
                    manualHistoricalSelectivityList = []
                    manualLookbackSelectivityList = []

                    autoDateList = []
                    autoParticipantIDList = []
                    autoGameNameList = []
                    autoExerciseNameList = []
                    autoStimulationRateList = []
                    autoHistoricalSelectivityList = []
                    autoLookbackSelectivityList = []

                    randomDateList = []
                    randomParticipantIDList = []
                    randomGameNameList = []
                    randomExerciseNameList = []
                    randomStimulationRateList = []
                    randomHistoricalSelectivityList = []
                    randomLookbackSelectivityList = []

                    #Create lists to store data slices
                    auto_stim_signal_list = []
                    manual_stim_signal_list = []
                    manual_stim_VNS_signal_list = []
                    auto_stim_VNS_signal_list = []
                    periodic_stim_signal_list = []
                    periodic_stim_VNS_signal_list = []
                    random_stim_signal_list = []
                    random_stim_VNS_signal_list = []

                    print(f"{current_participant.uid} | Participant {Fore.GREEN}{participant_index+1}{Style.RESET_ALL} of {len(all_participants)} | Visit {Fore.RED}{visit_index+1}{Style.RESET_ALL} of {len(visits)} - {visitDateTime} | Activity {Fore.BLUE}{index+1}{Style.RESET_ALL} of {len(activities)}")
    
                    #Print the game name to the console
                    print(activity.GetGameName())
                    
                    #Check if this exercise is one to ignore
                    if (activity.GetExerciseName() not in exercisesToIgnore):
                        
                        #Get the stimulation times for this activity 
                        daysFromStart = visitDateTime - datetime(2021,5,12)
                        adjustment =  (0.7947565709556785 *daysFromStart.days)
                        print(f'{participantID}:Adjustment = {adjustment} seconds')
                        stims_for_current_activity = activity.GetShiftedStimulationsFromReStoreDatalogs(shift = adjustment)
                        stims_for_current_activity = [stim - timedelta(seconds=adjustment) for stim in stims_for_current_activity]
                        #Check if there are any stimulations for this activity
                        if (len(stims_for_current_activity) == 0):
                            print(f"{participantID}:Found an exercise with no stimulations. Skipping this exercise.\n")
                            continue
                        
                        #Get the game signal and timestamps
                        activityName = activity.GetExerciseName()
                        print(f"{participantID}:Found an exercise to examine: {activity.GetExerciseName()}")
                        id = current_participant.uid
                        print(f"{participantID}:Getting game signal for activity...")
                        (game_signal_actual, game_signal_timestamps, game_signal_units_str, min_x, max_x, basis_time) = activity.GetGameSignal(use_real_world_units = True)
                        gain = activity.GetGain()
                        print(f"{participantID}:Done.")
                                                
                        if index < len(activities) - 1:
                            lastActivity = False
                        else:
                            lastActivity = True

                        if math.isnan(gain):
                            noiseFloor = 0.001
                        else:
                            noiseFloor = 1.5*gain/100

                        if VNS_active:
                            #Set VNS parameters for signal analysis
                            New_VNS_Parameters = RePlayVNSParameters(Enabled = True, 
                                Minimum_ISI = 5.5, 
                                Desired_ISI = 15, 
                                Selectivity = 0.95, 
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
                            first_device_sample_time = activity.GetSignalStartTime()
                            print(f"{participantID}:Done.")
                            
                            vns_signal = np.abs(vns_signal)
                            
                        game_signal_actual = np.abs(game_signal_actual)    
                        
                        #Set parameters for signal analysis
                        #windowSize indicates the number of seconds before and after the stimulation to analyze
                        windowSize = 20
                        startingIndexShift = windowSize*60
                        windowIndexTotal = startingIndexShift*2                       
                        
                        # create a list of indexes that represent a periodic stimulation algorithm where a stimulation takes place every 10 seconds of the game signal
                        
                        if periodicEnabled:
                            
                            if lastActivity:
                                periodic_game_signal = np.pad(game_signal_actual, (0,18000),'constant')
                                periodic_vns_signal = np.pad(vns_signal, (0,18000),'constant')
                            else:
                                periodic_game_signal = np.pad(game_signal_actual, (0,3600),'constant')
                                periodic_vns_signal = np.pad(vns_signal, (0,3600),'constant')

                            for intervalShift in np.arange(0, 600, 120):
                                current_signal_length = len(periodic_game_signal)
                                #get the number of stimulations that will occur for the current signal
                                numberOfStims = int(current_signal_length/600)
                                #create a list of stimulation times for the current signal
                                stimulationTimes = []
                                #create a list of stimulation times for the current VNS signal
                                stimulationTimesVNS = []
                                #iterate through the number of stimulations
                                for k in range(numberOfStims):
                                    if k < 1:
                                        continue
                                    #append the stimulation time to the list of stimulation times
                                    stimulationTimes.append(k*600+intervalShift)
                                    #append the stimulation time to the list of stimulation times
                                    stimulationTimesVNS.append(k*600+intervalShift)
                                
                                print(f"{participantID}:Starting periodic stimulation analysis. There are {len(stimulationTimes)} stimulations in this signal.")
                                #Iterate over each periodic stim   
                                for stim in stimulationTimes:
                                    
                                    # ignore stimulations that are within 30 seconds of the start of the signal to ensure plenty of activity is taking place
                                    if stim < 60*30:
                                        print("Stim is too close to the beginning of the signal. Skipping this stimulation.")
                                        continue
                                    stim_index = stim
                                    stim_value = abs(periodic_game_signal[stim_index])
                                    print(f"{participantID}:Stim at {stim_index} with value {stim_value}")
                                    
                                    #Use the stimulation time to get the signal before and after the stimulation
                                    stim_start_index = stim_index - startingIndexShift
                                    stim_end_index = stim_index + startingIndexShift
                                    if (stim_start_index < 0):
                                        stim_start_index = 0
                                    if (stim_end_index > len(periodic_game_signal)):
                                        stim_end_index = len(periodic_game_signal)
                                    stim_signal = np.abs(periodic_game_signal[stim_start_index:stim_end_index])
                                    if VNS_active:
                                        stim_VNS_signal = np.abs(periodic_vns_signal[stim_start_index:stim_end_index])

                                    #Check if the signal is the correct length
                                    if(len(stim_signal) != windowIndexTotal):
                                        print(f"{participantID}:Length of signal is not correct!")
                                        continue

                                    #Add the signals to the lists
                                    periodic_stim_signal_list.append(stim_signal)
                                    if VNS_active:
                                        periodic_stim_VNS_signal_list.append(stim_VNS_signal)
                                        
                                    periodicParticipantIDList.append(current_participant.uid)
                                    periodicGameNameList.append(activity.GetGameName())
                                    periodicExerciseNameList.append(activity.GetExerciseName())
                                    periodicShiftList.append(intervalShift)
                                    periodicStimulationRateList.append(numberOfStims/(activity.duration/60))
                                    periodicDateList.append(visitDateTime)
                                    stimMax = np.max(stim_signal[600-60:600+60])
                                    
                                    # calculate selectivity for the game signal
                                    if stim_index > 3000:
                                        periodicLookbackSelectivityList.append(stats.percentileofscore(periodic_game_signal[stim_index-3000:stim_index],stimMax))
                                    else:
                                        periodicLookbackSelectivityList.append(stats.percentileofscore(periodic_game_signal[0:stim_index],stimMax))
                                    periodicHistoricalSelectivityList.append(stats.percentileofscore(periodic_game_signal,stimMax))                       
                                    numberOfPeriodicStims = numberOfPeriodicStims + 1
                            
                            # create dataframe to dump list of lists into
                            periodic_stim_signal_list_df = pd.DataFrame(periodic_stim_signal_list)
                            if VNS_active:
                                periodic_stim_VNS_signal_list_df = pd.DataFrame(periodic_stim_VNS_signal_list)  
                                    
                            print(f"{participantID}:Writing lists to new columns of periodic stimulation dataframes...")
                            periodic_stim_signal_list_df['participant_ID'] = periodicParticipantIDList
                            periodic_stim_signal_list_df['game_name'] = periodicGameNameList
                            periodic_stim_signal_list_df['exercise_name'] = periodicExerciseNameList
                            periodic_stim_signal_list_df['stim_rate'] = periodicStimulationRateList
                            periodic_stim_signal_list_df['hist_sel'] = periodicHistoricalSelectivityList
                            periodic_stim_signal_list_df['selectivity'] = periodicLookbackSelectivityList
                            periodic_stim_signal_list_df['date'] = periodicDateList
                            periodic_stim_signal_list_df['shift'] = periodicShiftList
    
                            if VNS_active:
                                periodic_stim_VNS_signal_list_df['participant_ID'] = periodicParticipantIDList
                                periodic_stim_VNS_signal_list_df['game_name'] = periodicGameNameList
                                periodic_stim_VNS_signal_list_df['exercise_name'] = periodicExerciseNameList
                                periodic_stim_VNS_signal_list_df['stim_rate'] = periodicStimulationRateList
                                periodic_stim_VNS_signal_list_df['hist_sel'] = periodicHistoricalSelectivityList
                                periodic_stim_VNS_signal_list_df['selectivity'] = periodicLookbackSelectivityList
                                periodic_stim_VNS_signal_list_df['date'] = periodicDateList
                                periodic_stim_VNS_signal_list_df['shift'] = periodicShiftList
                            
                            if len(periodic_stim_signal_list) > 0:
                                # create or append dataframe to csv
                                periodic_stim_signal_list_df.to_csv(f"periodic_game_signal_{participantID}_df.csv", mode = 'a', header = pheader)
                                if VNS_active:
                                    periodic_stim_VNS_signal_list_df.to_csv(f"periodic_VNS_signal_{participantID}_df.csv", mode = 'a', header=pheader)
                                pheader = False    
                            print(f"\n{participantID}:Finished periodic stimulation analysis for this activity...\n") 
                        
                        # if we want to save random stimulations...
                        if randomEnabled:
                        
                            #get the current signal
                            current_signal = game_signal_actual
                            #get the length of the current signal
                            current_signal_length = len(current_signal)
                            #get the number of stimulations that will occur for the current signal
                            average_interval = 600

                            # Generate normally distributed intervals between samples with mean=average_interval
                            intervals = np.random.normal(loc=average_interval, scale=100, size=1000)

                            # Compute the cumulative sum of intervals to get the indices of the selected samples
                            indices = np.cumsum(intervals).astype(int)

                            # Filter out indices that are outside the signal range
                            indices = indices[indices < current_signal_length]
                            
                            print(f"{participantID}:Starting analysis for random stimulation. There are {len(indices)} stimulations in this signal.")
                            
                            #Iterate over each random stim   
                            for stim in indices:
                                
                                numberOfRandomStims = numberOfRandomStims + 1

                                if stim < 60*30:
                                    print("Stim is too close to the beginning of the signal. Skipping this stimulation.")
                                    continue
                                stim_index = stim
                                stim_value = abs(game_signal_actual[stim_index])
                                print(f"{participantID}:Stim at {stim_index} with value {stim_value}")
                                
                                #Use the stimulation time to get the signal before and after the stimulation
                                stim_start_index = stim_index - startingIndexShift
                                stim_end_index = stim_index + startingIndexShift
                                if (stim_start_index < 0):
                                    stim_start_index = 0
                                if (stim_end_index > len(game_signal_actual)):
                                    stim_end_index = len(game_signal_actual)
                                stim_signal = np.abs(game_signal_actual[stim_start_index:stim_end_index])
                                if VNS_active:
                                    stim_VNS_signal = np.abs(vns_signal[stim_start_index:stim_end_index])
                                    
                                #Check if the signal is the correct length and within the maximum value allowed
                                if(len(stim_signal) != windowIndexTotal):
                                    print(f"{participantID}:Length of signal is not correct!")
                                    continue

                                random_stim_signal_list.append(stim_signal)
                                if VNS_active:
                                    random_stim_VNS_signal_list.append(stim_VNS_signal)
                                randomParticipantIDList.append(current_participant.uid)
                                randomGameNameList.append(activity.GetGameName())
                                randomExerciseNameList.append(activity.GetExerciseName())
                                randomStimulationRateList.append(len(stimulationTimes)/(activity.duration/60))
                                randomDateList.append(visitDateTime)
                                stimMax = np.max(stim_signal[600-60:600+60])
                                
                                if stim_index > 3000:
                                    randomLookbackSelectivityList.append(stats.percentileofscore(game_signal_actual[stim_index-3000:stim_index],stimMax))
                                else:
                                    randomLookbackSelectivityList.append(stats.percentileofscore(game_signal_actual[0:stim_index],stimMax))
                                randomHistoricalSelectivityList.append(stats.percentileofscore(game_signal_actual,stimMax))
                                numberOfRandomStims = numberOfRandomStims + 1

                            random_stim_signal_list_df = pd.DataFrame(random_stim_signal_list)
                            if VNS_active:
                                random_stim_VNS_signal_list_df = pd.DataFrame(random_stim_VNS_signal_list)
                            
                            print(f"{participantID}:Writing lists to new columns of random stimulation dataframes...")
                            random_stim_signal_list_df['participant_ID'] = randomParticipantIDList
                            random_stim_signal_list_df['game_name'] = randomGameNameList
                            random_stim_signal_list_df['exercise_name'] = randomExerciseNameList
                            random_stim_signal_list_df['stim_rate'] = randomStimulationRateList
                            random_stim_signal_list_df['hist_sel'] = randomHistoricalSelectivityList
                            random_stim_signal_list_df['selectivity'] = randomLookbackSelectivityList
                            random_stim_signal_list_df['date'] = randomDateList
                            
                            if VNS_active:
                                random_stim_VNS_signal_list_df['participant_ID'] = randomParticipantIDList
                                random_stim_VNS_signal_list_df['game_name'] = randomGameNameList
                                random_stim_VNS_signal_list_df['exercise_name'] = randomExerciseNameList
                                random_stim_VNS_signal_list_df['stim_rate'] = randomStimulationRateList 
                                random_stim_VNS_signal_list_df['hist_sel'] = randomHistoricalSelectivityList
                                random_stim_VNS_signal_list_df['selectivity'] = randomLookbackSelectivityList
                                random_stim_VNS_signal_list_df['date'] = randomDateList
                            
                            if len(random_stim_signal_list) > 0:

                                random_stim_signal_list_df.to_csv(f"random_game_signal_{participantID}_df.csv", mode = 'a', header = rheader)
                                
                                if VNS_active:
                                    random_stim_VNS_signal_list_df.to_csv(f"random_VNS_signal_{participantID}_df.csv", mode='a', header=rheader)
                                rheader = False

                        # if we want to look at manual stimulations...            
                        if manualEnabled:

                            print(f"{participantID}:Starting manual stimulation analysis. There are {len(stims_for_current_activity)} stimulations in this signal.")
                            
                            #Iterate over each manual stimulation
                            for stim in stims_for_current_activity:
                                
                                #Get the stimulation time, index, and value
                                stim_time = (stim - first_device_sample_time).total_seconds()
                                stim_index = np.argmin(np.abs(np.asarray(game_signal_timestamps) - stim_time))
                                
                                if stim_index < 60*30:
                                    print("Stim is too close to the beginning of the signal. Skipping this stimulation.")
                                    continue
                                
                                stim_value = abs(game_signal_actual[stim_index])
                                print(f"{participantID}:Stim at {stim_time} with value {stim_value}")
                                
                                #Use the stimulation time to get the signal before and after the stimulation
                                stim_start_index = stim_index - startingIndexShift
                                stim_end_index = stim_index + startingIndexShift
                                if (stim_start_index < 0):
                                    stim_start_index = 0
                                if (stim_end_index > len(game_signal_actual)):
                                    stim_end_index = len(game_signal_actual)
                                stim_signal = np.abs(game_signal_actual[stim_start_index:stim_end_index])
                                if VNS_active:
                                    stim_VNS_signal = np.abs(vns_signal[stim_start_index:stim_end_index])
                                
                                #Check if the signal is the correct length and within the maximum value allowed
                                if(len(stim_signal) != windowIndexTotal):
                                    print(f"{participantID}:Length of signal is not correct!")
                                    continue

                                #Add the signals to the lists
                                manual_stim_signal_list.append(stim_signal)
                                if VNS_active:
                                    manual_stim_VNS_signal_list.append(stim_VNS_signal)
                                manualParticipantIDList.append(current_participant.uid)
                                manualGameNameList.append(activity.GetGameName())
                                manualExerciseNameList.append(activity.GetExerciseName())
                                manualStimulationRateList.append(len(stims_for_current_activity)/(activity.duration/60))
                                manualDateList.append(visitDateTime)
                                stimMax = np.max(stim_signal[600-60:600+60])
                                
                                if stim_index > 3000:
                                    manualLookbackSelectivityList.append(stats.percentileofscore(game_signal_actual[stim_index-3000:stim_index],stimMax))
                                else:
                                    manualLookbackSelectivityList.append(stats.percentileofscore(game_signal_actual[0:stim_index],stimMax))
                                manualHistoricalSelectivityList.append(stats.percentileofscore(game_signal_actual,stimMax))
                                
                                numberOfManualStims = numberOfManualStims + 1
                                
                            manual_overall_avg_signal_df = pd.DataFrame(manual_stim_signal_list)
                            
                            if VNS_active:
                                manual_stim_VNS_signal_list_df = pd.DataFrame(manual_stim_VNS_signal_list)
                                
                            print(f"{participantID}:Writing lists to new columns of manual stim dataframes...")
                            manual_overall_avg_signal_df['participant_ID'] = manualParticipantIDList
                            manual_overall_avg_signal_df['game_name'] = manualGameNameList
                            manual_overall_avg_signal_df['exercise_name'] = manualExerciseNameList
                            manual_overall_avg_signal_df['stim_rate'] = manualStimulationRateList
                            manual_overall_avg_signal_df['hist_sel'] = manualHistoricalSelectivityList
                            manual_overall_avg_signal_df['selectivity'] = manualLookbackSelectivityList
                            manual_overall_avg_signal_df['date'] = manualDateList
                            
                            if VNS_active:
                                manual_stim_VNS_signal_list_df['selectivity'] = manualLookbackSelectivityList
                                manual_stim_VNS_signal_list_df['hist_sel'] = manualHistoricalSelectivityList
                                manual_stim_VNS_signal_list_df['stim_rate'] = manualStimulationRateList
                                manual_stim_VNS_signal_list_df['exercise_name'] = manualExerciseNameList
                                manual_stim_VNS_signal_list_df['game_name'] = manualGameNameList
                                manual_stim_VNS_signal_list_df['participant_ID'] = manualParticipantIDList
                                manual_stim_VNS_signal_list_df['date'] = manualDateList

                            if len(manual_stim_signal_list) > 0:
                                if manualEnabled:
                                    manual_overall_avg_signal_df.to_csv(f"manual_game_signal_{participantID}_df.csv", mode = 'a', header=mheader)
                                if VNS_active:
                                    manual_stim_VNS_signal_list_df.to_csv(f"manual_VNS_signal_{participantID}_df.csv", mode = 'a', header=mheader)
                                mheader = False

                        print(f"\n{participantID}:Finished manual stimulation analysis for this activity\n")
                            
                        if autoEnabled and VNS_active:
                            print(f"{participantID}:Starting automatic stimulation analysis. There are {len(vns_trigger_ts)} stimulations in this signal.")
                            #Iterate over each automatic stimulation    
                            for stim in vns_trigger_ts:
                                
                                #Get the stimulation time, index, and value
                                stim_time = stim
                                stim_index = np.argmin(np.abs(np.asarray(game_signal_timestamps) - stim_time))
                                
                                if stim_index < 60*30:
                                    print("Stim is too close to the beginning of the signal. Skipping this stimulation.")
                                    continue
                                
                                stim_value = abs(game_signal_actual[stim_index])
                                print(f"{participantID}:Stim at {stim_time} with value {stim_value}")
                                
                                #Use the stimulation time to get the signal before and after the stimulation
                                stim_start_index = stim_index - startingIndexShift
                                stim_end_index = stim_index + startingIndexShift
                                if (stim_start_index < 0):
                                    stim_start_index = 0
                                if (stim_end_index > len(game_signal_actual)):
                                    stim_end_index = len(game_signal_actual)
                                stim_signal = np.abs(game_signal_actual[stim_start_index:stim_end_index])
                                stim_VNS_signal = np.abs(vns_signal[stim_start_index:stim_end_index])
                                
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
                                autoStimulationRateList.append(len(vns_trigger_ts)/(activity.duration/60)) 
                                autoDateList.append(visitDateTime)
                                stimMax = np.max(stim_signal[600-60:600+60])
                                
                                if stim_index > 3000:
                                    autoLookbackSelectivityList.append(stats.percentileofscore(game_signal_actual[stim_index-3000:stim_index],stimMax))
                                else:
                                    autoLookbackSelectivityList.append(stats.percentileofscore(game_signal_actual[0:stim_index],stimMax))
                                autoHistoricalSelectivityList.append(stats.percentileofscore(game_signal_actual,stimMax))
        
                                numberOfAutoStims = numberOfAutoStims + 1
                                # autoStimRate.append(len(vns_trigger_ts)/(activity.duration/60))
                            
                            auto_stim_signal_list_df = pd.DataFrame(auto_stim_signal_list)
                            
                            if VNS_active:
                                auto_stim_VNS_signal_list_df = pd.DataFrame(auto_stim_VNS_signal_list)
                            
                            print(f"{participantID}:Writing lists to new columns of algorithm dataframes...")
                            auto_stim_signal_list_df['participant_ID'] = autoParticipantIDList
                            auto_stim_signal_list_df['game_name'] = autoGameNameList
                            auto_stim_signal_list_df['exercise_name'] = autoExerciseNameList
                            auto_stim_signal_list_df['stim_rate'] = autoStimulationRateList
                            auto_stim_signal_list_df['hist_sel'] = autoHistoricalSelectivityList
                            auto_stim_signal_list_df['selectivity'] = autoLookbackSelectivityList
                            auto_stim_signal_list_df['date'] = autoDateList
                            
                            if VNS_active:
                                auto_stim_VNS_signal_list_df['hist_sel'] = autoHistoricalSelectivityList
                                auto_stim_VNS_signal_list_df['selectivity'] = autoLookbackSelectivityList
                                auto_stim_VNS_signal_list_df['date'] = autoDateList
                                auto_stim_VNS_signal_list_df['stim_rate'] = autoStimulationRateList
                                auto_stim_VNS_signal_list_df['exercise_name'] = autoExerciseNameList
                                auto_stim_VNS_signal_list_df['game_name'] = autoGameNameList
                                auto_stim_VNS_signal_list_df['participant_ID'] = autoParticipantIDList
                            
                            if len(auto_stim_signal_list) > 0:

                                auto_stim_signal_list_df.to_csv(f"auto_game_signal_{participantID}_df.csv", mode='a', header=aheader) 
                                
                                if VNS_active:
                                    auto_stim_VNS_signal_list_df.to_csv(f"auto_VNS_signal_{participantID}_df.csv", mode = 'a', header = aheader)
                                aheader = False

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
    if periodicEnabled:
        print(f"\n{participantID}:Total Periodic Stimulations: {numberOfPeriodicStims}")
        
    print(f"\n{participantID}:Total sessions: {numberOfSessions}")

    et = time.time()
    elapsed = (et - st)/60
    print(f"{participantID}:Elapsed time: {elapsed}")

def main():
    with concurrent.futures.ProcessPoolExecutor() as executor:
        executor.map(getAlgorithmResultsPerParticipant, participantsToFind)
        executor.shutdown(wait=True)
        
    print("Done! Disconnecting from database...")
    disconnect()

if __name__ == '__main__':
    main()