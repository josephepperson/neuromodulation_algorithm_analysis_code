from mongoengine import *

import numpy as np
import os
import struct
import time
import itertools
import hashlib
import pandas
from datetime import datetime
from datetime import timedelta
from pathlib import Path

from RePlayAnalysisCore3.RePlaySignalAnalyzer import RePlaySignalAnalyzer
from RePlayAnalysisCore3.CustomFields.CustomFields import *

class RePlayGameData(Document):
    meta = {
        'allow_inheritance': True,
        'collection':'RePlayGameData',
        'strict':False
    }

    filepath = StringField()
    filename = StringField()
    difficulty = FloatField(default=0)

    signal = ListField(FloatField())
    signal_actual = ListField(FloatField())
    signal_actual_units = StringField()
    signal_time = ListField(FloatField())                   #Units/datatype: datatype is float, unit is in seconds
    signal_timeelapsed = ListField(TimedeltaField())        #Units/datatype: datatype is Python timedelta, represents seconds elapsed since start of session
    signal_timenum = ListField(DateTimeField())             #Units/datatype: datatype is a Python datetime object

    rebaseline_time = ListField(DateTimeField())
    number_rebaseline_values = ListField(IntField())
    rebaseline_values = ListField(DynamicField())

    vns_algorithm_is_frame_data_present = BooleanField(default=False)
    vns_algorithm_timenum = ListField(DateTimeField())      #Units/datatype: datatype is Python datetime object
    vns_algorithm_time = ListField(FloatField())            #Units/datatype: datatype is float, unit is in seconds
    vns_algorithm_should_trigger = ListField(IntField())
    vns_algorithm_signal_value = ListField(FloatField())
    vns_algorithm_positive_threshold = ListField(FloatField())
    vns_algorithm_negative_threshold = ListField(FloatField())
    vns_algorithm_timing_allows_trigger = ListField(IntField())    
    
    def __init__(self, *args, **values):
        super().__init__(*args, **values)

    #Empty shell of a function that will be inherited by child classes.
    #This function will tell the analysis code how to convert the signal
    #that was saved in the data file into 2 signals: the signal in 
    #real-world units and the signal in "game units".
    def DetermineSignal (self, replay_version_code, game_name, exercise_name, gain, sensitivity):
        pass

    #Empty shell of a function that will be inherited by child classes. 
    #This method will be used to read in game data for each individual game.
    def ReadGameData(self, file_path, file_name, data_start_location):
        pass

    #This method returns the difficulty level of the game.
    def GetDifficulty(self):
        result = 1
        if (hasattr(self, "difficulty")):
            if (isinstance(self.difficulty, list)):
                if (len(self.difficulty) > 0):
                    result = self.difficulty[0]
            else:
                result = self.difficulty        
        return result

    #This method returns whether the handedness was known for this game, as well as whether the left hand was used.
    def GetHandedness(self):
        #This method returns two boolean values.
        #The first value represents: is the handedness of this session known?
        #The second value represents: was the left hand used during this session? (This value is only valid if the handedness of the session is known)
        return (False, False)

    #This method returns the game signal to the caller.
    def GetGameSignal (self, use_real_world_units = True, parent_data_file = None):
        result_signal = []
        result_units = "Unknown"
        if (use_real_world_units) and hasattr(self, "signal_actual"):
            result_signal = self.signal_actual
        elif hasattr(self, "signal"):
            result_signal = self.signal
            
        basis_time = None
        if (len(self.signal_timenum) > 0):
            basis_time = self.signal_timenum[0]

        return (result_signal, self.signal_time, result_units, basis_time)

    #This method analyzes the game signal and determines where repetition markers should be placed
    def CalculateRepetitionData(self, exercise_name):
        result_rep_start_idx = []
        result_repetition_count = 0

        #Analyze the session data and plot the session signal
        if (hasattr(self, "signal_actual")):

            result_signal_actual = self.signal_actual
            result_signal_timestamps = self.signal_time

            try:
                signal_analyzer = RePlaySignalAnalyzer(
                    exercise_name, 
                    result_signal_actual, 
                    None, 
                    result_signal_timestamps)

                (result_rep_start_idx, _, _, _) = signal_analyzer.CalculateRepetitionTimes()
                result_repetition_count = len(result_rep_start_idx)
            except:
                pass    

        return (result_repetition_count, result_rep_start_idx)

        
