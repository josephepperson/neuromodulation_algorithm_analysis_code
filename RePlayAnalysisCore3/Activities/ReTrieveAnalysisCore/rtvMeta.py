
#### ReTrieve Resource ####
# 
# Description
# - Repository for all meta-information used to group and plot data
#
# Usage
# - Reference these data structures rather than using local variables or hardcoding strings
# 
# Project: ReTrieve
# Author: Rachael Affenit Hudson
# Created: 09-05-2019
# Updated: 03-31-2020

from enum import Enum
import numpy as np
import pandas as pd
import os

# Participant Spreadsheet References
USABILITY_DIR = "Z:/storage/Rachael/Data Backup ReTrieve/Usability"
SCI_DIR = "Z:/storage/Rachael/Data Backup ReTrieve/SCI"
INDIVIDUAL_DIR = "Z:/storage/Rachael/Data Backup ReTrieve/Individual"

# Possible Datetime Formats
DATETIME_FORMATS = [
    '%Y-%m-%d %H.%M.%S',
    '%Y_%m_%d %H.%M.%S',
    '%Y_%m_%d_%H.%M.%S',
]

DATETIME_REGEX_FORMATS = [
    r'\d{4}-\d{2}-\d{2} \d{2}.\d{2}.\d{2}',
    r'\d{4}_\d{2}_\d{2} \d{2}.\d{2}.\d{2}',
    r'\d{4}_\d{2}_\d{2}_\d{2}.\d{2}.\d{2}',
    
]

# Figure subfolders
figureSubfolders = [
    "groupBar",
    "groupBarPDF",
    "daySummary",
    "indBar",
    "indHome",
    "diffScale"
]

# Event constants
OBJECT_RETURN_EVENT = "BLOCK"
HAND_ENTER_EVENT = "HAND ENTER"
HAND_EXIT_EVENT = "HAND EXIT"
sameEventTimeWindowInSeconds = 0.3

# Performance measure components
class RetrieveSet(object):
    def __init__(self, ID, name, dimension, units):
        self.ID = ID
        self.Name = name
        self.Dimension = dimension
        self.Units = units

# Comparison types
BETWEEN_HANDS = "Between Hands"
BETWEEN_GROUPS = "Between Groups"

# Core sets
INTRO_FIND = RetrieveSet(10, "Intro: Find", "None", "")
INTRO_DISC = RetrieveSet(12, "Intro: Discriminate", "None", "")
LENGTH = RetrieveSet(8, "Length", "Length", "inches")
WEIGHT = RetrieveSet(4, "Weight", "Weight", "grams")
TEXTURE_ROUNDED = RetrieveSet(7, "Handles (Ro)", "Texture", "sq inches")
TEXTURE_SQUARED = RetrieveSet(15, "Handles (Sq End)", "Texture", "mm")
SHAPE = RetrieveSet(1, "Shapes", "Points", "points")
POLYGONS = RetrieveSet(13, "Polygons", "Sides", "sides")

allSets = {
    LENGTH,
    WEIGHT,
    TEXTURE_ROUNDED,
    TEXTURE_SQUARED,
    SHAPE,
    POLYGONS,
    INTRO_FIND,
    INTRO_DISC
}

def getSetFromID(id):
    return next((x for x in allSets if x.ID == id), None)

oldSetOrder = [
    LENGTH,
    WEIGHT,
    TEXTURE_ROUNDED,
    SHAPE
]

oldSetIDOrder = [
    LENGTH.ID,
    WEIGHT.ID,
    TEXTURE_ROUNDED.ID,
    SHAPE.ID
]

oldSetNameOrder = [
    LENGTH.Name,
    WEIGHT.Name,
    TEXTURE_ROUNDED.Name,
    SHAPE.Name
]

setIdentificationByID = {
    LENGTH.ID: LENGTH,
    WEIGHT.ID: WEIGHT,
    TEXTURE_ROUNDED.ID: TEXTURE_ROUNDED,
    TEXTURE_SQUARED.ID: TEXTURE_SQUARED,
    SHAPE.ID: SHAPE,
    POLYGONS.ID: POLYGONS
}

# Task difficulty levels
class DifficultyLevels(Enum):
    EASY = "Easy"
    MEDIUM = "Med"
    HARD = "Hard"

difficultySwitcher = {
    1: DifficultyLevels.EASY.value, 
    2: DifficultyLevels.MEDIUM.value, 
    3: DifficultyLevels.HARD.value
}

difficultyOrder = [
    DifficultyLevels.EASY.value,
    DifficultyLevels.MEDIUM.value,
    DifficultyLevels.HARD.value,
]

# Performance measure components
class RetrieveMeasure(object):
    def __init__(self, label, key, units, max):
        self.Label = label
        self.Key = key
        self.Units = units
        self.Max = max

# Injury class
class Injury(object):
    def __init__(self, label, key):
        self.Label = label
        self.Key = key

# Define injury types
BRAIN_INJURY = Injury("Brain Injury", "Y")
HEALTHY = Injury("Healthy", "N")

# Define measures
SEARCH_TIME = RetrieveMeasure("Search Time", "totalSearchTimeMinutes", "(min)", None)
PERCENT_CORRECT = RetrieveMeasure("Percent Correct", "percentCorrect", "", 100)
PERCENT_ERROR = RetrieveMeasure("Percent Error", "percentError", "", 100)
TRIAL_RATE = RetrieveMeasure("Trial Rate", "trialsPerMinSearching", "(/min)", None)
ENGAGED_TIME = RetrieveMeasure("Engaged Time", "totalEngagedTimeMinutes", "(min)", None)
RETRIEVALS = RetrieveMeasure("Retrievals", "retrievals", "", None)
STIMS = RetrieveMeasure("Mock Stimulations", "numStims", "", None)

# Define groups of measures
performanceMeasures = [TRIAL_RATE, PERCENT_CORRECT] # removed SEARCH_TIME for now
usabilityMeasures = [ENGAGED_TIME, RETRIEVALS, STIMS] # removed STIMS for now

# Combining sets and difficulties
allSetDiffs = [
    sn + " " + dl
    for sn in oldSetNameOrder
    for dl in difficultyOrder
]

# Combining set ids and dimensions
allSetnameDiffs = [
    sn + " " + dl
    for sn in oldSetNameOrder
    for dl in difficultyOrder
]

# Set and performance combined, sorted by performance
allSetPerformanceOrder = [
        (s, pm)
        for s in oldSetOrder
        for pm in performanceMeasures
]

# Define possible groups, and the label they have in datafiles
controlGroups = ["Control", "Alternate", "No Glove", "Healthy"]
impairedGroups = ["Impaired", "Glove", "Brain Injury"]

# Replay directories
outerDirNames = [
    "Retrieve_Files",
    "ReTrieve_Files",
    "ReTrieve_Photos",
]
replayDirectories = [
    "Breakout",
    "FruitArchery",
    "FruitNinja",
    "RepetitionsMode",
    "SpaceRunner",
    "TrafficRacer",
    "TyperShark",
]

# Define groups of prescriptions
telerehabPrescriptions = [
    "Rx A: Mild", 
    "Rx B: Severe", 
    "ReTrieve Telerehab: Training",
    "ReTrieve Telerehab: Full",
] 
clinicPrescriptions = [
    "Day 1",
    "Day 2: Mild",
    "Day 2: Severe",
    "Day 3",
    "ReTrieve Only",
]
    #sorted(
    #, key=lambda x: x[0].Name)

# Generate empty dataframe to plot
def emptyPlot(performanceKey):
    emptyPlotData = {
        "Group": [impairedGroups[0], impairedGroups[0], impairedGroups[0]],
        "Difficulty": [DifficultyLevels.EASY, DifficultyLevels.MEDIUM, DifficultyLevels.HARD],
        performanceKey: [0, 0, 0]
    }
    return pd.DataFrame(emptyPlotData, columns=["Group", "Difficulty", performanceKey])

if __name__ == "__main__":
    import doctest
    doctest.testmod()