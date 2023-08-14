#### ReTrieve Figure Home ####
# 
# Description
# - Generate performance per day figures for home data
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

from RePlayAnalysisCore3.Activities.ReTrieveAnalysisCore import rtvMeta
from RePlayAnalysisCore3.Activities.ReTrieveAnalysisCore import rtvPalette
from RePlayAnalysisCore3.Activities.ReTrieveAnalysisCore import rtvFigureFormat
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np

# At Home Over Time
# TODO: Make this work for multiple participants as well
def homeLinePlotBase(df, performanceMeasure, useErrorBars, splitByDifficulty):
    if useErrorBars:
        myCI = 68
        myErrStyle = "bars"
    else:
        myCI = None
        myErrStyle = None

    if splitByDifficulty:
        myHue = "Difficulty"
    else:
        myHue = None

    # Make plot
    fig, axs = plt.subplots(
        nrows=1, 
        ncols=1, 
        figsize=rtvFigureFormat.FIG_SIZE_RECT,
    )

    lp = sns.lineplot(
        x="Day", 
        y=performanceMeasure.Key, 
        data=df, 
        hue=myHue, 
        marker="o", 
        ci=myCI, 
        err_style=myErrStyle,
        palette=rtvPalette.GreenYellow,
    )

    # Format subplot
    lp = rtvFigureFormat.formatSubplot(
        plot=lp, 
        title=performanceMeasure.Label + " at Home Per Day",
        xLabel="Day at Home",
        yLabel=performanceMeasure.Label + " " + performanceMeasure.Units,
        ylim=performanceMeasure.Max,
    )

    # Format figure
    fig = rtvFigureFormat.formatFigure(fig)

    return fig

# At Home Over Time
# TODO: Make this work for multiple participants as well
def homeBarPlotBase(df, performanceMeasure, useErrorBars, splitByDifficulty):
    if useErrorBars:
        myCI = 68
        myErrStyle = "bars"
    else:
        myCI = None
        myErrStyle = None

    if splitByDifficulty:
        myHue = "Difficulty"
        myPalette = rtvPalette.GreenYellow
    else:
        myHue = None
        myPalette = rtvPalette.Green

    # Make plot
    fig, axs = plt.subplots(
        nrows=1, 
        ncols=1, 
        figsize=rtvFigureFormat.FIG_SIZE_RECT,
    )

    lp = sns.barplot(
        x="Day", 
        y=performanceMeasure.Key, 
        data=df, 
        hue=myHue, 
        capsize=0.05,
        ci=68,
        palette=myPalette,
    )

    # Format subplot
    lp = rtvFigureFormat.formatSubplot(
        plot=lp, 
        title=performanceMeasure.Label + " at Home Per Day",
        xLabel="Day at Home",
        yLabel=performanceMeasure.Label + " " + performanceMeasure.Units,
        ylim=performanceMeasure.Max,
    )

    # Format figure
    fig = rtvFigureFormat.formatFigure(fig)

    return fig

if __name__ == "__main__":
    import doctest
    doctest.testmod()