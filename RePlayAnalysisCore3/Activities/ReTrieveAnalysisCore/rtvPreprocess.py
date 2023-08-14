#### ReTrieve Preprocess ####
# 
# Description
# - Preprocessing functions used to clean data before assembly into a dataframe
#
# Usage
# - Call cleanDataForAnalysis() on dict{} extracted from a single retrieve datafile
# 
# Project: ReTrieve
# Author: Rachael Affenit Hudson
# Created: 03-27-2020
# Updated: 03-31-2020

from logging import exception
from RePlayAnalysisCore3.Activities.ReTrieveAnalysisCore import rtvMeta
from RePlayAnalysisCore3.Activities.ReTrieveAnalysisCore import rtvHelpers
import numpy as np

def hasMatchingTimestamp(objectReturnTimes, previousEventTime, thisEventTime, nextEventTime):
    """
    Determine if this tap event has a matching detected object
    - RETURNS: True/False
    """
    for eventIndex in range(len(objectReturnTimes)):
        if (
            (
                objectReturnTimes[eventIndex]
                <= thisEventTime + rtvMeta.sameEventTimeWindowInSeconds
            )
            and objectReturnTimes[eventIndex] <= nextEventTime
            and objectReturnTimes[eventIndex] + rtvMeta.sameEventTimeWindowInSeconds
            >= previousEventTime
        ):
            return True
    return False

def insertNewTimestamp(eventsCondensed, eventsCondensedKeys, newTimeStamp):
    """
    Inserts a timestamp at the indicated time in eventsCondensed and events
    - RETURNS: [eventsCondensed, eventsCondensedKeys]
    """
    # Add key to the list of keys, sort, then find its index
    eventsCondensedKeys.append(newTimeStamp)
    eventsCondensedKeys.sort()

    # Find the first timeIndex where we are greater than the undetected timeIndex, insert before
    inds = [i for i, v in enumerate(eventsCondensedKeys) if v == newTimeStamp]
    eventsCondensed.insert(inds[0], rtvMeta.OBJECT_RETURN_EVENT)
    return [eventsCondensed, eventsCondensedKeys]

def getPreviousAndNextTimestamp(correctReturnIndices, correctReturnTimes, timeIndex):
    """
    Given an index in return indices/times, find the previous and next event time
    - RETURNS: [previousEventTime, nextEventTime]
    """
    # Get the return indices before and after this one
    previousEventTime = correctReturnIndices[timeIndex] - 1
    nextEventTime = correctReturnIndices[timeIndex] + 1

    # Check that indices are within length of list
    if previousEventTime < 0:
        previousEventTime = 0.0  # Start at t=0 if this is the first object return
    else:
        previousEventTime = correctReturnTimes[previousEventTime]
    if nextEventTime > len(correctReturnTimes) - 1:
        nextEventTime = correctReturnTimes[len(correctReturnTimes) - 1] + 5.0
    else:
        nextEventTime = correctReturnTimes[nextEventTime]

    return [previousEventTime, nextEventTime]

def insertUndetectedObjects(eventsCondensed, eventsCondensedKeys, correctReturnTimes):
    """
    Insert objects that were undetected into eventsCondensed and eventsCondensed keys
    - RETURNS: [eventsCondensed, eventsCondensedKeys]
    """
    objectReturnIndices = [
        eventIndex
        for eventIndex, eventName in enumerate(eventsCondensed)
        if eventName == rtvMeta.OBJECT_RETURN_EVENT
    ]  # make each their own function
    objectReturnTimes = [eventsCondensedKeys[detected] for detected in objectReturnIndices]
    correctReturnTimes = [returnTime for returnTime in correctReturnTimes if returnTime > 0]
    correctReturnIndices = list(range(0, len(correctReturnTimes)))
    numObjectsReturned = len(objectReturnTimes)

    if len(correctReturnTimes) > 0:
        for timeIndex in range(len(correctReturnTimes)):

            [previousEventTime, nextEventTime] = getPreviousAndNextTimestamp(
                correctReturnIndices, correctReturnTimes, timeIndex
            )

            if not hasMatchingTimestamp(
                objectReturnTimes, previousEventTime, correctReturnTimes[timeIndex], nextEventTime
            ):
                [eventsCondensed, eventsCondensedKeys] = insertNewTimestamp(
                    eventsCondensed, eventsCondensedKeys, correctReturnTimes[timeIndex]
                )
                numObjectsReturned += 1
                print("\tAdded object event. New Total = " + str(numObjectsReturned))

    return [eventsCondensed, eventsCondensedKeys]

def cleanDataForAnalysis(data):
    """
    Clean data from this datafile and format for dataframe
    - RETURNS: all elements to be packed into the dataframe
    """
    # Extract data from datafile object
    try:
        correctReturnTimes = data["Set-TapsRecorded-s"]
        timeSearchingForObject = data["Set-BlockSearchTime-s"]
        objectIDs = data["Meta-Item-IDs"]
        objectSequence = data["Meta-Sequence"]
        objectIDSequence = [objectIDs[i - 1] for i in objectSequence]
        totalSessionTime = data["Agg-TotalTime-s"]
        stimulationTimes = data["Set-StimTimes-s"]
        numStimulations = len(data["Set-StimTimes-s"])
    except KeyError:
        print("\tERROR: Expected key not found in file- skipping to next file")
        return []

    try:
        eventsCondensed = data["Signal-EventsCond"]
        eventsCondensedKeys = data["Signal-EventsCondKeys"]
    except KeyError:
        print("\tERROR: Event data not found in this file- skipping to next file")
        return []

    try:
        handLocTimes = data["Set-HandTipTimes-s"]
        handYloc = data["Signal-HandTipLoc"]
        handXloc = data["Signal-HandSideLoc"]
    except KeyError:
        print(
            "\tHand location data not found for this file- continuing with empty location data"
        )
        handLocTimes = []
        handYloc = []
        handXloc = []    

    # Clean up our data
    timeSearchingForObject = rtvHelpers.removeZerosAndNegatives(timeSearchingForObject)
    [setName, setID, setDiff] = rtvHelpers.identifySet(data)
    [eventsCondensed, eventsCondensedKeys] = insertUndetectedObjects(
        eventsCondensed, eventsCondensedKeys, correctReturnTimes
    )
    objectIDs = rtvHelpers.removeNan(objectIDs)

    # Calculate number of objects returned for search time and percent correct
    objectReturnIndices = [
        eventIndex
        for eventIndex, eventName in enumerate(eventsCondensed)
        if eventName == rtvMeta.OBJECT_RETURN_EVENT
    ]
    objectReturnTimes = [eventsCondensedKeys[i] for i in objectReturnIndices]
    numObjectsReturned = len(objectReturnTimes)
    print("\tObjects Returned = " + str(numObjectsReturned))

    # Are there too many tap events?
    if np.count_nonzero(correctReturnTimes) > 12:
        print("WARNING: More taps recorded than objects in sequence")

    # Are there not enough object return events?
    if numObjectsReturned < np.count_nonzero(correctReturnTimes):
        print(
            "WARNING: More taps recorded than objects returned ("
            + str(np.count_nonzero(correctReturnTimes))
            + " > "
            + str(numObjectsReturned)
            + ")"
        )

    return [
        setName,
        setID,
        setDiff,
        timeSearchingForObject,
        numObjectsReturned,
        correctReturnTimes,
        objectIDSequence,
        objectIDs,
        handLocTimes,
        handXloc,
        handYloc,
        eventsCondensed,
        eventsCondensedKeys,
        totalSessionTime,
        stimulationTimes,
        numStimulations,
    ]

if __name__ == "__main__":
    import doctest
    doctest.testmod()