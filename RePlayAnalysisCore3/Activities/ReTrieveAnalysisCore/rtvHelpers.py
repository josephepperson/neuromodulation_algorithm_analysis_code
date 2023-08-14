#### ReTrieve Helpers ####
# 
# Description
# - Helper functions for analysis
#
# Usage
# - Call individual functions from other scripts
# 
# Project: ReTrieve
# Author: Rachael Affenit Hudson
# Created: 09-05-2019
# Updated: 03-31-2020

import os
import numpy as np
from datetime import datetime
import scipy.stats as stats
import RePlayAnalysisCore3.Activities.ReTrieveAnalysisCore.rtvFileImport
from RePlayAnalysisCore3.Activities.ReTrieveAnalysisCore import rtvMeta

# Identity Conversion Functions
def objectIDs2SetID(IDtuple):
    """ 
    Get set ID from objectIDs
    (Behavior is bizarre when there is only one item in the list- this is why we add NaN to single items)
    - RETURNS: setName (string)

    >>> objectIDs2SetName((3,1))
    Shapes Easy
    >>> objectIDs2SetName(tuple([3,1]))
    Shapes Easy
    >>> objectIDs2SetName(tuple([24]))
    "UNKNOWN SET"
    >>> objectIDs2SetName(tuple([24,np.nan]))
    "Intro: Find"
    >>> t = [5,20,26]
    >>> objectIDs2SetName(tuple(t))
    "Intro: Discriminate"
    """
    switcher = {
        (3, 1): (1, 1), # shapes easy
        (3, 4, 1): (1, 2), # shapes med
        (5, 4, 2): (1, 3), # shapes hard
        (5, 20, 26): (12, 2), # intro: disc
        (13, 15): (8, 1), # rods easy
        (13, 14, 15): (8, 2), # rods med
        (36, 14, 37): (8, 3), # rods hard
        (24, np.nan): (10, 1), # intro: find
        (24, 26): (7, 1), # rounded handles easy
        (24, 25, 26): (7, 2), # rounded handles med
        (39, 25, 40): (7, 3), # rounded handles hard
        (38, 21): (4, 1), # weight easy
        (38, 20, 21): (4, 2), # weight med
        (22, 20, 23): (4, 3), # weight hard
    }
    setIDDiff = switcher.get(IDtuple, "UNKNOWN SET")
    return setIDDiff
def setName2SetIDs(setName):
    """ 
    Get setID from setName
    - RETURNS: setID (int)

    >>> setName2SetIDs("Rods")
    8
    >>> setName2SetIDs("Intro: Find")
    10
    """
    setID = 0
    if "Shapes" in setName:
        setID = 1
    if "Handles" in setName:
        setID = 7
    if "Weight" in setName:
        setID = 4
    if "Rods" in setName:
        setID = 8
    if "Intro: Find" in setName:
        setID = 10
    if "Intro: Discriminate" in setName:
        setID = 12
    return setID
def identifySet(data):
    """ 
    Identify set name/difficulty/ID based on the objectIDs in a datafile
    - RETURNS: [setName, setID, setDiff]

    Old File Tests
    >>> data = rtvFileImport.loadDataFromFile(os.path.join('Z:', 'storage', 'Rachael', 'Data Backup ReTrieve', 'Usability','003','2019-07-30', '003_2019-07-30 11.40.00_impaired.json'))
    >>> [name, ID, difficulty] = identifySet(data)
    >>> print(name)
    Intro: Find
    >>> print(ID)
    10
    >>> print(difficulty)
    Easy

    Weird File Tests
    >>> data = rtvFileImport.loadDataFromFile(os.path.join('Z:', 'storage', 'Rachael', 'Data Backup ReTrieve', 'Usability','013','2019-12-09', '013_2019-12-09 18.20.31_impaired.json'))
    >>> [name, ID, difficulty] = identifySet(data)
    >>> print(name)
    Length
    >>> print(ID)
    8
    >>> print(difficulty)
    Easy

    New File Tests
    >>> data = rtvFileImport.loadDataFromFile(os.path.join('Z:', 'storage', 'Rachael', 'Data Backup ReTrieve', 'Usability', '013','2019-09-20', '013_2019-09-20 14.15.51_impaired.json'))
    >>> [name, ID, difficulty] = identifySet(data)
    >>> print(name)
    Weight
    >>> print(ID)
    4
    >>> print(difficulty)
    Hard
    """
    # Get set name (from metadata if present, or objectIDs if not)
    setID = None
    setDiff = None
    setName = ""
    objectIDs = data["Meta-Item-IDs"]
    if len(objectIDs) == 1:
        objectIDs.append(np.nan)

    # If metadata is recorded, use it
    if ("Meta-Set-Difficulty" in data) and ("Meta-Set" in data) and ("Meta-Set-ID" in data):
        setID = data["Meta-Set-ID"]
        setDiff = rtvMeta.difficultySwitcher.get(data["Meta-Set-Difficulty"], "Invalid Difficulty")

        if setDiff == "Invalid Difficulty":
            print("WARNING: Difficulty setting is invalid")

        if setID == "":
            print("WARNING: This file has EMPTY Meta-Set value. Identifying set from objectIDs")
            setIDDiff = objectIDs2SetID(tuple(objectIDs))
            setID = setIDDiff[0]
            setDiff = rtvMeta.difficultySwitcher.get(setIDDiff[1], "Invalid Difficulty")

    # If metadata NOT recorded, determine all set information from the objectIDs
    else:
        setIDDiff = objectIDs2SetID(tuple(objectIDs))
        setID = setIDDiff[0]
        setDiff = rtvMeta.difficultySwitcher.get(setIDDiff[1], "Invalid Difficulty")

    # Generate setName now that we have the correct setID
    setName = rtvMeta.getSetFromID(setID).Name

    if "UNKNOWN" in setName:
        print("WARNING: Object IDs " + objectIDs + " are not recognized by objectIDs2SetName()")

    

    return [setName, setID, setDiff]

# General Helpers
def removeZerosAndNegatives(lst):
    """
    Remove zeros and negatives from a list
    - RETURNS: filtered list
    """
    return [lst[i] for i in range(len(lst)) if (lst[i] != np.nan and lst[i] > 0)]
def removeNan(lst):
    """
    Remove NaN values from list
    - RETURNS: filtered list
    """
    return [x for x in lst if x != np.nan]
def isNaT(nat):
    """
    Is the passed value NaT?
    - RETURNS: True/False
    """
    return nat == np.datetime64("NaT")
def stringToDatetime(myString, datetimeFormat):
    return datetime.strptime(myString, datetimeFormat)
def datetimeToString(myDatetime, datetimeFormat):
    return myDatetime.strftime(datetimeFormat)
def daterange(date1, date2):
    """
    Create a date range from two dates
    - RETURNS: Range of dates that can be iterated using "for date in daterange:"
    """
    for n in range(int((date2 - date1).days) + 1):
        yield date1 + dt.timedelta(n)
def flatten(S):
    """
    Flatten a series of unpredictably deep nested lists into one list
    - RETURNS: A single list of elements in the passed nested list
    """
    if S == []:
        return S
    if isinstance(S[0], list):
        return flatten(S[0]) + flatten(S[1:])
    return S[:1] + flatten(S[1:])
def intersection(lst1, lst2): 
    """
    Returns the intersection of two lists
    """
    lst3 = [value for value in lst1 if value in lst2] 
    return lst3 
def createDirIfNecessary(filepath):
    """
    Create directories leading to the parameter filepath if they don't already exist
    """
    if not os.path.exists(filepath):
        os.mkdir(filepath)

if __name__ == "__main__":
    import doctest
    doctest.testmod()