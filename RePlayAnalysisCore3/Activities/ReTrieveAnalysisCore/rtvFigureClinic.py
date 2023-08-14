#### ReTrieve Figure Clinic ####
# 
# Description
# - Generate Group or Individual performance comparison figures from clinic data
#
# Usage
# - Format the dataframe for the function
# - Pass it to the function
# - Function returns a plt object
# 
# Project: ReTrieve
# Author: Rachael Affenit Hudson
# Created: 03-27-2020
# Updated: 03-31-2020

from matplotlib.pyplot import legend
from RePlayAnalysisCore3.Activities.ReTrieveAnalysisCore import rtvMeta
from RePlayAnalysisCore3.Activities.ReTrieveAnalysisCore import rtvPalette
from RePlayAnalysisCore3.Activities.ReTrieveAnalysisCore import rtvHelpers
from RePlayAnalysisCore3.Activities.ReTrieveAnalysisCore import rtvFileImport
from RePlayAnalysisCore3.Activities.ReTrieveAnalysisCore import rtvAggregate
from RePlayAnalysisCore3.Activities.ReTrieveAnalysisCore import rtvFigureFormat
import seaborn as sns
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import math
import warnings
import itertools
import six
import os

# TODO: MAKE THIS A FUNCTION
        # Write Datapoints and P-Values to file
        # with open("avgs-pvals.txt", "a") as file:
        #     c = performancePerSet[performancePerSet["Group"] == "Control"]
        #     i = performancePerSet[performancePerSet["Group"] == "Impaired"]
        #     for myset in rtvMeta.difficultyOrder:
        #         file.write(setName + " " + performanceMeasure.Label + " " + myset + "\n")
        #         cc = c[c["Difficulty"] == myset]
        #         ii = i[i["Difficulty"] == myset]
        #         file.write("\tControl Datapoints [" + ", ".join(map(str, cc[performanceMeasure.Key])) + "]\n")
        #         file.write("\tImpaired Datapoints [" + ", ".join(map(str, ii[performanceMeasure.Key])) + "]\n")
        #         # file.write("\tP-Vals [" + ', '.join(map(str,pvals)) + "]\n")

# Compare Group performance in clinic
def groupPerformanceBySetDifficulty(performancePerSet, comparisonType, includeSwarm):
    """
    BAR/SWARM chart of given performance metric for given setName by difficulty. Groups are represented by hue.
    """

    fig, axs = plt.subplots(
        nrows = int(len(rtvMeta.oldSetIDOrder)/2) + len(rtvMeta.performanceMeasures), 
        ncols = len(rtvMeta.performanceMeasures), 
        figsize = rtvFigureFormat.FIG_SIZE_LARGE_TALL, 
        sharey = False, #determines whether to show the y-axis on both left and right
    )

    for i, (ax, (rtvSet, performanceMeasure)) in enumerate(zip(axs.flatten(), rtvMeta.allSetPerformanceOrder)):

        performanceOnMySet = performancePerSet[performancePerSet["Set ID"] == rtvSet.ID]

        # Make barplot
        bp = sns.barplot(
            x="Difficulty",
            y=performanceMeasure.Key,
            hue="Group",
            order=rtvMeta.difficultyOrder,
            data=performanceOnMySet,
            ax=ax,
            capsize=0.05,
            ci=68,
            palette=rtvPalette.Triple,
        )
        legendString = "bar" if i>=6 else "invisible"

        # TODO: Fix legend!!!!

        # If we want a swarm plot as well, add it on top of the bar plot
        if includeSwarm:
            bp = sns.swarmplot(
                x="Difficulty",
                y=performanceMeasure.Key,
                hue="Group",
                order=rtvMeta.difficultyOrder,
                data=performanceOnMySet,
                ax=ax,
                color="k",
                dodge=True,
                alpha=0.9,
            )
            legendString = "swarm" if i>=6 else "invisible"
        
        bp = rtvFigureFormat.formatSubplot(
            plot=bp, 
            title=rtvSet.Name,
            yLabel=performanceMeasure.Label + " " + performanceMeasure.Units,
            ylim=performanceMeasure.Max,
            legend=legendString
        )

    # Format figure
    if comparisonType == rtvMeta.BETWEEN_HANDS: 
        myTitle = "Performance with Alternate and Impaired Hand"
    else:
        myTitle = "Performance with Healthy and Brain-Injured Participants"
    fig = rtvFigureFormat.formatFigure(
        fig,
        title=myTitle
    )

    return fig

def groupPairPointPlot(performancePerSet, performanceMeasure):
    # Create new column to represent setName + difficulty
    performancePerSet["Set"] = performancePerSet["Set Name"] + " " + performancePerSet["Difficulty"]

    sns.set_style(rtvPalette.background)
    g = sns.PairGrid(
        data=performancePerSet, 
        y_vars=performanceMeasure.Key,
        x_vars=["Group"]*12,
        hue="UID",
        height=5, 
        aspect=.5
    )
    g.map(sns.pointplot, scale=1.3, errwidth=4)

    return plt
def difficultySorted(performancePerSet, includeSwarm):
    # Create new column to represent setID + difficulty
    performancePerSet["Set"] = performancePerSet["Set Name"] + " " + performancePerSet["Difficulty"]
    controlPerformancePerSet = performancePerSet[performancePerSet.Group.isin(rtvMeta.controlGroups)] # Select control participants
    controlPerformancePerSet = controlPerformancePerSet[controlPerformancePerSet["Set Name"].isin(rtvMeta.oldSetNameOrder)] # Select core sets

    fig, axs = plt.subplots(
        nrows=1, 
        ncols=len(rtvMeta.performanceMeasures), 
        figsize=rtvFigureFormat.FIG_SIZE_WIDE,
    )

    for i, performanceMeasure in enumerate(rtvMeta.performanceMeasures):
        
        result = controlPerformancePerSet.groupby(["Set"])[performanceMeasure.Key].aggregate(np.mean).reset_index().sort_values(performanceMeasure.Key)

        bp = sns.barplot(
            x="Set",
            y=performanceMeasure.Key,
            data=controlPerformancePerSet,
            order=result["Set"],
            ax=axs[i],
            capsize=0.05,
            ci=68,
        )
        legendString = "bar"
        
        if includeSwarm:
            bp = sns.swarmplot(
                x="Set",
                y=performanceMeasure.Key,
                data=controlPerformancePerSet,
                order=result["Set"],
                ax=axs[i],
                color="k",
                dodge=True,
                alpha=0.9,
            )
            legendString = "swarm"
        
        bp = rtvFigureFormat.formatSubplot(
            plot=bp, 
            tickLabelRotation=90,
            xLabel="",
            yLabel=performanceMeasure.Label + " " + performanceMeasure.Units,
            ylim=performanceMeasure.Max,
            legend=legendString
        )

        # Set y-axis for percent correct
        # left, right = bp.get_xlim()
        # if performanceMeasure.Label == rtvMeta.PERCENT_CORRECT.Label:
        #     bp.axhline(50, left, right, color="black")
        #     bp.axhline(33, left, right, color="black")

    # Format figure
    fig = rtvFigureFormat.formatFigure(
        fig,
        title="Difficulty Sorted"
    )

    return plt
def difficultyScaling(performancePerSet, groups, includeSwarm):
    # Create new column to represent setName + difficulty
    performancePerSet["Set"] = performancePerSet["Set Name"] + " " + performancePerSet["Difficulty"]
    controlPerformancePerSet = performancePerSet[performancePerSet.Group.isin(groups)] # Select control participants

    fig, axs = plt.subplots(
        nrows=1, 
        ncols=len(rtvMeta.performanceMeasures), 
        figsize=rtvFigureFormat.FIG_SIZE_WIDE,
    )

    for i, performanceMeasure in enumerate(rtvMeta.performanceMeasures):

        bp = sns.barplot(
            x="Set Name",
            y=performanceMeasure.Key,
            hue="Difficulty",
            hue_order=rtvMeta.difficultyOrder,
            order=rtvMeta.oldSetNameOrder,
            data=controlPerformancePerSet,
            ax=axs[i],
            capsize=0.05,
            ci=68,
            palette=rtvPalette.DiffColors
        )
        legendString = "bar"

        # Swarm plot
        if includeSwarm:
            bp = sns.swarmplot(
                x="Set Name",
                y=performanceMeasure.Key,
                hue="Difficulty",
                hue_order=rtvMeta.difficultyOrder,
                order=rtvMeta.oldSetNameOrder,
                data=controlPerformancePerSet,
                ax=axs[i],
                color="k",
                dodge=True,
                alpha=0.9,
            )
            legendString = "swarm"

        bp = rtvFigureFormat.formatSubplot(
            plot=bp, 
            xTickLabels=rtvMeta.oldSetNameOrder, 
            tickLabelRotation=0,
            xLabel="",
            yLabel=performanceMeasure.Label + " " + performanceMeasure.Units,
            ylim=performanceMeasure.Max,
            legend=legendString
        )

        # Set y-axis for percent correct
        # left, right = bp.get_xlim()
        # if performanceMeasure.Label == rtvMeta.PERCENT_CORRECT.Label:
        #     bp.axhline(50, left, right, color="black")
        #     bp.axhline(33, left, right, color="black")

    # Format figure
    fig = rtvFigureFormat.formatFigure(
        fig,
        title="Difficulty Scaling"
    )

    return plt

# TODO: Apply this format to other figure functions
def individualPerformanceBySetDifficulty(performancePerSession, UID, includeSwarm, setting = None, dateRangeString = None, groupData = None):
    """
    BAR/SWARM chart of given performance metric for given setName by difficulty. Groups are represented by hue.
    """

    sns.set_style("whitegrid")

    fig, axs = plt.subplots(
        nrows = int(len(rtvMeta.oldSetIDOrder)/2) + len(rtvMeta.performanceMeasures), 
        ncols = len(rtvMeta.performanceMeasures), 
        figsize = rtvFigureFormat.FIG_SIZE_LARGE_TALL, 
    )

    groupKeys = [
        "Brain Injury", 
        "Group", 
        "Setting", 
        "Set Name",
        "setNumObjects"
    ]
    aggDict = {
        rtvMeta.TRIAL_RATE.Key: "mean",
    }
    aggByMean = performancePerSession.groupby(groupKeys).agg(aggDict).reset_index()
    maxMeanTrialRate = aggByMean[rtvMeta.TRIAL_RATE.Key].max() * 1.2
    legendString = "invisible"
    sampleBP = None

    # For each panel in this 8-panel figure
    # (2 performance measures wide x 4 sets long)
    for i, (ax, (rtvSet, performanceMeasure)) in enumerate(zip(axs.flatten(), rtvMeta.allSetPerformanceOrder)):

        performanceOnMySet = performancePerSession[performancePerSession["Set ID"] == rtvSet.ID]
        
        # If data does NOT exist, plot empty dataframe
        if (performanceOnMySet.empty):
            bp = sns.barplot(
                x="Difficulty",
                y=performanceMeasure.Key,
                hue="Group",
                order=rtvMeta.difficultyOrder,
                data=rtvMeta.emptyPlot(performanceMeasure.Key),
                ax=ax,
            )
            if i==7:
                sampleBP = bp
        
        # If data exists
        else:
            # Make barplot (if data exists)
            bp = sns.barplot(
                x="Difficulty",
                y=performanceMeasure.Key,
                hue="Group",
                order=rtvMeta.difficultyOrder,
                data=performanceOnMySet,
                ax=ax,
                capsize=0.05,
                ci=68,
                palette= rtvPalette.QuadIndWithGroup if groupData else rtvPalette.Triple
            )
            legendString = "outsideBar" if i==0 else "invisible"

            # If we want a swarm plot as well, add it on top of the bar plot
            if includeSwarm:
                bp = sns.swarmplot(
                    x="Difficulty",
                    y=performanceMeasure.Key,
                    hue="Group",
                    order=rtvMeta.difficultyOrder,
                    data=performanceOnMySet,
                    ax=ax,
                    color="k",
                    dodge=True,
                    alpha= 0.9
                )
                legendString = "outsideSwarm" if i==0 else "invisible"
        
        # Format regardless if data exists
        bp = rtvFigureFormat.formatSubplot(
            plot=bp, 
            axis=ax,
            title=rtvSet.Name,
            yLabel=performanceMeasure.Label + " " + performanceMeasure.Units,
            ylim= maxMeanTrialRate if performanceMeasure == rtvMeta.TRIAL_RATE else performanceMeasure.Max,
            gridlines=True,
            legend=legendString
        )

    # Build title based on options
    myTitle = "ReTrieve " + UID
    if setting is not None:
        myTitle = myTitle + " for " + setting
    if dateRangeString is not None:
        myTitle = myTitle + dateRangeString

    # Format figure
    fig = rtvFigureFormat.formatFigure(
        fig,
        refSubplot=sampleBP,
        title=myTitle,
        legend=legendString,
    )

    return fig

# CSV output
def writePrescriptionPerformanceToCSV(performancePerSession, prescription, filePath):
    result = performancePerSession[performancePerSession["Prescription"] == prescription]
    result.to_csv(os.path.join(filePath, prescription + "_Performance.csv"), index = False)

if __name__ == "__main__":
    import doctest
    doctest.testmod()