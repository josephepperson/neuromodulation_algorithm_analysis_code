#### ReTrieve File Import ####
# 
# Description
# - Imports ReTrieve data from datafiles
# - Calculates useful performance metrics
# - Builds a dataframe from preprocessed data
#
# Usage
# - Reads and processes files from the local Retrieve_Files directory
# - Returns a fully functional dataframe to main script
# - Runs when loadPkl = false in retrieve-analysis-main.py
# 
# Project: ReTrieve
# Author: Rachael Affenit Hudson
# Created: 09-05-2019
# Updated: 03-31-2020

from RePlayAnalysisCore3.Activities.ReTrieveAnalysisCore import rtvMeta
from RePlayAnalysisCore3.Activities.ReTrieveAnalysisCore import rtvHelpers
from RePlayAnalysisCore3.Activities.ReTrieveAnalysisCore import rtvPreprocess

import json
import sys
import traceback
import doctest
import os
import glob
import filecmp as fc
import pandas as pd
import numpy as np
import numpy.ma as ma
import pathlib
import datetime as dt
import math
import re

# Load Data from Files
def loadVisitMetadata(excel_path):
    """
    Extract Visit info from participant excel sheet into dataframe
    - RETURNS: visit_df of meta information for each visit
    """

    excel_path = pathlib.Path(excel_path)
    visit_df = pd.read_excel(excel_path, "VisitMeta")  # Read from VisitMeta tab
    visit_df = visit_df[
        [
            "UID",
            "Group",
            "Setting",
            "Prescription",
            "Clinic Date",
            "Start Time",
            "End Time",
            "Start Date",
            "End Date",
        ]
    ]

    visit_df["UID"] = visit_df["UID"].astype(str)

    # Make sure date contains ONLY date, not time
    try:
        # Convert to datetime object if possible
        visit_df["clinicDatetime"] = pd.to_datetime(visit_df["Clinic Date"], errors="coerce")
        visit_df["startDatetime"] = pd.to_datetime(visit_df["Start Date"], errors="coerce")
        visit_df["endDatetime"] = pd.to_datetime(visit_df["End Date"], errors="coerce")

        # Remove any rows in which all dates are missing
        visit_df = visit_df.dropna(
            how="all", subset=["clinicDatetime", "startDatetime", "endDatetime"]
        )
        visit_df.reindex()

        # Reformat date and time columns to match
        visit_df["Clinic Date"] = visit_df["clinicDatetime"].dt.date
        visit_df["Start Date"] = visit_df["startDatetime"].dt.date
        visit_df["End Date"] = visit_df["endDatetime"].dt.date
        visit_df["Start Time"] = visit_df["Start Time"].apply(str)
        visit_df["Start Time"] = visit_df["Start Time"].apply(pd.to_datetime, errors="coerce")
        visit_df["End Time"] = visit_df["End Time"].apply(str)
        visit_df["End Time"] = visit_df["End Time"].apply(pd.to_datetime, errors="coerce")
        visit_df["Session Time (min)"] = (visit_df["End Time"] - visit_df["Start Time"]).astype(
            "timedelta64[m]"
        )
        visit_df["Start Time"] = visit_df["Start Time"].dt.time
        visit_df["End Time"] = visit_df["End Time"].dt.time
    except:
        print(
            "ERROR: An element in date/time columns of the Participant Reference Sheet is not a datetime"
        )

    # Filter out datetime columns
    visit_df = visit_df[
        [
            "UID",
            "Group",
            "Setting",
            "Prescription",
            "Clinic Date",
            "Session Time (min)",
            "Start Time",
            "End Time",
            "Start Date",
            "End Date",
        ]
    ]

    return visit_df
def loadParticipantMetadata(excel_path):
    """
    Extract Participant info from participant excel sheet into dataframe
    - RETURNS: df of meta information for each participant
    """

    excel_path = pathlib.Path(excel_path)
    df = pd.read_excel(excel_path, "ParticipantMeta")
    df = df[
        [
            "UID",
            "Gender",
            "Age",
            "Handedness",
            "Brain Injury",
            "Injury Type",
            "Date of Injury",
            "Tactile Severity",
        ]
    ]
    df["UID"] = df["UID"].astype(str)
    return df
def loadDataFromFile(filename):
    """
    Load data from a single JSON file into a dictionary
    - RETURN: data {} of file information

    >>> data = loadDataFromFile(os.path.join('Retrieve_Files','003','2019-07-30', '003_2019-07-30 11.40.00_impaired.json'))
    >>> print(data.keys())
    dict_keys(['Meta-Date', 'Meta-Set', 'Meta-Item-IDs', 'Meta-Sequence', 'Agg-TotalTime-s', 'Agg-SearchTime-s', 'Agg-SearchTimeAvg-s', 'Agg-PercentCorrect', 'Set-BlockSearchTime-s', 'Set-TapsRecorded-s', 'Set-StimTimes-s', 'Signal-HandTipTimes-s', 'Signal-Keys', 'Signal-HandDiff', 'Signal-BlockDiff', 'Signal-EventsRawKeys', 'Signal-EventsCondKeys', 'Signal-EventsRaw', 'Signal-EventsCond', 'Signal-HandTipLoc', 'Signal-HandSideLoc'])
    >>> print(data['Meta-Date'])
    2019-07-30 11.40.00
    >>> print(data['Meta-Set'])
    Intro: Find
    >>> print(data['Meta-Item-IDs'])
    [24]

    """
    data = {}
    try:
        with open(filename) as json_file:
            data = json.load(json_file)
    except OSError:
        print("ERROR: Could not access file " + filename)
        raise

    return data

def parseFilename (filename):
        tentative_datetime = None
        tentative_UID = None

        #Parse Date
        dateFormatIndex = 0
        dateString = ""
        for datetimeRegexFormat in rtvMeta.DATETIME_REGEX_FORMATS:
            try:
                dateString = re.search(datetimeRegexFormat, filename).group(0)
                tentative_datetime = rtvHelpers.stringToDatetime(dateString, rtvMeta.DATETIME_FORMATS[dateFormatIndex])
                break
            except Exception as e:
                dateFormatIndex = dateFormatIndex + 1
                pass

        #Parse UID
        try:
            tentative_UID = filename.partition(dateString)[0]
            tentative_UID = tentative_UID.rstrip('_')
        except Exception as e:
            print(str(e))

        return (tentative_datetime, tentative_UID)

# Build dataframe
def singleFileDataFrame(pathToFile, filename, index, dateDir, uid, date):
    """
    Create dataframe for a single file
    """
    # Extract patient and session information from filepath
    #filename = os.path.basename(file)
    name = os.path.splitext(filename)[0]  # filename without json
    splitName = name.split("_")
    if len(splitName) == 3:
        dateTime = splitName[1]
        time = dateTime.split(" ")[1]
    elif len(splitName) == 6 or len(splitName) == 5:
        dateTime = splitName[1] + "-" + splitName[2] + "-" + splitName[3] + " " + splitName[4]
        time = splitName[4]

    # Get the data for that file and extract the data
    unprocessedData = loadDataFromFile(pathToFile)
    print(name)

    # Clean our data for analysis
    cleanedData = rtvPreprocess.cleanDataForAnalysis(unprocessedData)
    if cleanedData == []:
        return pd.DataFrame()
    else:
        [
            setName,
            setID,
            setDiff,
            objectSearchTimes,
            numObjectsReturned,
            tapsRecorded,
            IDsequence,
            objectIDs,
            handLocTimes,
            Xloc,
            Yloc,
            ec,
            ecKeys,
            sessionTime,
            stimTimes,
            numStims,
        ] = cleanedData

    # Combine associated lists in to single objects
    eventsCondensed = {k: v for k, v in zip(ecKeys, ec)}
    handLoc = [(time, x, y) for time, x, y in zip(handLocTimes, Xloc, Yloc)]

    # Calculate Performance Metrics
    percentCorrect = 0
    try:
        percentCorrect = (np.count_nonzero(tapsRecorded) / numObjectsReturned) * 100
    except ZeroDivisionError:
        print("ERROR: numObjectsReturned = 0, cannot divide by zero; check your datafile")

    # Different date formats
    for datetimeFormat in rtvMeta.DATETIME_FORMATS:
        try:
            myDate = rtvHelpers.stringToDatetime(date, datetimeFormat).date()
        except Exception as e:
            pass

    # Write known data to dataframe
    myFile = pd.DataFrame.from_dict(
        {
            "UID": uid,
            "dateTime": dt.datetime.strptime(dateTime, "%Y-%m-%d %H.%M.%S"),
            "date": myDate,
            "time": dt.datetime.strptime(time, "%H.%M.%S").time(),
            "setID": setID,
            "setName": setName,
            "setDiff": setDiff,
            "setObjectIDs": [objectIDs],
            "setNumObjects": str(int(len(objectIDs))) + " Objects",
            "objectIDSequence": [IDsequence],
            "numObjectsReturned": [numObjectsReturned],
            "tapRecordedTimeStamps": [tapsRecorded],
            "numTaps": len(tapsRecorded),
            "numStims": numStims,
            "stimTimeStamps": [stimTimes],
            "searchTimeByObject": [objectSearchTimes],
            "percentCorrect": percentCorrect,
            "meanSearchTimeMinutes": np.nanmean(objectSearchTimes),
            "totalSearchTimeMinutes": np.sum(objectSearchTimes),
            "totalEngagedTimeMinutes": [sessionTime],
            "eventsCondensed": [eventsCondensed],
            "handLoc": [handLoc], # (time, x, y)
        }
    )

    return myFile
def buildSummaryDataFrame(maindir):
    """
    Build dataframe of session information from a directory full of Retrieve datafiles
    - RETURN: Raw dataframe of all session information
    """

    # Init dataframe
    colNames = {
        "UID",
        "dateTime",
        "date",
        "time",
        "setID",
        "setName",
        "setDiff",
        "setObjectIDs",
        "setNumObjects",
        "objectIDSequence",
        "numObjectsReturned",
        "tapRecordedTimeStamps",
        "numTaps",
        "numStims",
        "stimTimeStamps",
        "searchTimeByObject",
        "percentCorrect",
        "meanSearchTimeMinutes",
        "totalSearchTimeMinutes",
        "totalEngagedTimeMinutes",
        "eventsCondensed",
        "handLoc",
    }
    dataFrame = pd.DataFrame(columns=colNames)

    # Default UID
    uid = "00000"

    # Iterate through folders until we find one that matches
    allDirs = [x[0] for x in os.walk(maindir)]
    for subfolder in allDirs:
        # If this is the maindir, go to next
        if os.path.basename(subfolder) in rtvMeta.outerDirNames:
            continue
        # If we found a replay directory, go to next
        elif os.path.basename(subfolder) in rtvMeta.replayDirectories:
            continue
        # If we found an id directory, record id, initialize vars, and go to next
        elif not "-" in os.path.basename(subfolder) and not "_" in os.path.basename(subfolder):
            uid = os.path.basename(subfolder)
            #group = "xx"
            continue
        # If we found a date directory, process the files inside
        else:
            # For each date they trained
            date = os.path.basename(subfolder)

            # For each JSON file in this date directory, process it
            dateDir = os.path.join(maindir, uid, date)
            for dirpath, dirs, files in os.walk(dateDir):
                if "ReTrieve_Files" in dirs:
                    for dirpath, dirs, files in os.walk(os.path.join(dateDir, "ReTrieve_Files")):
                        files = [fi for fi in files if fi.endswith(".json")]
                        for filename in files:
                            myFile = singleFileDataFrame(
                                pathlib.PurePath(dirpath, filename), 
                                filename, 
                                len(dataFrame), 
                                dateDir, 
                                uid, 
                                date
                            )
                            if myFile.empty:
                                print("\tcleanDataForAnalysis() returned empty, skipping to next file")
                                continue
                            if pd.isnull(myFile["meanSearchTimeMinutes"][0]):
                                print("\tNO OBJECTS RETURNED DURING THIS SESSION. Skipping to next file")
                                continue
                            else:
                                dataFrame = dataFrame.append(myFile, ignore_index=True)
                else:
                    files = [fi for fi in files if fi.endswith(".json")]
                    for filename in files:
                        myFile = singleFileDataFrame(
                            pathlib.PurePath(dirpath, filename), 
                            filename, 
                            len(dataFrame), 
                            dateDir, 
                            uid, 
                            date
                        )
                        if myFile.empty:
                            print("\tcleanDataForAnalysis() returned empty, skipping to next file")
                            continue
                        if pd.isnull(myFile["meanSearchTimeMinutes"][0]):
                            print("\tNO OBJECTS RETURNED DURING THIS SESSION. Skipping to next file")
                            continue
                        else:
                            dataFrame = dataFrame.append(myFile, ignore_index=True)

    dataFrame["UID"] = dataFrame["UID"].astype(str)

    return dataFrame

if __name__ == "__main__":
    import doctest
    doctest.testmod()
