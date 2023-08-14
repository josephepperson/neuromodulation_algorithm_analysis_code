import sys
import os.path as o
import pandas as pd
import seaborn as sns
import matplotlib as mpl

import matplotlib.pyplot as plot

sys.path.append(o.abspath(o.join(o.dirname(sys.modules[__name__].__file__), "..")))

from colorama import Fore
from colorama import Style

import numpy as np
from scipy.signal import find_peaks
import seaborn as sns
from scipy import stats

VNS_signal_analysis = False
game_signal_analysis = True

font = {'family' : 'normal',
        'weight' : 'normal',
        'size'   : 22}

sns.set_theme(style="white")

plot.rc('font', **font)

participants = ["001-002-00001","001-002-00002","001-002-00003","001-002-00004"]

signalAttributes_all = ['participant_ID','game_name','exercise_name','stim_rate','hist_sel','selectivity','date']
signalAttributes_short = ['hist_sel','selectivity']
signalAttributes_hist_sel = ['participant_ID','game_name','exercise_name','stim_rate','selectivity','date']
folderName = "figures"
dataFolderName = "data"

manual_game_signal_df = pd.DataFrame()
auto_game_signal_df = pd.DataFrame()
manual_VNS_signal_df = pd.DataFrame()
auto_VNS_signal_df = pd.DataFrame()
periodic_cont_game_signal_df = pd.DataFrame()
periodic_cont_VNS_signal_df = pd.DataFrame()
periodic_game_signal_df = pd.DataFrame()
periodic_VNS_signal_df = pd.DataFrame()
random_cont_game_signal_df = pd.DataFrame()
random_cont_VNS_signal_df = pd.DataFrame()
random_game_signal_df = pd.DataFrame()
random_VNS_signal_df = pd.DataFrame()

for participantID in participants:
    
    print(f"Loading manual stims for {participantID}")
    manual_signal_temp_df = pd.read_csv(f"manual_game_signal_{participantID}_df.csv")
    manual_game_signal_df = pd.concat([manual_game_signal_df, manual_signal_temp_df])

    manual_VNS_signal_temp_df = pd.read_csv(f"manual_VNS_signal_{participantID}_df.csv")
    manual_VNS_signal_df = pd.concat([manual_VNS_signal_df, manual_VNS_signal_temp_df])

    print(f"Loading auto stims for participant {participantID}")
    auto_signal_temp_df = pd.read_csv(f"auto_game_signal_{participantID}_df.csv") 
    auto_game_signal_df = pd.concat([auto_game_signal_df, auto_signal_temp_df])
    
    auto_VNS_signal_temp_df = pd.read_csv(f"auto_VNS_signal_{participantID}_df.csv")
    auto_VNS_signal_df = pd.concat([auto_VNS_signal_df, auto_VNS_signal_temp_df])
    
    print(f"Loading impersistent periodic stims for participant {participantID}")
    periodic_signal_temp_df = pd.read_csv(f"periodic_game_signal_{participantID}_df.csv")
    periodic_game_signal_df = pd.concat([periodic_game_signal_df, periodic_signal_temp_df])
    
    periodic_VNS_signal_temp_df = pd.read_csv(f"periodic_VNS_signal_{participantID}_df.csv")
    periodic_VNS_signal_df = pd.concat([periodic_VNS_signal_df, periodic_VNS_signal_temp_df]) 
    
    print(f"Loading impersistent random stims for participant {participantID}")
    random_game_signal_temp_df = pd.read_csv(f"random_game_signal_{participantID}_df.csv")
    random_game_signal_df = pd.concat([random_game_signal_df, random_game_signal_temp_df])    
    random_VNS_signal_temp_df = pd.read_csv(f"random_VNS_signal_{participantID}_df.csv")
    random_VNS_signal_df = pd.concat([random_VNS_signal_df, random_VNS_signal_temp_df])

# in case the analysis code appended additional headers, remove any rows with the same content as the header
manual_game_signal_df = manual_game_signal_df[manual_game_signal_df.participant_ID != 'participant_ID']
auto_game_signal_df = auto_game_signal_df[auto_game_signal_df.participant_ID != 'participant_ID']
manual_VNS_signal_df = manual_VNS_signal_df[manual_VNS_signal_df.participant_ID != 'participant_ID']
auto_VNS_signal_df = auto_VNS_signal_df[auto_VNS_signal_df.participant_ID != 'participant_ID']
periodic_game_signal_df = periodic_game_signal_df[periodic_game_signal_df.participant_ID != 'participant_ID']
periodic_VNS_signal_df = periodic_VNS_signal_df[periodic_VNS_signal_df.participant_ID != 'participant_ID']
random_game_signal_df = random_game_signal_df[random_game_signal_df.participant_ID != 'participant_ID']
random_VNS_signal_df = random_VNS_signal_df[random_VNS_signal_df.participant_ID != 'participant_ID']

# remove extra column that may be created from csv export/import
auto_VNS_signal_df = auto_VNS_signal_df.drop("Unnamed: 0", axis=1)
auto_game_signal_df = auto_game_signal_df.drop("Unnamed: 0", axis=1)
manual_VNS_signal_df = manual_VNS_signal_df.drop("Unnamed: 0", axis=1)
manual_game_signal_df = manual_game_signal_df.drop("Unnamed: 0", axis=1)
periodic_game_signal_df = periodic_game_signal_df.drop("Unnamed: 0", axis=1)
periodic_VNS_signal_df = periodic_VNS_signal_df.drop("Unnamed: 0", axis=1)
random_game_signal_df = random_game_signal_df.drop("Unnamed: 0", axis=1)
random_VNS_signal_df = random_VNS_signal_df.drop("Unnamed: 0", axis=1)

# drop columns that do not contain signal data and create alternative datasets for ease of use
auto_VNS_signal_dfA = auto_VNS_signal_df.drop(columns = signalAttributes_all, axis=1)
auto_game_signal_dfA = auto_game_signal_df.drop(columns = signalAttributes_all, axis=1)

manual_VNS_signal_dfA = manual_VNS_signal_df.drop(columns = signalAttributes_all, axis=1)
manual_game_signal_dfA = manual_game_signal_df.drop(columns = signalAttributes_all, axis=1)

periodic_game_signal_dfA = periodic_game_signal_df.drop(columns = signalAttributes_all, axis=1)
periodic_game_signal_dfA = periodic_game_signal_dfA.drop(columns = 'shift', axis=1)
periodic_VNS_signal_dfA = periodic_VNS_signal_df.drop(columns = signalAttributes_all, axis=1)

random_game_signal_dfA = random_game_signal_df.drop(columns = signalAttributes_short, axis=1)
random_VNS_signal_dfA = random_VNS_signal_df.drop(columns = signalAttributes_short, axis=1)

# if the analysis is intended for the game signal, normalize the data by each participant per day, per exercise, per game, on each day.
if game_signal_analysis:

    full_auto_dfNORM = pd.DataFrame()
    full_manual_dfNORM = pd.DataFrame()
    full_periodic_dfNORM = pd.DataFrame()
    full_random_dfNORM = pd.DataFrame()
    full_auto_dfNORM_raw = pd.DataFrame()
    full_manual_dfNORM_raw = pd.DataFrame()
    full_periodic_dfNORM_raw = pd.DataFrame()
    full_random_dfNORM_raw = pd.DataFrame()

    for participant in manual_game_signal_df.participant_ID.unique():
        
        for index, exercise in enumerate(manual_game_signal_df.exercise_name.unique()):
            
            for game in manual_game_signal_df.game_name.unique():
                
                for dateOfActivity in manual_game_signal_df.date.unique():
                        
                    manual_df = manual_game_signal_df[(manual_game_signal_df.exercise_name == exercise) & (manual_game_signal_df.game_name == game) & (manual_game_signal_df.participant_ID == participant) & (manual_game_signal_df.date == dateOfActivity)]
                    
                    if len(manual_df[manual_df.participant_ID == participant]) == 0:
                        continue

                    print(f"Found some data for {participant} on {dateOfActivity} playing {game} with {exercise}")
                    manual_dfA = manual_df.drop(columns = signalAttributes_all, axis=1)

                    auto_df = auto_game_signal_df[(auto_game_signal_df.exercise_name == exercise) & (auto_game_signal_df.game_name == game) & (auto_game_signal_df.participant_ID == participant)& (auto_game_signal_df.date == dateOfActivity)]
                    auto_dfA = auto_df.drop(columns = signalAttributes_all, axis=1)

                    random_df = random_game_signal_df[(random_game_signal_df.exercise_name == exercise) & (random_game_signal_df.game_name == game) & (random_game_signal_df.participant_ID == participant) & (random_game_signal_df.date == dateOfActivity)]
                    random_dfA = random_df.drop(columns = signalAttributes_all, axis=1)
                    
                    periodic_df = periodic_game_signal_df[(periodic_game_signal_df.exercise_name == exercise) & (periodic_game_signal_df.game_name == game) & (periodic_game_signal_df.participant_ID == participant) & (periodic_game_signal_df.date == dateOfActivity)]
                    periodic_dfA = periodic_df.iloc[:,0:2400]

                    periodicShiftList = []
                    
                    lowerIndexSlice = 540
                    upperIndexSlice = 660
                    
                    for subset in periodic_df['shift'].unique():
                        slice = periodic_df[periodic_df['shift'] == subset].iloc[:,lowerIndexSlice:upperIndexSlice].T.max()
                        denom = sum(slice)/len(slice)
                        periodicShiftList.append(denom)
                        
                    print(periodicShiftList)
                    denom = sum(periodicShiftList)/len(periodicShiftList)
                    
                    if denom == 0:
                        print("DIVISION BY ZERO")
                    print(f"Exercise: {exercise}, Denominator: {denom}")
                    
                    manual_dfNORM = (manual_dfA/denom)*100-100
                    auto_dfNORM = (auto_dfA/denom)*100-100
                    periodic_dfNORM = (periodic_dfA/denom)*100-100
                    random_dfNORM = (random_dfA/denom)*100-100
                    
                    full_auto_dfNORM_raw = pd.concat([full_auto_dfNORM_raw,auto_dfNORM])
                    full_manual_dfNORM_raw = pd.concat([full_manual_dfNORM_raw,manual_dfNORM])
                    full_periodic_dfNORM_raw = pd.concat([full_periodic_dfNORM_raw,periodic_dfNORM])
                    full_random_dfNORM_raw = pd.concat([full_random_dfNORM_raw,random_dfNORM])
                    
                    manual_dfNORM['Exercise'] = exercise
                    auto_dfNORM['Exercise'] = exercise
                    periodic_dfNORM['Exercise'] = exercise
                    random_dfNORM['Exercise'] = exercise
                    
                    manual_dfNORM['game_name'] = manual_df['game_name'].to_numpy()
                    auto_dfNORM['game_name'] = auto_df['game_name'].to_numpy()
                    periodic_dfNORM['game_name'] = periodic_df['game_name'].to_numpy()
                    random_dfNORM['game_name'] = random_df['game_name'].to_numpy()
                    
                    manual_dfNORM['date'] = manual_df['date'].to_numpy()
                    auto_dfNORM['date'] = auto_df['date'].to_numpy()
                    periodic_dfNORM['date'] = periodic_df['date'].to_numpy()
                    random_dfNORM['date'] = random_df['date'].to_numpy()
                    
                    manual_dfNORM['participant_ID'] = manual_df['participant_ID'].to_numpy()
                    auto_dfNORM['participant_ID'] = auto_df['participant_ID'].to_numpy()
                    periodic_dfNORM['participant_ID'] = periodic_df['participant_ID'].to_numpy()
                    random_dfNORM['participant_ID'] = random_df['participant_ID'].to_numpy()
                    
                    full_auto_dfNORM = pd.concat([full_auto_dfNORM,auto_dfNORM])
                    full_manual_dfNORM = pd.concat([full_manual_dfNORM,manual_dfNORM])
                    full_periodic_dfNORM = pd.concat([full_periodic_dfNORM,periodic_dfNORM])
                    full_random_dfNORM = pd.concat([full_random_dfNORM,random_dfNORM])

    full_auto_dfNORM = full_auto_dfNORM.reset_index(drop = True)
    full_manual_dfNORM = full_manual_dfNORM.reset_index(drop = True)
    full_periodic_dfNORM = full_periodic_dfNORM.reset_index(drop = True)
    full_random_dfNORM = full_random_dfNORM.reset_index(drop = True)

# normalize the VNS signals if this type of analysis is enabled

if VNS_signal_analysis:
    full_auto_dfNORM = pd.DataFrame()
    full_manual_dfNORM = pd.DataFrame()
    full_periodic_dfNORM = pd.DataFrame()
    full_random_dfNORM = pd.DataFrame()
    full_auto_dfNORM_raw = pd.DataFrame()
    full_manual_dfNORM_raw = pd.DataFrame()
    full_periodic_dfNORM_raw = pd.DataFrame()
    full_random_dfNORM_raw = pd.DataFrame()

    for participant in manual_VNS_signal_df.participant_ID.unique():
        
        for index, exercise in enumerate(manual_VNS_signal_df.exercise_name.unique()):
            
            for game in manual_VNS_signal_df.game_name.unique():
                
                for dateOfActivity in manual_VNS_signal_df.date.unique():
                        
                    manual_df = manual_VNS_signal_df[(manual_VNS_signal_df.exercise_name == exercise) & (manual_VNS_signal_df.game_name == game) & (manual_VNS_signal_df.participant_ID == participant) & (manual_VNS_signal_df.date == dateOfActivity)]
                    
                    if len(manual_df[manual_df.participant_ID == participant]) == 0:
                        continue

                    print(f"Found some data for {participant} on {dateOfActivity} playing {game} with {exercise}")
                    manual_dfA = manual_df.drop(columns = signalAttributes_all, axis=1)

                    auto_df = auto_VNS_signal_df[(auto_VNS_signal_df.exercise_name == exercise) & (auto_VNS_signal_df.game_name == game) & (auto_VNS_signal_df.participant_ID == participant)& (auto_VNS_signal_df.date == dateOfActivity)]
                    auto_dfA = auto_df.drop(columns = signalAttributes_all, axis=1)

                    random_df = random_VNS_signal_df[(random_VNS_signal_df.exercise_name == exercise) & (random_VNS_signal_df.game_name == game) & (random_VNS_signal_df.participant_ID == participant) & (random_VNS_signal_df.date == dateOfActivity)]
                    random_dfA = random_df.drop(columns = signalAttributes_all, axis=1)
                    
                    periodic_df = periodic_VNS_signal_df[(periodic_VNS_signal_df.exercise_name == exercise) & (periodic_VNS_signal_df.game_name == game) & (periodic_VNS_signal_df.participant_ID == participant) & (periodic_VNS_signal_df.date == dateOfActivity)]
                    periodic_dfA = periodic_df.iloc[:,0:2400]

                    periodicShiftList = []
                    
                    lowerIndexSlice = 1140
                    upperIndexSlice = 1260
                    
                    for subset in periodic_df['shift'].unique():
                        slice = periodic_df[periodic_df['shift'] == subset].iloc[:,lowerIndexSlice:upperIndexSlice].T.max()
                        denom = sum(slice)/len(slice)
                        periodicShiftList.append(denom)
                        
                    print(periodicShiftList)
                    denom = sum(periodicShiftList)/len(periodicShiftList)
                    if denom == 0:
                        print("DIVISION BY ZERO")
                    print(f"Exercise: {exercise}, Denominator: {denom}")
                    
                    manual_dfNORM = (manual_dfA/denom)*100-100
                    auto_dfNORM = (auto_dfA/denom)*100-100
                    periodic_dfNORM = (periodic_dfA/denom)*100-100
                    random_dfNORM = (random_dfA/denom)*100-100
                    
                    full_auto_dfNORM_raw = pd.concat([full_auto_dfNORM_raw,auto_dfNORM])
                    full_manual_dfNORM_raw = pd.concat([full_manual_dfNORM_raw,manual_dfNORM])
                    full_periodic_dfNORM_raw = pd.concat([full_periodic_dfNORM_raw,periodic_dfNORM])
                    full_random_dfNORM_raw = pd.concat([full_random_dfNORM_raw,random_dfNORM])
                    
                    manual_dfNORM['Exercise'] = exercise
                    auto_dfNORM['Exercise'] = exercise
                    periodic_dfNORM['Exercise'] = exercise
                    random_dfNORM['Exercise'] = exercise
                    
                    manual_dfNORM['game_name'] = manual_df['game_name'].to_numpy()
                    auto_dfNORM['game_name'] = auto_df['game_name'].to_numpy()
                    periodic_dfNORM['game_name'] = periodic_df['game_name'].to_numpy()
                    random_dfNORM['game_name'] = random_df['game_name'].to_numpy()
                    
                    manual_dfNORM['date'] = manual_df['date'].to_numpy()
                    auto_dfNORM['date'] = auto_df['date'].to_numpy()
                    periodic_dfNORM['date'] = periodic_df['date'].to_numpy()
                    random_dfNORM['date'] = random_df['date'].to_numpy()
                    
                    manual_dfNORM['participant_ID'] = manual_df['participant_ID'].to_numpy()
                    auto_dfNORM['participant_ID'] = auto_df['participant_ID'].to_numpy()
                    periodic_dfNORM['participant_ID'] = periodic_df['participant_ID'].to_numpy()
                    random_dfNORM['participant_ID'] = random_df['participant_ID'].to_numpy()
                    
                    full_auto_dfNORM = pd.concat([full_auto_dfNORM,auto_dfNORM])
                    full_manual_dfNORM = pd.concat([full_manual_dfNORM,manual_dfNORM])
                    full_periodic_dfNORM = pd.concat([full_periodic_dfNORM,periodic_dfNORM])
                    full_random_dfNORM = pd.concat([full_random_dfNORM,random_dfNORM])

    full_auto_dfNORM = full_auto_dfNORM.reset_index(drop = True)
    full_manual_dfNORM = full_manual_dfNORM.reset_index(drop = True)
    full_periodic_dfNORM = full_periodic_dfNORM.reset_index(drop = True)
    full_random_dfNORM = full_random_dfNORM.reset_index(drop = True)

#create a vector for plotting and convert it from indexes to seconds
# NOTICE: THIS CODE ASSUMES DATA IS 2400 SAMPLES (40 SECONDS) WIDE 
x = np.arange(-1200, 1200)/60

df_grouped = pd.DataFrame()

df_grouped['median'] = full_manual_dfNORM_raw.mean()
df_grouped['ci'] = full_manual_dfNORM_raw.sem()*1.96
df_grouped['ci_upper'] = df_grouped['median'] + df_grouped['ci']
df_grouped['ci_lower'] = df_grouped['median'] - df_grouped['ci']

df_grouped2 = pd.DataFrame()

df_grouped2['median'] = full_auto_dfNORM_raw.mean()
df_grouped2['ci'] = full_auto_dfNORM_raw.sem()*1.96
df_grouped2['ci_upper'] = df_grouped2['median'] + df_grouped2['ci']
df_grouped2['ci_lower'] = df_grouped2['median'] - df_grouped2['ci']

df_grouped3 = pd.DataFrame()

df_grouped3['median'] = full_periodic_dfNORM_raw.mean()
df_grouped3['ci'] = full_periodic_dfNORM_raw.sem()*1.96
df_grouped3['ci_upper'] = df_grouped3['median'] + df_grouped3['ci']
df_grouped3['ci_lower'] = df_grouped3['median'] - df_grouped3['ci']

fig, ax = plot.subplots(figsize=(30, 10))

x = np.arange(-1200, 1200)/60

ax.plot(x, df_grouped['median'], color = "blue", label = "Manual Stim")
ax.fill_between(
    x, df_grouped['ci_lower'], df_grouped['ci_upper'], color='blue', alpha=.15)

ax.plot(x, df_grouped2['median'], color = "red", label = "Auto Stim")
ax.fill_between(
    x, df_grouped2['ci_lower'], df_grouped2['ci_upper'], color='red', alpha=.15)

ax.plot(x, df_grouped3['median'], color = "green", label = "Periodic Stim")
ax.fill_between(
    x, df_grouped3['ci_lower'], df_grouped3['ci_upper'], color='green', alpha=.15)

ax.set_xlim(-5,5)
x = np.arange(-1, 1, 0.01)
ax.fill_between(x, -1, 2, alpha = 0.1, color = "grey", zorder = -1)
ax.axvline(x=0, color = "grey", linestyle = "--")
plot.xticks(np.arange(-20, 20, step=2))
ax.set_title("Manual vs. Automatic Triggering")
ax.legend()
ax.set(xlabel='Time from Trigger (sec)', ylabel='Signal Amplitude (Normalized)')
plot.show()
plot.close()

##########################

# let's see how the peak selection compares across algorithms.

lowerIndexSlice = 1140
upperIndexSlice = 1260

full_manual_dfNORM['peaks'] = full_manual_dfNORM.iloc[:,lowerIndexSlice:upperIndexSlice].T.max()
full_auto_dfNORM['peaks'] = full_auto_dfNORM.iloc[:,lowerIndexSlice:upperIndexSlice].T.max()

full_manual_dfNORM['type'] = "Manual Stim"
full_auto_dfNORM['type'] = "Dynamic Algorithm"

full_manual_df_reduced = pd.DataFrame().assign(peaks=full_manual_dfNORM['peaks'],
                                               type=full_manual_dfNORM['type'],
                                               Exercise=full_manual_dfNORM['Exercise'])
full_auto_df_reduced = pd.DataFrame().assign(peaks=full_auto_dfNORM['peaks'],
                                             type=full_auto_dfNORM['type'],
                                             Exercise=full_auto_dfNORM['Exercise'])

dataframe = pd.DataFrame()
dataframe = pd.concat([full_manual_df_reduced,full_auto_df_reduced])

mpl.rcParams.update(mpl.rcParamsDefault)
font = {'size'   : 24}
plot.rc('font', **font)
plot.rcParams['font.sans-serif'] = "Myriad Pro"

fig, ax = plot.subplots(figsize=(6, 12.5),tight_layout=True)
plot.rcParams.update({'figure.autolayout': True})

ax.bar(x = ["Dynamic Algorithm","Manual Stimulation"],
    height = [dataframe[dataframe.type == 'Dynamic Algorithm'].peaks.mean(),
            dataframe[dataframe.type == 'Manual Stim'].peaks.mean()],
    color = ['#EA4335','#F4B400'],
    yerr = [dataframe[dataframe.type == 'Dynamic Algorithm'].peaks.sem(), 
            dataframe[dataframe.type == 'Manual Stim'].peaks.sem()])
ax.set_ylabel(f"Increase in paired movement size over open-loop (%)")

# The spines
plot.setp(ax.spines.values(), linewidth=2)
ax.spines[['right', 'top']].set_visible(False)

# The ticks
ax.xaxis.set_tick_params(width=2)
ax.yaxis.set_tick_params(width=2)
plot.xticks(rotation = 90)
plot.savefig("manualStimCompare_allStims.svg")

# statistics

dynamicMean = dataframe[dataframe.type == 'Dynamic Algorithm'].peaks.mean()
manualMean = dataframe[dataframe.type == 'Manual Stim'].peaks.mean()
dynamicSEM = dataframe[dataframe.type == 'Dynamic Algorithm'].peaks.sem()
manualSEM = dataframe[dataframe.type == 'Manual Stim'].peaks.sem()

print(f"Dynamic algorithm mean, SEM: {dynamicMean}, {dynamicSEM}")
print(f"Manual stim mean, SEM: {manualMean}, {manualSEM}")

ttest_results1 = stats.ttest_ind(dataframe[dataframe.type == 'Dynamic Algorithm'].peaks,
                                 dataframe[dataframe.type == 'Manual Stim'].peaks)

print(f"Statistic: {ttest_results1}")
meanDiff = abs(dynamicMean - manualMean)
semDiff = meanDiff/(ttest_results1[0])
print(f"Mean Difference: {meanDiff}, +/- {semDiff}")
##########################

# let's see how the peak selection compares across algorithms, but also grouped by exercise.

lowerIndexSlice = 1140
upperIndexSlice = 1260

full_manual_dfNORM['peaks'] = full_manual_dfNORM.iloc[:,lowerIndexSlice:upperIndexSlice].T.max()
full_auto_dfNORM['peaks'] = full_auto_dfNORM.iloc[:,lowerIndexSlice:upperIndexSlice].T.max()

full_manual_dfNORM['type'] = "Manual Stim"
full_auto_dfNORM['type'] = "Dynamic Algorithm"

full_manual_df_reduced = pd.DataFrame().assign(peaks=full_manual_dfNORM['peaks'],
                                               type=full_manual_dfNORM['type'],
                                               Exercise=full_manual_dfNORM['Exercise'])
full_auto_df_reduced = pd.DataFrame().assign(peaks=full_auto_dfNORM['peaks'],
                                             type=full_auto_dfNORM['type'],
                                             Exercise=full_auto_dfNORM['Exercise'])

dataframe = pd.DataFrame()
dataframe = pd.concat([full_manual_df_reduced,full_auto_df_reduced])

mpl.rcParams.update(mpl.rcParamsDefault)
font = {'size'   : 24}
plot.rc('font', **font)
plot.rcParams['font.sans-serif'] = "Myriad Pro"

fig, ax = plot.subplots(figsize=(6, 12.5),tight_layout=True)
plot.rcParams.update({'figure.autolayout': True})

ax.bar(x = ["Dynamic Algorithm","Manual Stimulation"],
    height = [dataframe[dataframe.type == 'Dynamic Algorithm'].groupby('Exercise').peaks.mean().mean(),
            dataframe[dataframe.type == 'Manual Stim'].groupby('Exercise').peaks.mean().mean()],
    color = ['#EA4335','#F4B400'],
    yerr = [dataframe[dataframe.type == 'Dynamic Algorithm'].groupby('Exercise').peaks.mean().sem(), 
            dataframe[dataframe.type == 'Manual Stim'].groupby('Exercise').peaks.mean().sem()])
ax.set_ylabel(f"Increase in paired movement size over open-loop (%)")

# The spines
plot.setp(ax.spines.values(), linewidth=2)
ax.spines[['right', 'top']].set_visible(False)

# The ticks
ax.xaxis.set_tick_params(width=2)
ax.yaxis.set_tick_params(width=2)
plot.xticks(rotation = 90)
plot.savefig("manualStimCompare_exercises")

# statistics

dynamicMean = dataframe[dataframe.type == 'Dynamic Algorithm'].groupby('Exercise').peaks.mean().mean()
manualMean = dataframe[dataframe.type == 'Manual Stim'].groupby('Exercise').peaks.mean().mean()
dynamicSEM = dataframe[dataframe.type == 'Dynamic Algorithm'].groupby('Exercise').peaks.mean().sem() 
manualSEM = dataframe[dataframe.type == 'Manual Stim'].groupby('Exercise').peaks.mean().sem()

print(f"Dynamic algorithm mean, SEM: {dynamicMean}, {dynamicSEM}")
print(f"Manual stim mean, SEM: {manualMean}, {manualSEM}")

ttest_results1 = stats.ttest_ind(list(dataframe[dataframe.type == 'Dynamic Algorithm'].groupby('Exercise').peaks.mean()),
                                 list(dataframe[dataframe.type == 'Manual Stim'].groupby('Exercise').peaks.mean()))

print(f"Statistic: {ttest_results1}")
meanDiff = abs(dynamicMean - manualMean)
semDiff = meanDiff/(ttest_results1[0])
print(f"Mean Difference: {meanDiff}, +/- {semDiff}")
