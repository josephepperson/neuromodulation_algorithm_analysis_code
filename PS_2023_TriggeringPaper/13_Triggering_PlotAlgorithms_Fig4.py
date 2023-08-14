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

participants = ["001-002-00001",
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

signalAttributes_all = ['participant_ID','game_name','exercise_name','stim_rate','hist_sel','selectivity','date']
signalAttributes_short = ['hist_sel','selectivity']
signalAttributes_hist_sel = ['participant_ID','game_name','exercise_name','stim_rate','selectivity','date']
folderName = "figures"
dataFolderName = "data"

auto_df = pd.DataFrame()
threshold_df = pd.DataFrame()
periodic_df = pd.DataFrame()
auto_df_temp = pd.DataFrame()
threshold_df_temp = pd.DataFrame()
periodic_df_temp = pd.DataFrame()

for participantID in participants:
    
    try:
        print(f"Loading manual stims for {participantID}")
        auto_df_temp = pd.read_csv(f"C:/Users/jde160530/Documents/TXBDC/Figure4_data/auto_game_signal_{participantID}_df.csv")
        auto_df = pd.concat([auto_df, auto_df_temp])

        print(f"Loading auto stims for participant {participantID}")
        periodic_df_temp = pd.read_csv(f"C:/Users/jde160530/Documents/TXBDC/Figure4_data/periodic_game_signal_{participantID}_df.csv") 
        periodic_df = pd.concat([periodic_df, periodic_df_temp])
        
        print(f"Loading persistent periodic stims for participant {participantID}")
        threshold_df_temp = pd.read_csv(f"C:/Users/jde160530/Documents/TXBDC/Figure4_data/threshold_game_signal_{participantID}_df.csv")
        threshold_df = pd.concat([threshold_df, threshold_df_temp])
    except:
        print("No file by that name...")

# remove extra column that may be created from csv export/import
auto_df = auto_df.drop("Unnamed: 0", axis=1)
periodic_df = periodic_df.drop("Unnamed: 0", axis=1)
threshold_df = threshold_df.drop("Unnamed: 0", axis=1)

# select activities that are at least 1 min long
auto_df = auto_df[auto_df.game_length > 1]
periodic_df = periodic_df[periodic_df.game_length > 1]
threshold_df = threshold_df[threshold_df.game_length > 1]

# plot selectivity
mpl.rcParams.update(mpl.rcParamsDefault)
font = {'size'   : 22}
plot.rc('font', **font)

labels = [ 'Dynamic', 'Threshold','Periodic']

fig, ax = plot.subplots(figsize=(10, 10))

medianprops = dict(linestyle='-', linewidth=1, color='black')

bplot1 = ax.boxplot(x = [auto_df[auto_df.algo_setting == 0.95].groupby(['start_time','algo_setting','participant_ID']).mean(numeric_only = True).selectivity.groupby('participant_ID').mean(),
                         threshold_df[threshold_df.algo_setting == 32].groupby(['start_time','algo_setting','participant_ID']).mean(numeric_only = True).selectivity.groupby('participant_ID').mean(),
                         periodic_df[periodic_df.algo_setting == 12].groupby(['start_time','algo_setting','participant_ID']).mean(numeric_only = True).selectivity.groupby('participant_ID').mean()
                         ],
                         notch=True,
                         vert=True,
                         patch_artist=True,
                         labels = labels,
                         medianprops=medianprops)
ax.set_ylabel("Percent of max movement")

# The spines
plot.setp(ax.spines.values(), linewidth=2)

# The ticks
ax.xaxis.set_tick_params(width=2)
ax.yaxis.set_tick_params(width=2)

ax.spines[['right', 'top']].set_visible(False)

# fill with colors
colors = ['#34A853', '#4285F4','#EA4335' ]
for patch, color in zip(bplot1['boxes'], colors):
    patch.set_facecolor(color)

plot.show()

# statistics

bp1periodic = periodic_df[periodic_df.algo_setting == 12].groupby(['start_time','algo_setting','participant_ID']).mean(numeric_only = True).selectivity.groupby('participant_ID').mean()
bp1threshold = threshold_df[threshold_df.algo_setting == 32].groupby(['start_time','algo_setting','participant_ID']).mean(numeric_only = True).selectivity.groupby('participant_ID').mean()
bp1auto = auto_df[auto_df.algo_setting == 0.95].groupby(['start_time','algo_setting','participant_ID']).mean(numeric_only = True).selectivity.groupby('participant_ID').mean()

bplot1 = ax.boxplot(x = [bp1auto,
                         bp1threshold,
                         bp1periodic
                         ],
                         notch=True,
                         patch_artist=False)

medians = [round(item.get_ydata()[0], 5) for item in bplot1['medians']]
means = [round(item.get_ydata()[0], 5) for item in bplot1['means']]
minimums = [round(item.get_ydata()[0], 5) for item in bplot1['caps']][::2]
maximums = [round(item.get_ydata()[0], 5) for item in bplot1['caps']][1::2]
q1 = [round(min(item.get_ydata()), 5) for item in bplot1['boxes']]
q3 = [round(max(item.get_ydata()), 5) for item in bplot1['boxes']]
IQRange = []
for i in range(len(q1)):
    IQRange.append(q3[i] - q1[i])
fliers = [item.get_ydata() for item in bplot1['fliers']]
lower_outliers = []
upper_outliers = []
for i in range(len(fliers)):
    lower_outliers_by_box = []
    upper_outliers_by_box = []
    for outlier in fliers[i]:
        if outlier < q1[i]:
            lower_outliers_by_box.append(round(outlier, 1))
        else:
            upper_outliers_by_box.append(round(outlier, 1))
    lower_outliers.append(lower_outliers_by_box)
    upper_outliers.append(upper_outliers_by_box)    
    
stats_list = [medians, means, minimums, maximums, q1, q3, IQRange, lower_outliers, upper_outliers]
stats_names = ['Median', 'Mean', 'Minimum', 'Maximum', 'Q1', 'Q3', 'IQR', 'Lower outliers', 'Upper outliers']
categories = ['Dynamic', 'Threshold','Periodic' ]
for i in range(len(categories)):
    print(f'\033[1m{categories[i]}\033[0m')
    for j in range(len(stats_list)):
        if len(stats_list[j]) == 0:
            print(f"{stats_names[j]}: 0")
        else:
            print(f'{stats_names[j]}: {stats_list[j][i]}')
    print('\n')

ttest_results3 = stats.ttest_rel(bp1auto, bp1threshold)
ttest_results2 = stats.ttest_rel(bp1periodic, bp1auto)
ttest_results1 = stats.ttest_rel(bp1periodic, bp1threshold)

print("Means and SEMs:")
print(f"Dynamic: {bp1auto.mean()}, {bp1auto.sem()}")
print(f"Threshold: {bp1threshold.mean()}, {bp1threshold.sem()}")
print(f"Periodic: {bp1periodic.mean()}, {bp1periodic.sem()}")

                  
print("Statistics for quality comparison:")
print(f'Periodic vs Threshold: {ttest_results1}')
print(f'Periodic vs Dynamic: {ttest_results2}')
print(f'Dynamic vs Threshold: {ttest_results3}\n')

#plot rate
mpl.rcParams.update(mpl.rcParamsDefault)
font = {'size'   : 22}
plot.rc('font', **font)
fig, ax = plot.subplots(figsize=(10, 10))

medianprops = dict(linestyle='-', linewidth=1, color='black')

bplot2 = ax.boxplot(x = [auto_df[auto_df.algo_setting == 0.95].groupby(['start_time','algo_setting','participant_ID']).mean(numeric_only = True).stim_rate.groupby('participant_ID').mean(),
                         threshold_df[threshold_df.algo_setting == 32].groupby(['start_time','algo_setting','participant_ID']).mean(numeric_only = True).stim_rate.groupby('participant_ID').mean(),
                         periodic_df[periodic_df.algo_setting == 12].groupby(['start_time','algo_setting','participant_ID']).mean(numeric_only = True).stim_rate.groupby('participant_ID').mean()
                         ],
                         notch=True,
                         vert=True,
                         patch_artist=True,
                         labels = labels,
                         medianprops=medianprops)
ax.set_ylabel("Rate (stims/min)")

# The spines
plot.setp(ax.spines.values(), linewidth=2)

# The ticks
ax.xaxis.set_tick_params(width=2)
ax.yaxis.set_tick_params(width=2)

ax.spines[['right', 'top']].set_visible(False)

# fill with colors
colors = ['#34A853', '#4285F4','#EA4335' ]
for patch, color in zip(bplot2['boxes'], colors):
    patch.set_facecolor(color)

plot.show()

# statistics

bp2periodic = periodic_df[periodic_df.algo_setting == 12].groupby(['start_time','algo_setting','participant_ID']).mean(numeric_only = True).stim_rate.groupby('participant_ID').mean()
bp2threshold = threshold_df[threshold_df.algo_setting == 32].groupby(['start_time','algo_setting','participant_ID']).mean(numeric_only = True).stim_rate.groupby('participant_ID').mean()
bp2auto = auto_df[auto_df.algo_setting == 0.95].groupby(['start_time','algo_setting','participant_ID']).mean(numeric_only = True).stim_rate.groupby('participant_ID').mean()

bplot2 = ax.boxplot(x = [bp2auto,
                         bp2threshold,
                         bp2periodic
                         ],
                         notch=True,
                         vert=True,
                         patch_artist=False)

medians = [round(item.get_ydata()[0], 5) for item in bplot2['medians']]
means = [round(item.get_ydata()[0], 5) for item in bplot2['means']]
minimums = [round(item.get_ydata()[0], 5) for item in bplot2['caps']][::2]
maximums = [round(item.get_ydata()[0], 5) for item in bplot2['caps']][1::2]
q1 = [round(min(item.get_ydata()), 5) for item in bplot2['boxes']]
q3 = [round(max(item.get_ydata()), 5) for item in bplot2['boxes']]
fliers = [item.get_ydata() for item in bplot2['fliers']]
lower_outliers = []
upper_outliers = []
IQRange = []
for i in range(len(q1)):
    IQRange.append(q3[i] - q1[i])
for i in range(len(fliers)):
    lower_outliers_by_box = []
    upper_outliers_by_box = []
    for outlier in fliers[i]:
        if outlier < q1[i]:
            lower_outliers_by_box.append(round(outlier, 1))
        else:
            upper_outliers_by_box.append(round(outlier, 1))
    lower_outliers.append(lower_outliers_by_box)
    upper_outliers.append(upper_outliers_by_box)    
    
stats_list = [medians, means, minimums, maximums, q1, q3, IQRange, lower_outliers, upper_outliers]
stats_names = ['Median', 'Mean', 'Minimum', 'Maximum', 'Q1', 'Q3','IQR', 'Lower outliers', 'Upper outliers']
categories = ['Dynamic', 'Threshold','Periodic' ]
for i in range(len(categories)):
    print(f'\033[1m{categories[i]}\033[0m')
    for j in range(len(stats_list)):
        if len(stats_list[j]) == 0:
            print(f"{stats_names[j]}: 0")
        else:
            print(f'{stats_names[j]}: {stats_list[j][i]}')
    print('\n')

ttest_results1 = stats.ttest_rel(bp2periodic, bp2threshold)
ttest_results2 = stats.ttest_rel(bp2periodic, bp2auto)
ttest_results3 = stats.ttest_rel(bp2auto, bp2threshold)

print("Means and SEMs:")
print(f"Dynamic: {bp2auto.mean()}, {bp2auto.sem()}")
print(f"Threshold: {bp2threshold.mean()}, {bp2threshold.sem()}")
print(f"Periodic: {bp2periodic.mean()}, {bp2periodic.sem()}")

print("Statistics for rate comparison:")
print(f'Periodic vs Threshold: {ttest_results1}')
print(f'Periodic vs Dynamic: {ttest_results2}')
print(f'Dynamic vs Threshold: {ttest_results3}\n')

# amount of threshold sessions with no stims:
noStims = threshold_df[threshold_df.algo_setting == 32].drop_duplicates(subset=['start_time'], keep='last')
noStimsResult = len(noStims[noStims.stim_rate == 0.0])/(len(noStims))*100
print(f'Percentage of sessions with no stims: {noStimsResult}')

# amount of threshold sessions with selectivity below 95%:
averageSelectivity = threshold_df[threshold_df.algo_setting == 32].groupby('start_time').mean(numeric_only = True)
averageSelectivityResult = len(averageSelectivity[averageSelectivity.selectivity < 95])/len(averageSelectivity)*100
print(f'Percentage of sessions below 95% selectivity: {averageSelectivityResult}')

# ISI calculation for sessions with stimulations (threshold)
ISI_results = threshold_df[threshold_df.algo_setting == 32].drop_duplicates(subset=['start_time'], keep='last')
ISI_results = ISI_results[~(ISI_results.stim_rate == 0.0)]
ISI_mean = ((1/ISI_results.stim_rate)*60).mean()
ISI_sem = ((1/ISI_results.stim_rate)*60).sem()
print(f'ISI for threshold sessions with stimulations: {ISI_mean} +/- {ISI_sem}')

# ISI calculation for sessions with stimulations (dynamic)
ISI_results = auto_df[auto_df.algo_setting == 0.95].drop_duplicates(subset=['start_time'], keep='last')
ISI_results = ISI_results[~(ISI_results.stim_rate == 0.0)]
ISI_mean = ((1/ISI_results.stim_rate)*60).mean()
ISI_sem = ((1/ISI_results.stim_rate)*60).sem()
print(f'ISI for dynamic sessions with stimulations: {ISI_mean} +/- {ISI_sem}')

# total number of exercises examined:
numOfExercises = len(auto_df[auto_df.algo_setting == 0.95].drop_duplicates(subset=['start_time'], keep='last'))
print(f'Total number of exercises examined: {numOfExercises}')

#plot supplementary figure
mpl.rcParams.update(mpl.rcParamsDefault)
font = {'size'   : 26}
plot.rc('font', **font)
plot.rcParams['font.sans-serif'] = "Myriad Pro"
fig, ax = plot.subplots(figsize=(15, 10))

threshold_df['selectivity'].replace(0, np.nan, inplace=True)
threshold_df['hist_sel'].replace(0, np.nan, inplace=True)

auto_df.algo_setting = auto_df.algo_setting*100
auto_df.algo_setting = auto_df.algo_setting.astype(int)

periodic_df = periodic_df[~(periodic_df.algo_setting == 20.0)]
threshold_df = threshold_df[~(threshold_df.algo_setting == 64)]
auto_df = auto_df[~(auto_df.algo_setting == 35)]

ax.errorbar(periodic_df.groupby(['participant_ID','algo_setting','start_time']).mean(numeric_only = True).groupby('algo_setting').mean().selectivity,
            periodic_df.groupby(['participant_ID','algo_setting','start_time']).mean(numeric_only = True).groupby('algo_setting').mean().stim_rate,
            xerr=periodic_df.groupby(['participant_ID','algo_setting','start_time']).mean(numeric_only = True).groupby('algo_setting').sem().selectivity,
            yerr=periodic_df.groupby(['participant_ID','algo_setting','start_time']).mean(numeric_only = True).groupby('algo_setting').sem().stim_rate,
            marker = 'o',
            markersize = 4,
            linestyle = 'solid',
            color = '#EA4335',
            linewidth = 2)
ax.errorbar(threshold_df.groupby(['participant_ID','algo_setting','start_time']).mean(numeric_only = True).groupby('algo_setting').mean().hist_sel,
            threshold_df.groupby(['participant_ID','algo_setting','start_time']).mean(numeric_only = True).groupby('algo_setting').mean().stim_rate,
            xerr=threshold_df.groupby(['participant_ID','algo_setting','start_time']).mean(numeric_only = True).groupby('algo_setting').sem().hist_sel,
            yerr=threshold_df.groupby(['participant_ID','algo_setting','start_time']).mean(numeric_only = True).groupby('algo_setting').sem().stim_rate,
            marker = 'o',
            markersize = 4,
            linestyle = 'solid',
            color = '#4285F4',
            linewidth = 2)
ax.errorbar(auto_df.groupby(['participant_ID','algo_setting','start_time']).mean(numeric_only = True).groupby('algo_setting').mean().selectivity,
            auto_df.groupby(['participant_ID','algo_setting','start_time']).mean(numeric_only = True).groupby('algo_setting').mean().stim_rate,
            xerr=auto_df.groupby(['participant_ID','algo_setting','start_time']).mean(numeric_only = True).groupby('algo_setting').sem().selectivity,
            yerr=auto_df.groupby(['participant_ID','algo_setting','start_time']).mean(numeric_only = True).groupby('algo_setting').sem().stim_rate,
            marker = 'o',
            markersize = 4,
            linestyle = 'solid',
            color = '#34A853',
            linewidth = 2)

for i, txt in enumerate(periodic_df.groupby(['participant_ID','algo_setting','start_time']).mean(numeric_only = True).groupby('algo_setting').mean().index):
    txt = str(txt) + " sec"
    ax.annotate(txt, (periodic_df.groupby(['participant_ID','algo_setting','start_time']).mean(numeric_only = True).groupby('algo_setting').mean().selectivity.iloc[i]+1,
                      periodic_df.groupby(['participant_ID','algo_setting','start_time']).mean(numeric_only = True).groupby('algo_setting').mean().stim_rate.iloc[i] - 0.08))

for i, txt in enumerate(threshold_df.groupby(['participant_ID','algo_setting','start_time']).mean(numeric_only = True).groupby('algo_setting').mean().index):
    txt = str(txt) + "x"
    ax.annotate(txt, (threshold_df.groupby(['participant_ID','algo_setting','start_time']).mean(numeric_only = True).groupby('algo_setting').mean().selectivity.iloc[i]-4,
                      threshold_df.groupby(['participant_ID','algo_setting','start_time']).mean(numeric_only = True).groupby('algo_setting').mean().stim_rate.iloc[i]-0.1))

for i, txt in enumerate(auto_df.groupby(['participant_ID','algo_setting','start_time']).mean(numeric_only = True).groupby('algo_setting').mean().index):
    txt = str(txt) + "%"
    ax.annotate(txt, (auto_df.groupby(['participant_ID','algo_setting','start_time']).mean(numeric_only = True).groupby('algo_setting').mean().selectivity.iloc[i]+1,
                      auto_df.groupby(['participant_ID','algo_setting','start_time']).mean(numeric_only = True).groupby('algo_setting').mean().stim_rate.iloc[i]))

ax.set_xlim(25,100)
ax.set_ylim(3,10.5)
# The spines
plot.setp(ax.spines.values(), linewidth=3)

# The ticks
ax.xaxis.set_tick_params(width=2)
ax.yaxis.set_tick_params(width=2)

ax.spines[['right', 'top']].set_visible(False)
ax.grid(alpha = 0.3)

ax.set_xlabel("Percent of max movement")
ax.set_ylabel("Rate (stims/min)")

ax.legend(labels)

plot.show()