# %%
import sys
import os.path as o

# %%
#region imports and setup

import time
import matplotlib.pyplot as plot
import pandas as pd

sys.path.append(o.abspath(o.join(o.dirname(sys.modules[__name__].__file__), "..")))

from datetime import datetime
from datetime import timedelta
import matplotlib.pyplot as plot

from colorama import Fore
from colorama import Style
import colorama

from mongoengine import *
from datetime import timedelta
from datetime import datetime
from RePlayAnalysisCore3.RePlayStudy import RePlayStudy
from RePlayAnalysisCore3.RePlayParticipant import RePlayParticipant
st = time.time()

#Initialize colorama
colorama.init()

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

#Define a couple of things that will be used later in the script when it comes time to save figures
current_date_str = datetime.now().strftime("%Y_%m_%d")

#endregion

# %%    

#Get a starttime for the script
script_start_time = datetime.now()

listOfDiscrepancies = []
listOfDates = []
userID = []

#Iterate over each participant
for participant_index, current_participant in enumerate(all_participants):
    print(f"Participant: {current_participant.uid}")
    #Get the visits for this participant
    visits = current_participant.children
    
    #Iterate over each visit
    for visit_index, thisVisit in enumerate(visits):
        
        #Check if this visit is after the end of the manual stimulation period. If so, skip it
        print(thisVisit.start_time)
        if (thisVisit.start_time > datetime(2021,8,30,0)):
            continue
        
        #Get the activities and start time for this visit
        visitDateTime = thisVisit.start_time
        activities = thisVisit.children
        
        #order activities by start time
        activities = sorted(activities, key=lambda x: x.start_time, reverse=False)
        
        earliest_start_time = activities[0].start_time
        next_start_time = activities[1].start_time
        if next_start_time - earliest_start_time > timedelta(seconds = 400):
            earliest_start_time = next_start_time
        
        # Let's see if we can maximize the number of stimulations for every exercise in a day for a participant...

        stims_for_current_activity = activities[0].GetStimulationsPerDayFromReStoreDatalogs() 
        sorted_stims_on_cur_date = sorted(stims_for_current_activity)
        
        if (len(sorted_stims_on_cur_date) == 0):
            continue

        #calculate stimulation mean
        stim_mean_time = (sorted_stims_on_cur_date[-1] - sorted_stims_on_cur_date[0])/2
        stim_mean_time = sorted_stims_on_cur_date[0] + stim_mean_time
        #calculate therapy mean
        therapy_start_time = activities[0].start_time
        therapy_end_time = activities[-1].start_time + timedelta(seconds = activities[-1].duration)
        therapy_mean_time = (therapy_end_time - therapy_start_time)/2
        therapy_mean_time = therapy_start_time + therapy_mean_time
        #calculate discrepancy between means
        discrepancy = therapy_mean_time - stim_mean_time
        seconds = discrepancy.total_seconds()
        listOfDiscrepancies.append(seconds)
        listOfDates.append(thisVisit.start_time)
        userID.append(current_participant.uid)

dataframe = pd.DataFrame()
dataframe["listOfDates"] = listOfDates
dataframe["listOfDiscrepancies"] = listOfDiscrepancies
dataframe["userID"] = userID

dataframe.to_csv("")

script_end_time = datetime.now()
script_running_time = script_end_time - script_start_time
print(f"Running duration of script: {script_running_time}")
print("")  
print("Done! Disconnecting from database...")
disconnect()