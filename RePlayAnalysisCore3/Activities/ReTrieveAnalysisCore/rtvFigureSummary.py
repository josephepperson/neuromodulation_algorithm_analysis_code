#### ReTrieve Figure Summary ####
# 
# Description
# - Generate summary figures for clinic data
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

from RePlayAnalysisCore3.Activities.ReTrieveAnalysisCore import rtvPalette
from RePlayAnalysisCore3.Activities.ReTrieveAnalysisCore import rtvMeta
from RePlayAnalysisCore3.Activities.ReTrieveAnalysisCore import rtvHelpers
from RePlayAnalysisCore3.Activities.ReTrieveAnalysisCore import rtvFigureFormat
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import os
from PIL import Image
import PIL

# Event summary graphs
def eventBarGraphBase(df, performanceMeasure):

    fig, ax = plt.subplots(
        nrows=1, 
        ncols=1, 
        figsize=rtvFigureFormat.FIG_SIZE_SINGLE_BAR
    )

    result = (
        df.groupby(["UID"])[performanceMeasure.Key]
        .aggregate(np.median)
        .reset_index()
        .sort_values(performanceMeasure.Key)
    )

    bp = sns.barplot(
        data=result, 
        y=performanceMeasure.Key, 
        capsize=0.05, 
        ci=68, 
        palette=rtvPalette.Green,
    )

    bp = rtvFigureFormat.formatSubplot(
        plot=bp,
        title=performanceMeasure.Label,
        yLabel=performanceMeasure.Label + " " + performanceMeasure.Units,
        legend="invisible",
    )

    fig = rtvFigureFormat.formatFigure(fig)

    return fig
def eventSummaryBarGraph(dfFiltered, settingName):

    # Aggregate all entries by mean for this UID
    groupKeys = [
        "UID", 
    ]
    aggDict = {
        "trialsPerMinSearching": "mean",
        "percentCorrect": "mean",
        "percentError": "mean",
        "trials": "mean",
        "retrievals": "mean",
        "numStims": "mean",
        "totalSearchTimeMinutes": "mean",
        "totalEngagedTimeMinutes": "mean",
    }
    dfAggregate = dfFiltered.groupby(groupKeys).agg(aggDict).reset_index() # take the mean for each UID present
    dfAggregate["retrievalsPerHour"] = dfAggregate["retrievals"] / (dfAggregate["totalEngagedTimeMinutes"]/60.0)

    fig, ax = plt.subplots(
        nrows=1, 
        ncols=1, 
        figsize=rtvFigureFormat.FIG_SIZE_SQUARE_SMALL
    )

    unstacked = (
        dfAggregate[[event.Key for event in rtvMeta.usabilityMeasures]]
        .unstack()
        .to_frame()
    )
    bars = (
        tuple([event.Label for event in rtvMeta.usabilityMeasures])
    )

    # Prints out our averages and SDs 
    print("\n" + settingName + " Overview")
    print("==================================")
    print("Engaged Time Avg: " + str(np.mean(dfAggregate.totalEngagedTimeMinutes)))
    print("Engaged Time SD: " + str(np.std(dfAggregate.totalEngagedTimeMinutes)))
    print("Retrievals Per Day Avg: " + str(np.mean(dfAggregate.retrievals)))
    print("Retrievals Per Day SD: " + str(np.std(dfAggregate.retrievals)))
    print("Retrievals Per Hour Avg: " + str(np.mean(dfAggregate.retrievals)))
    print("Retrievals Per Hour SD: " + str(np.std(dfAggregate.retrievals)))
    print("Trials Avg: " + str(np.mean(dfAggregate.trials)))
    print("Trials SD: " + str(np.std(dfAggregate.trials)))
    print("Stims Avg: " + str(np.mean(dfAggregate.numStims)))
    print("Stims SD: " + str(np.std(dfAggregate.numStims)))

    bp = sns.barplot(
        y=unstacked[0], 
        x=unstacked.index.get_level_values(0), 
        ax=ax, 
        capsize=0.05, 
        ci=68,
        palette=rtvPalette.Green
    )

    bp = rtvFigureFormat.formatSubplot(
        plot=bp,
        title="Events Recorded " + settingName,
        tickLabelRotation=45,
        xTickLabels=bars,
        yLabel="Events",
        legend="invisible"
    )

    fig = rtvFigureFormat.formatFigure(fig)

    return fig

# Impaired performance compared to random
def impairedCompareToRandom(dfImpaired, performanceMeasure, includeSwarm):
    """
    BAR and overlaid SWARM chart for impaired performance difference from random performance
    """

    randomPerformanceTwoObjects = 50
    randomPerformanceThreeObjects = 33.3333333
    pvals = []

    # Add Random performance data to our dataframe
    dfImpaired = dfImpaired.append(
        {
            "Group": "Random",
            performanceMeasure.Key: randomPerformanceTwoObjects,
            "setNumObjects": "2 Objects",
        }, 
        ignore_index=True,
    )
    dfImpaired = dfImpaired.append(
        {
            "Group": "Random",
            performanceMeasure.Key: randomPerformanceThreeObjects,
            "setNumObjects": "3 Objects",
        }, 
        ignore_index=True,
    )

    # Make figure
    fig, axs = plt.subplots(
        nrows=1, 
        ncols=1, 
        figsize=rtvFigureFormat.FIG_SIZE_SQUARE_SMALL, 
    )

    # Make plot
    # TODO: Add p-value annotations
    bp = sns.barplot(
        x="setNumObjects",
        y=performanceMeasure.Key,
        hue="Group",
        order=["2 Objects", "3 Objects"],
        data=dfImpaired,
        capsize=0.05,
        ci=68,
        palette=rtvPalette.Random,
    )

    # left, right = bp.get_xlim()
    # if performanceMeasure.Label == rtvMeta.PERCENT_CORRECT.Label:
    #     bp.axhline(50, left, right, color="black")
    #     bp.axhline(33, left, right, color="black")

    # If we want a swarm plot as well, add it on top of the bar plot
    if includeSwarm:
        sp = sns.swarmplot(
            x="setNumObjects",
            y=performanceMeasure.Key,
            hue="Group",
            order=["2 Objects", "3 Objects"],
            data=dfImpaired,
            color="k",
            dodge=True,
            alpha=0.9,
        )
        sp.legend().remove()

    # Formatting
    bp = rtvFigureFormat.formatSubplot(
        plot=bp, 
        xLabel="",
        yLabel=performanceMeasure.Label + " " + performanceMeasure.Units,
        title="Percent Correct vs. Random",
        ylim=100,
        legend="invisible",
    )

    # Format figure
    fig = rtvFigureFormat.formatFigure(fig)

    return plt

# Grid of VNS hand images
def vnsImageGrid(path):
    listing = os.listdir(path)  # glob.glob('*.jpeg')
    npath = []
    im = []
    for infile in listing:
        im.append(infile)
        npath.append(os.path.join(path, infile))
    width = 300
    height = 400
    gridWidth = 20
    gridHeight = 5
    new_im = Image.new("RGB", (width * gridWidth, height * gridHeight))

    for i in range(gridWidth):
        for j in range(gridHeight):
            try:
                filepath = npath.pop(0)
            except IndexError:
                break
            im = Image.open(filepath)
            im.thumbnail((width, height))

            # paste the image at location i,j
            new_im.paste(im, (i * width, j * height))
        else:
            continue  # executed if inner loop ended normally (no break)
        break  # executed if 'continue' was skipped (break occurred)

    fig, ax = plt.subplots(figsize=(gridWidth, gridHeight))
    ax.imshow(new_im, interpolation="nearest")
    plt.tight_layout()
    return plt

# Heat map of hand locs
def handLocHeatMap(rawData):
    """
    Generate heat map of hand locations for impaired and unimpaired hand of BI participants
    """
    ## TODO: Make this work
    x = rtvHelpers.flatten(rawData.x)
    y = rtvHelpers.flatten(rawData.y)
    sns.jointplot(x=x, y=y, data=rawData, kind="kde")
    plt.title("All Data Heat Map")
    return plt

if __name__ == "__main__":
    import doctest
    doctest.testmod()