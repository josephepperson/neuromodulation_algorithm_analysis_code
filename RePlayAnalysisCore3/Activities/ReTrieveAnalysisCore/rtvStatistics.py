#### ReTrieve Helpers ####
# 
# Description
# - Statistical tests for dataframes of ReTrieve data
#
# Usage
# - Choose a test to run
# - Pass in the dataframe, group column, group label(s), and measure used to run the test
# 
# Project: ReTrieve
# Author: Rachael Affenit Hudson
# Created: 04-29-2020
# Updated: 04-29-2020

import scipy.stats as stats
import pandas as pd
import csv
import os
from RePlayAnalysisCore3.Activities.ReTrieveAnalysisCore import rtvMeta
from RePlayAnalysisCore3.Activities.ReTrieveAnalysisCore import rtvHelpers

STATS_CSV_FILE = "Statistics.csv"
SCRIPT_DIR = ""

def dfOneSampleTTest(df, measure, groupColumn, expLabel, popMean):
    """
    One Sample T-Test: compare data to population mean
    """
    exp = df[df[groupColumn] == expLabel].dropna()

    [t, p] = stats.ttest_1samp(
        exp[measure].tolist(),
        popMean.tolist(),
        nan_policy="omit"
    )

    if (len(t) > 1 or len(p) > 1):
        print ("STATS ERROR: One Sample T-Test returned more than one t or p value!")
        return ["Error", "Error"]
    else:
        return [t[0], p[0], len(exp)]

def dfIGTTest(df, measure, groupColumn, ctrlLabel, expLabel):
    """
    Independent-Groups T-Test for a dataframe
    """
    ctrl = df[df[groupColumn] == ctrlLabel].dropna()
    exp = df[df[groupColumn] == expLabel].dropna() 

    [t, p] = stats.ttest_ind(
        ctrl[measure].tolist(), 
        exp[measure].tolist(), 
        nan_policy="omit"
    ) 

    return [t, p, [len(ctrl), len(exp)]]

def dfPairedTTest(df, measure, groupColumn, beforeLabel, afterLabel, matchBy):
    """
    Paired t-test
    """
    # Separate into before and after
    before = df[df[groupColumn] == beforeLabel].dropna()
    after = df[df[groupColumn] == afterLabel].dropna()

    # Eliminate all rows that don't exist in both datasets
    common = before.merge(after, how="inner", on=matchBy)
    for match in matchBy:
        before = before[before[match].isin(common[match])]
        after = after[after[match].isin(common[match])]

    # Sort by UID
    before.sort_values(by=matchBy)
    after.sort_values(by=matchBy)

    # Run paired t-test
    [t, p] = stats.ttest_rel(
        before[measure].tolist(), 
        after[measure].tolist()
    )
    
    return [t, p, len(before)]

def correlation(col1, col2):
    r = stats.pearsonr(col1, col2)
    return r

def createStatsFile(scriptdir):
    SCRIPT_DIR = scriptdir
    with open(os.path.join(SCRIPT_DIR, STATS_CSV_FILE), "w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["Injury", "Group", "Performance Measure", "ReTrieve Set", "Test", "Comparison", "Sample Size (n)", "T-Statistic", "P-Value"])

def writeStatsRow(row):
    # Write row to csv file
    with open(os.path.join(SCRIPT_DIR, STATS_CSV_FILE), "a+", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(row)

def ttestPerformanceEasyHard(performancePerSet, injury, groupType):
    """
    Compare easy/hard performance on each set for this group
    Paired by UID
    """
    performancePerSet = performancePerSet[performancePerSet["Brain Injury"] == injury.Key]
    performancePerSet = performancePerSet[performancePerSet["Group"].isin(groupType)]
    for (rtvSet, performanceMeasure) in rtvMeta.allSetPerformanceOrder:
        thisSet = performancePerSet[performancePerSet["Set Name"] == rtvSet.Name]

        [t, p, n] = dfPairedTTest(
            thisSet, 
            performanceMeasure.Key, 
            "Difficulty", 
            "Easy", 
            "Hard",
            ["UID", "Set Name"]
        )
        
        writeStatsRow([
            injury.Label, 
            groupType[0],
            performanceMeasure.Label, 
            rtvSet.Name, 
            "Paired T-Test", 
            "Easy/Hard", 
            str(n),
            str(t), 
            str(p),
        ])

def ttestPerformanceControlImpaired(performancePerSet, injury):
    """
    Compare performance of control/impaired groups for given injury type
    Paired by UID
    """
    performancePerSet["Set"] = performancePerSet["Set Name"] + " " + performancePerSet["Difficulty"]
    performancePerSet = performancePerSet[performancePerSet["Brain Injury"] == injury.Key]
    for performanceMeasure in rtvMeta.performanceMeasures:
        for rtvSet in rtvMeta.allSetDiffs:
            thisSet = performancePerSet[performancePerSet["Set"] == rtvSet]
            groupLabels = thisSet.Group.unique()
            [t,p,n] = [0,0,0]

            try :
                [t, p, n] = dfPairedTTest(  
                    thisSet, 
                    performanceMeasure.Key, 
                    "Group", 
                    rtvHelpers.intersection(groupLabels, rtvMeta.controlGroups)[0], 
                    rtvHelpers.intersection(groupLabels, rtvMeta.impairedGroups)[0],
                    ["UID", "Set Name", "Difficulty"]
                )
            except:
                print("STATS ERROR: Index out of range")
            
            
            writeStatsRow([
                injury.Label,
                "N/A",
                performanceMeasure.Label,
                rtvSet,
                "Paired T-Test",
                "Control/Impaired",
                str(n),
                str(t), 
                str(p),
            ])

def ttestPerformanceRandom(performancePerSet):
    """
    Compare performance of impaired BI group to random accuracy
    """
    randomPerformanceTwoObjects = 50
    randomPerformanceThreeObjects = 33.333333
    performanceMeasure = rtvMeta.PERCENT_CORRECT
    
    # Filter data to impaired BI
    performancePerSet = performancePerSet[performancePerSet["Brain Injury"] == rtvMeta.BRAIN_INJURY.Key]
    dfImpaired = performancePerSet[performancePerSet["Group"].isin(rtvMeta.impairedGroups)]

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

    for numObjectsSetting in dfImpaired.setNumObjects.unique():
        # Filter
        selected = dfImpaired[dfImpaired["setNumObjects"] == numObjectsSetting]
        popMeanRandom = selected[selected["Group"] == "Random"]
        popMeanRandom = popMeanRandom[popMeanRandom["setNumObjects"] == numObjectsSetting]
        experimental = selected[selected["Group"] != "Random"]
        
        # Group data by UID
        groupKeys = [
            "UID",
            "setNumObjects"
        ]
        experimental = (experimental.groupby(groupKeys).agg({performanceMeasure.Key: "mean"}).reset_index())

        [t, p, n] = dfOneSampleTTest(
            experimental, 
            performanceMeasure.Key, 
            "setNumObjects", 
            numObjectsSetting, 
            popMeanRandom[performanceMeasure.Key],
        )

        writeStatsRow([
            rtvMeta.BRAIN_INJURY.Label,
            "Impaired",
            performanceMeasure.Label,
            "All",
            "One Sample T-Test",
            "Impaired/Random", 
            str(n),
            str(t), 
            str(p),
        ])

if __name__ == "__main__":
    import doctest
    doctest.testmod()