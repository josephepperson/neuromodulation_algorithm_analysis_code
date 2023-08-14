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
import matplotlib.pyplot as plot

from colorama import Fore
from colorama import Style
import colorama

from mongoengine import *
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
        
        stims_for_current_activity = activities[0].GetStimulationsFromReStoreDatalogs() 
        sorted_stims_on_cur_date = sorted(stims_for_current_activity)
        #test
        if (len(sorted_stims_on_cur_date) == 0):
            continue

        discrepancy = earliest_start_time - sorted_stims_on_cur_date[0]
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