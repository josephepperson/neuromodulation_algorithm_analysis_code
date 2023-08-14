#### ReTrieve Aggregate ####
# 
# Description
# - Functions that add to and/or modify existing data in dataframe
#
# Usage
# - Call modifier functions on dataframe, returns dataframe
# 
# Project: ReTrieve
# Author: Rachael Affenit Hudson
# Created: 03-27-2020
# Updated: 03-31-2020

from RePlayAnalysisCore3.Activities.ReTrieveAnalysisCore import rtvMeta
from RePlayAnalysisCore3.Activities.ReTrieveAnalysisCore import rtvHelpers
import numpy as np
import pandas as pd

# Functions to apply to individual df rows
def getSetDimension(row):
    """
    Add dimension for each row
    USAGE: Apply across column
    - RETURN: Dimension for the set in this row
    """
    if isinstance(row, int):
        #dimension = rtvMeta.setIdentificationByID.get(row, "UNKNOWN").Dimension
        dimension = next((x for x in rtvMeta.allSets if x.ID == row), "UNKNOWN")
    else:
        #dimension = rtvMeta.setIdentificationByID.get(row["setID"], "UNKNOWN").Dimension
        dimension = next((x for x in rtvMeta.allSets if x.ID == row["setID"]), "UNKNOWN")
    return dimension
def getSetUnits(row):
    """
    Add units for each set
    USAGE: Apply across column
    - RETURN: Units for the set in this row
    """
    if isinstance(row, int):
        #units = rtvMeta.setIdentificationByID.get(row, "UNKNOWN").Units
        units = next((x for x in rtvMeta.allSets if x.Units == row), "UNKNOWN")
    else:
        #units = rtvMeta.setIdentificationByID.get(row["setID"], "UNKNOWN").Units
        units = next((x for x in rtvMeta.allSets if x.Units == row["setID"]), "UNKNOWN")
    return units

# Dataframe modifier functions
def addMetadata(df):
    """
    Apply getDifficultyAlias(), getSetDimension(), and getSetUnits() to dataframe
    - RETURNS: Same dataframe with three new columns
    """
    # Set Dimension
    df["setDimension"] = df.apply(getSetDimension, axis=1)
    # Set Units
    df["setUnits"] = df.apply(getSetUnits, axis=1)
    return df
# TODO: Split up this function
def calcDatafileAggregates(participantData, df, allData):
    """
    Calculate performance and usage data for each ReTrieve data file, which can then be summed or averaged later.
    """

    # Initialize aggregate data columns
    colNames = {
        "UID",
        "DateTime",
        "Brain Injury",
        "Date",
        "Time",
        "Day",
        "Group",
        "Setting",
        "Set ID",
        "Set Name",
        "setNumObjects"
        "Difficulty",
        "Prescription",
        "trials",
        "retrievals",
        "numStims",
        "trialsPerMinEngaged",
        "trialsPerMinSearching",
        "retrievalsPerMinEngaged",
        "totalSearchTimeMinutes",
        "totalEngagedTimeMinutes",
        "percentEngagedTimeSearching",
        "percentCorrect",
        "percentError"
    }
    dfPerFile = pd.DataFrame(columns=colNames)

    # Count rows in new dataframe
    newDfRows = 0

    # For each row in the visit data spreadsheet
    for index, row in df.iterrows():

        rowUIDs = {str(row["UID"]), str(row["UID"])[1:]}
        if row["Group"] in rtvMeta.controlGroups:
            rowGroup = "Control"
        elif row["Group"] in rtvMeta.impairedGroups:
            rowGroup = "Impaired"
        else:
            print("WARNING: Group " + row["Group"] + " does not match any known groups.")
        
        # Find the matching UID in the dataframe of all data
        matching = allData[allData["UID"].isin(rowUIDs)]
        #matching = matching[matching["group"] == rowGroup]

        # Get all dates represented by this row
        if (not pd.isnull(row["Clinic Date"])) and (not rtvHelpers.isNaT(row["Clinic Date"])):
            drange = rtvHelpers.daterange(row["Clinic Date"], row["Clinic Date"])
        elif (
            (not pd.isnull(row["Start Date"]))
            and (not pd.isnull(row["End Date"]))
            and (not rtvHelpers.isNaT(row["Start Date"]))
            and (not rtvHelpers.isNaT(row["End Date"]))
        ):
            drange = rtvHelpers.daterange(row["Start Date"], row["End Date"])

        # For all dates represented by this visit data spreadsheet row
        for i, date in enumerate(drange):
            # Find the files with matching Date/UID/Group
            dt = matching[matching.date == date]

            # For all relevant sessions, add data to dataframe with matching metadata
            for fileIndex, matchingFile in dt.iterrows():
                if matchingFile.setName != "":
                    # Add known data for this file to our dataframe
                    try:
                        singleSession = pd.DataFrame(
                            {
                                "UID": [row["UID"]],
                                "DateTime": matchingFile.dateTime,
                                "Brain Injury": participantData[participantData["UID"] == row["UID"]][
                                    "Brain Injury"
                                ],
                                "Date": [date],
                                "Time": matchingFile.time,
                                "Day": [i + 1],
                                "Group": row["Group"],
                                "Setting": row["Setting"],
                                "Set ID": [matchingFile.setID],
                                "Set Name": [matchingFile.setName],
                                "setNumObjects": [matchingFile.setNumObjects],
                                "Difficulty": [matchingFile.setDiff],
                                "Prescription": [row["Prescription"]],
                                "trials": [matchingFile["numTaps"]],
                                "retrievals": [matchingFile["numObjectsReturned"]],
                                "numStims": [matchingFile["numStims"]],
                                "trialsPerMinEngaged": [0],
                                "trialsPerMinSearching": [0],
                                "retrievalsPerMinEngaged": [0],
                                "totalSearchTimeMinutes": [matchingFile["totalSearchTimeMinutes"]],
                                "totalEngagedTimeMinutes": [matchingFile["totalEngagedTimeMinutes"]],
                                "percentEngagedTimeSearching": [0],
                                "percentCorrect": [matchingFile["percentCorrect"]],
                                "percentError": [100-matchingFile["percentCorrect"]]
                            }
                        )
                    except ValueError:
                        print("ValueError: Array length 1 does not match index length 0")
                    dfPerFile = dfPerFile.append(singleSession, ignore_index=True)

                    # Increment row counter
                    newDfRows = newDfRows + 1

    # TODO: Identify and throw error on rows with "0" for either of the following values
    # Calculate remove zeros and fix units
    dfPerFile["totalSearchTimeMinutes"] = dfPerFile[dfPerFile["totalSearchTimeMinutes"] != 0].totalSearchTimeMinutes / 60.0  # Convert search time from seconds to minutes
    dfPerFile["totalEngagedTimeMinutes"] = dfPerFile[dfPerFile["totalEngagedTimeMinutes"] != 0].totalSearchTimeMinutes / 60.0  # Convert from seconds to minutes
    
    try:
        dfPerFile["trialsPerMinEngaged"] = dfPerFile["trials"].div(dfPerFile["totalEngagedTimeMinutes"]) # Trials/minute engaged
        dfPerFile["retrievalsPerMinEngaged"] = dfPerFile["retrievals"].div(dfPerFile["totalEngagedTimeMinutes"]) # Retrievals/minute
        dfPerFile["percentEngagedTimeSearching"] = dfPerFile["totalSearchTimeMinutes"].div(dfPerFile["totalEngagedTimeMinutes"]) * 100
    except ZeroDivisionError as error:
        print("Engaged Time = 0: ERROR " + str(error))

    try:
        dfPerFile["trialsPerMinSearching"] =  dfPerFile["trials"].div(dfPerFile["totalSearchTimeMinutes"]) # Trials/minute searching
    except ZeroDivisionError as error:
        print("Search Time = 0: ERROR " + str(error))

    # Convert completed columns to float
    dfPerFile["totalSearchTimeMinutes"] = dfPerFile["totalSearchTimeMinutes"].astype(float)
    dfPerFile["totalEngagedTimeMinutes"] = dfPerFile["totalEngagedTimeMinutes"].astype(float)
    dfPerFile["trialsPerMinEngaged"] = dfPerFile["trialsPerMinEngaged"].astype(float)
    dfPerFile["trialsPerMinSearching"] = dfPerFile["trialsPerMinSearching"].astype(float)
    dfPerFile["retrievalsPerMinEngaged"] = dfPerFile["retrievalsPerMinEngaged"].astype(float)
    dfPerFile["retrievals"] = dfPerFile["retrievals"].astype(float)
    dfPerFile["numStims"] = dfPerFile["numStims"].astype(float)

    return dfPerFile
def aggPerformanceBySession(df):
    groupKeys = [
        "UID", 
        "Brain Injury", 
        "Group", 
        "Setting",
        "Date",
        "Day",
        "Set ID",
        "Set Name", 
        "Difficulty",
        "setNumObjects"
    ]
    aggDict = {
        "trialsPerMinSearching": "mean",
        "percentCorrect": "mean",
        "percentError": "mean"
    }
    dfPerSet = (df.groupby(groupKeys).agg(aggDict).reset_index())
    return dfPerSet
def aggPerformanceBySet(df):
    groupKeys = [
        "UID", 
        "Brain Injury", 
        "Group", 
        "Setting",
        "Set ID",
        "Set Name", 
        "Difficulty",
        "setNumObjects"
    ]
    aggDict = {
        "trialsPerMinSearching": "mean",
        "percentCorrect": "mean",
        "percentError": "mean"
    }
    dfPerSet = (df.groupby(groupKeys).agg(aggDict).reset_index())
    return dfPerSet
def aggEventsByDay(df):
    groupKeys = [
        "UID", 
        "Brain Injury", 
        "Group", 
        "Setting", 
        "Date",
        "Day",
    ]
    aggDict = {
        "trialsPerMinSearching": "mean",
        "percentCorrect": "mean",
        "percentError": "mean",
        "trials": "sum",
        "retrievals": "sum",
        "numStims": "sum",
        "totalSearchTimeMinutes": "sum",
        "totalEngagedTimeMinutes": "sum",
    }
    dfPerDay = df.groupby(groupKeys).agg(aggDict).reset_index()
    return dfPerDay

if __name__ == "__main__":
    import doctest
    doctest.testmod()