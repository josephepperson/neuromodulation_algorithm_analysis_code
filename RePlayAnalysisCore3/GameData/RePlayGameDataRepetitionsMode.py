from mongoengine import *
import os
import struct
import time
import itertools
import hashlib
import numpy as np
import pandas
from datetime import datetime
from datetime import timedelta
from pathlib import Path
from py_linq import Enumerable

from RePlayAnalysisCore3.CustomFields.CustomFields import *
from RePlayAnalysisCore3.GameData.RePlayGameData import RePlayGameData
from RePlayAnalysisCore3.DataFiles.RePlayDataFileStatic import RePlayDataFileStatic
from RePlayAnalysisCore3.RePlayExercises import RePlayExercises
from RePlayAnalysisCore3.RePlayExercises import RePlayDevice

class RePlayGameDataRepetitionsMode(RePlayGameData):

    repetitions_mode_file_version = IntField()
    start_time = DateTimeField()
    rep_start_time = ListField(DateTimeField())
    end_of_attempt_time = ListField(DateTimeField())

    signal_transformed = ListField(FloatField())
    signal_not_normalized = ListField(FloatField())

    target_rep_count = IntField()
    starting_hit_threshold = FloatField()
    hit_threshold = ListField(FloatField())
    return_threshold = FloatField()
    threshold_type = StringField()
    minimum_trial_duration = FloatField()    

    is_session_handedness_known = BooleanField()
    is_session_left_handed = BooleanField()
    
    should_convert_signal_to_velocity = IntField()
    is_single_polarity = IntField()
    should_force_alternation = IntField()

    #region Constructor

    def __init__(self, *args, **values):
        super().__init__(*args, **values)

    #endregion

    #region Methods that typically only called when loading the session from the data file.

    def ReadGameData(self, file_path, file_name, data_start_location):
        self.filepath = file_path
        self.filename = file_name
        self.__data_start_location = data_start_location

        self.start_time = datetime.min
        self.rep_start_time = []
        self.hit_threshold = []
        self.signal = []
        self.signal_not_normalized = []
        self.signal_time = []
        self.signal_timenum = []
        self.signal_timeelapsed = []
        self.is_session_handedness_known = False
        self.is_session_left_handed = False        

        rep_values= []
        rep_timestamps = []
        rep_timeelapsed = []
        rep_time = []

        self.end_of_attempt_time = []

        #Initialize the game file version to a default value
        self.repetitions_mode_file_version = 1
        
        #Create lists for rebaselining information
        self.rebaseline_time = []
        self.number_rebaseline_values = []
        self.rebaseline_values = []

        #Grab the file size in bytes
        flength = os.stat(self.filename).st_size

        with open(self.filename, 'rb') as f:

            f.seek(self.__data_start_location)
            try:
                #Modify this line when the replay games call the CloseFile method in the RepModeSaveGameData class
                while (f.tell() < flength - 8):

                    packet_type = RePlayDataFileStatic.read_byte_array(f, 'int')

                    #Packet 1 indicates metadata for a session
                    if packet_type == 1:
                        timenum_read = RePlayDataFileStatic.read_byte_array(f, 'float64')
                        self.start_time = RePlayDataFileStatic.convert_matlab_datenum_to_python_datetime(timenum_read)
                        self.repetitions_mode_file_version = RePlayDataFileStatic.read_byte_array(f, 'int')
                        self.target_rep_count = RePlayDataFileStatic.read_byte_array(f, 'int')
                        
                        temp_length = RePlayDataFileStatic.read_byte_array(f, 'int32')
                        self.threshold_type = f.read(temp_length).decode()

                        #Exercise sensitivity was only saved in replay V1, however it was always 1
                        if self.repetitions_mode_file_version == 1:
                            temp_length = RePlayDataFileStatic.read_byte_array(f, 'int32')
                            # self.exercise_sensitivity = f.read(temp_length).decode()
                            _ = f.read(temp_length).decode()
                        
                        self.return_threshold = RePlayDataFileStatic.read_byte_array(f, 'double')
                        self.minimum_trial_duration = RePlayDataFileStatic.read_byte_array(f, 'double')

                        if self.repetitions_mode_file_version >= 4:
                            self.starting_hit_threshold = RePlayDataFileStatic.read_byte_array(f, 'double')
                            self.should_convert_signal_to_velocity = RePlayDataFileStatic.read_byte_array(f, 'uint8')
                            self.is_single_polarity = RePlayDataFileStatic.read_byte_array(f, 'uint8')
                            self.should_force_alternation = RePlayDataFileStatic.read_byte_array(f, 'uint8')
                        else:
                            self.starting_hit_threshold = float("NaN")
                            self.should_convert_signal_to_velocity = -1
                            self.is_single_polarity = -1
                            self.should_force_alternation = -1

                    #Packet 2 indicates gamedata packet
                    elif packet_type == 2:
                        if self.repetitions_mode_file_version >= 5:
                            timenum_read = RePlayDataFileStatic.read_byte_array(f, 'float64')
                            self.signal_timenum.append(RePlayDataFileStatic.convert_matlab_datenum_to_python_datetime(timenum_read))
                            self.signal_timeelapsed.append(self.signal_timenum[-1]-self.signal_timenum[0])
                            self.signal_time.append(self.signal_timeelapsed[-1].total_seconds())

                            self.signal.append(RePlayDataFileStatic.read_byte_array(f, 'double'))
                            self.signal_not_normalized.append(RePlayDataFileStatic.read_byte_array(f, 'double'))
                        elif self.repetitions_mode_file_version >= 3:
                            timenum_read = RePlayDataFileStatic.read_byte_array(f, 'float64')
                            self.signal_timenum.append(RePlayDataFileStatic.convert_matlab_datenum_to_python_datetime(timenum_read))
                            self.signal_timeelapsed.append(self.signal_timenum[-1]-self.signal_timenum[0])
                            self.signal_time.append(self.signal_timeelapsed[-1].total_seconds())

                            self.signal.append(RePlayDataFileStatic.read_byte_array(f, 'double'))
                        else:
                            timenum_read = RePlayDataFileStatic.read_byte_array(f, 'float64')
                            rep_timestamps.append(RePlayDataFileStatic.convert_matlab_datenum_to_python_datetime(timenum_read))
                            rep_timeelapsed.append(rep_timestamps[-1]-rep_timestamps[0])
                            rep_time.append(rep_timeelapsed[-1].total_seconds())

                            temp_read = RePlayDataFileStatic.read_byte_array(f, 'double')
                            rep_values.append(temp_read)

                    #Packet 3 indiciates rephead data
                    elif packet_type == 3:
                        timenum_read = RePlayDataFileStatic.read_byte_array(f, 'float64')
                        self.rep_start_time.append(RePlayDataFileStatic.convert_matlab_datenum_to_python_datetime(timenum_read))
                        self.hit_threshold.append(RePlayDataFileStatic.read_byte_array(f, 'double'))
                        
                        #In game file versions 1 and 2, the data was saved to the game data file as individual repetitions.
                        #Therefore, we simply must reconstruct the signal from each of these individual repetitions.
                        if self.repetitions_mode_file_version < 3:
                            if len(rep_values) > 0:
                                inter_rep_interval = 0
                                if (len(self.end_of_attempt_time) > 0):
                                    temp_isi = rep_timestamps[0] - self.end_of_attempt_time[-1]
                                    inter_rep_interval = temp_isi.total_seconds()

                                base_time_addon = inter_rep_interval
                                if (len(self.signal_time) > 0):
                                    base_time_addon = self.signal_time[-1] + inter_rep_interval
                                base_time_addon_timedelta = timedelta(seconds = base_time_addon)

                                rep_time = [(x + base_time_addon) for x in rep_time]
                                rep_timeelapsed = [(x + base_time_addon_timedelta) for x in rep_timeelapsed]

                                self.signal.extend(rep_values)
                                self.signal_timenum.extend(rep_timestamps)
                                self.signal_timeelapsed.extend(rep_timeelapsed)
                                self.signal_time.extend(rep_time)
                                self.end_of_attempt_time.append(rep_timestamps[-1])
                                
                            rep_values = []
                            rep_timestamps = []
                            rep_timeelapsed = []
                            rep_time = []

                    #Packet 4 indiciates rebaseline packet
                    elif packet_type == 4:
                        timenum_read = RePlayDataFileStatic.read_byte_array(f, 'float64')
                        self.rebaseline_time.append(RePlayDataFileStatic.convert_matlab_datenum_to_python_datetime(timenum_read))

                        number_rebaseline_values = RePlayDataFileStatic.read_byte_array(f, 'int')
                        self.number_rebaseline_values.append(number_rebaseline_values)

                        temp_baselines = []
                        for _ in itertools.repeat(None, number_rebaseline_values):
                            temp_baselines.append(RePlayDataFileStatic.read_byte_array(f, 'double'))

                        self.rebaseline_values.append(temp_baselines)

                    #Packet 5 indicates end of attempt packet 
                    elif packet_type == 5:
                        timenum_read = RePlayDataFileStatic.read_byte_array(f, 'float64')
                        self.end_of_attempt_time.append(RePlayDataFileStatic.convert_matlab_datenum_to_python_datetime(timenum_read))

                    #Packet 6 indicates the "handedness" of the session
                    elif packet_type == 6:
                        timenum_read = RePlayDataFileStatic.read_byte_array(f, 'float64')
                        is_left_handed_int8 = RePlayDataFileStatic.read_byte_array(f, 'int8')
                        self.is_session_handedness_known = True
                        self.is_session_left_handed = False
                        if (is_left_handed_int8 == 1):
                            self.is_session_left_handed = True
                        
                    else:
                        self.bad_packet_count = self.bad_packet_count + 1
                        if (self.bad_packet_count > 10):
                            self.aborted_file = True
                            print("Aborting file because bad packet count exceeded 10 bad packets.")
                            return

            except:
                print(f'\nGame Crash detected during read of file: {self.filepath.stem}')
                self.crash_detected = 1

        #Final clean-up work. This is necessary to catch the last data in the file that is not properly
        #handled in the if-else statement above (for game file versions < 3).
        if self.repetitions_mode_file_version < 3:
            if len(rep_values) > 0:
                inter_rep_interval = 0
                if (len(self.end_of_attempt_time) > 0):
                    temp_isi = rep_timestamps[0] - self.end_of_attempt_time[-1]
                    inter_rep_interval = temp_isi.total_seconds()

                base_time_addon = inter_rep_interval
                if (len(self.signal_time) > 0):
                    base_time_addon = self.signal_time[-1] + inter_rep_interval
                base_time_addon_timedelta = timedelta(seconds = base_time_addon)

                rep_time = [(x + base_time_addon) for x in rep_time]
                rep_timeelapsed = [(x + base_time_addon_timedelta) for x in rep_timeelapsed]                

                self.signal.extend(rep_values)
                self.signal_timenum.extend(rep_timestamps)
                self.signal_timeelapsed.extend(rep_timeelapsed)
                self.signal_time.extend(rep_time)
                self.end_of_attempt_time.append(rep_timestamps[-1])

    def DetermineSignal (self, replay_version_code, game_name, exercise_name, gain, sensitivity):
        #Create some default values
        self.signal_actual_units = "Unknown"
        self.signal_actual = []
        self.signal_transformed = []

        exercise_tuple = Enumerable(RePlayExercises.exercises).where(lambda x: x[0] == exercise_name).first_or_default()

        #RePlay version code 30 is the first version that was used in the Baylor SCI trial.
        if (exercise_tuple is not None) and hasattr(self, "signal_not_normalized"):
            is_force_exercise = exercise_tuple[2]
            device_used = exercise_tuple[1]

            #Set the value of signal actual and its units
            self.signal_actual = self.signal_not_normalized
            self.signal_actual_units = exercise_tuple[3]            

            #Now calculate the game signal
            debounce_list = []
            for s in self.signal_not_normalized:
                val = 0
                if game_name == "ReCheck":
                    debounce_list.append(s)
                    debounce_list = debounce_list[-10:]

                    if (len(debounce_list) >= 10):
                        if is_force_exercise:
                            val = np.nanmedian(debounce_list)
                        else:
                            val = np.nanmean(np.diff(debounce_list))
                else:
                    if device_used == RePlayDevice.ReCheck:
                        debounce_list.append(s * gain)
                    else:
                        debounce_list.append(s * gain / sensitivity)
                    debounce_list = debounce_list[-10:]
                    
                    if (len(debounce_list) >= 10):
                        if (exercise_name == "Flipping") or (exercise_name == "Supination"):
                            val = np.nanmean(np.diff(debounce_list))
                        else:
                            val = np.nanmedian(debounce_list)

                self.signal_transformed.append(val)

    #endregion

    #region Methods to get basic information about this session

    def GetDifficulty(self):
        #"Repetitions Mode" doesn't have a true difficulty setting. Therefore, we will simply return the "target" number of repetitions
        #that the participant was asked to complete. This will be representative of difficulty for now.
        result = 1
        if (hasattr(self, "target_rep_count")):
            result = self.target_rep_count
        return result
        
    def GetHandedness(self):
        #This method returns two boolean values.
        #The first value represents: is the handedness of this session known?
        #The second value represents: was the left hand used during this session? (This value is only valid if the handedness of the session is known)        
        if(hasattr(self, "is_session_handedness_known") and hasattr(self, "is_session_left_handed")):
            return (self.is_session_handedness_known, self.is_session_left_handed)
        else: 
            return (False, False)

    def GetGameSignal (self, use_real_world_units = True, parent_data_file = None):
        #This method returns the game signal to the caller.
        if hasattr(self, "signal_actual") and hasattr(self, "signal_transformed"):
            result_signal = []
            result_units = "Unknown"
            
            if (use_real_world_units):
                result_signal = self.signal_actual
                result_units = self.signal_actual_units
            else:
                result_signal = self.signal_transformed
                result_units = "Transformed game units"

            basis_time = None
            if (len(self.signal_timenum) > 0):
                basis_time = self.signal_timenum[0]

            return (result_signal, self.signal_time, result_units, basis_time)
        else:
            return super().GetGameSignal(use_real_world_units)

    #endregion

    #region Methods related to calculating or handling repetitions

    def _calculate_repetition_indices (self, repetition_timestamps):
        result_rep_start_idx = []
        result_repetition_count = 0

        if (repetition_timestamps is not None) and (len(repetition_timestamps) > 0):
            result_repetition_count = len(repetition_timestamps)

            current_rep_idx = 0
            for i in range(0, len(self.signal_timenum)):
                if (current_rep_idx < len(repetition_timestamps)):
                    if (self.signal_timenum[i] >= repetition_timestamps[current_rep_idx]):
                        result_rep_start_idx.append(i)
                        current_rep_idx += 1
                else:
                    break

        return (result_repetition_count, result_rep_start_idx)        

    def GetCorrespondingSignalIndexFromSecondsElapsed (self, seconds_elapsed):
        if (self.signal_timenum is not None) and (len(self.signal_timenum) > 0):
            new_rep_timestamp = self.signal_timenum[0] + timedelta(seconds=seconds_elapsed)
            return self.GetCorrespondingSignalIndexFromTimestamp(new_rep_timestamp)

    def GetCorrespondingSignalIndexFromTimestamp (self, signal_timestamp):
        result = float("NaN")
        for i in range(0, len(self.signal_timenum)):
            if (self.signal_timenum[i] >= signal_timestamp):
                result = i
                break
        
        return result

    #This method overrides the CalculateRepetitionData method on the RePlayGameData base class.
    #This method calculates repetition data specifically for Repetitions Mode and ReCheck game sessions.
    #It does this by fetching the repetition markers that are saved in the data files.
    def CalculateRepetitionData(self, exercise_name):
        return self._calculate_repetition_indices(self.rep_start_time)

    #This method re-calculates repetition markers using the game signal for this Repetitions Mode or ReCheck game session.
    #In some cases for ReCheck the repetition markers may not match those that would have been calculated by Repetitions Mode.
    #For this reason, this function runs the exact same algorithm that would typically be run during gameplay by Repetitions Mode
    #to calculate new repetition markers.
    def RecalculateRepetitionMarkersUsingGameSignal (self, game_name, exercise_id, gain, standard_range, trim_parameter = None):
        verified_repetition_times = []

        #First, let's make sure we meet the necessary criteria to re-analyze the signal
        if ((hasattr(self, "signal_actual")) and 
            (hasattr(self, "signal_not_normalized")) and
            (hasattr(self, "signal_timenum")) and 
            (hasattr(self, "is_single_polarity")) and 
            (hasattr(self, "should_force_alternation")) and
            (hasattr(self, "should_convert_signal_to_velocity")) and
            (hasattr(self, "return_threshold")) and
            (hasattr(self, "minimum_trial_duration")) and
            (hasattr(self, "rep_start_time")) and
            (self.is_single_polarity > -1) and
            (self.should_force_alternation > -1) and
            (self.should_convert_signal_to_velocity > -1) and
            (len(self.signal_timenum) == len(self.signal_actual)) and
            (len(self.signal_timenum) == len(self.signal_not_normalized)) and
            (hasattr(self, "rebaseline_time")) and
            (len(self.rebaseline_time) > 0)):
            
            #This code will exactly mimic what happens in RePlay's Repetitions Mode.
            #First let's create some state variables

            exercise_name = exercise_id
            sensitivity = standard_range
            min_trial_duration_seconds = self.minimum_trial_duration

            exercise_tuple = Enumerable(RePlayExercises.exercises).where(lambda x: x[0] == exercise_name).first_or_default()
            device_used = exercise_tuple[1]

            #This function currently only supports ReCheck sessions
            if ((game_name == "ReCheck") and (device_used == RePlayDevice.ReCheck)):

                #These values are "hard-coded" values that work for the ReCheck devices only
                is_single_polarity = False
                should_force_alternation = True
                return_threshold = 20

                #Set up some state variables
                is_positive_trial = True
                current_trial_state = "Ready"
                debounce_list = []
                verified_repetition_times = []
                current_repetition_start_time = None
                current_trial_max_value_achieved = 0
                progress_to_next_state = False

                start_idx = 0
                end_idx = len(self.signal_actual)
                if (trim_parameter is not None):
                    if ("start" in trim_parameter):
                        start_idx = trim_parameter["start"]
                    if ("end" in trim_parameter):
                        end_idx = trim_parameter["end"]

                #Now let's loop through the signal sample-by-sample
                for i in range(start_idx, end_idx):
                    s = self.signal_not_normalized[i]
                    val = 0

                    if device_used == RePlayDevice.ReCheck:
                        debounce_list.append(s * gain)
                    else:
                        debounce_list.append(s * gain / sensitivity)
                    debounce_list = debounce_list[-10:]

                    if (len(debounce_list) >= 10):
                        if (exercise_name == "Flipping") or (exercise_name == "Supination"):
                            val = np.nanmean(np.diff(debounce_list))
                        else:
                            val = np.nanmedian(debounce_list)

                    #Now let's handle the current exercise value based on the current trial state
                    if (current_trial_state == "Ready"):
                        current_trial_max_value_achieved = val

                        if (is_single_polarity > 0):
                            if (val >= return_threshold):
                                progress_to_next_state = True
                        else:
                            if (should_force_alternation > 0):
                                if (((val >= return_threshold) and is_positive_trial) or 
                                    ((val <= -return_threshold) and not is_positive_trial)):

                                    progress_to_next_state = True
                            else:
                                if ((val >= return_threshold) or (val <= -return_threshold)):
                                    progress_to_next_state = True
                                    if (val >= 0):
                                        is_positive_trial = True
                                    else:
                                        is_positive_trial = False
                        
                        if (progress_to_next_state):
                            print(f"Set trial state to: In Progress at index {i}")
                            current_trial_state = "In Progress"
                            current_repetition_start_time = self.signal_timenum[i]

                    elif (current_trial_state == "In Progress"):
                        
                        if (abs(val) > current_trial_max_value_achieved):
                            current_trial_max_value_achieved = abs(val)
                        
                        crossed_return_threshold = False
                        if ((is_positive_trial and (val < return_threshold)) or 
                            ((not is_positive_trial) and (val > -return_threshold))):
                            crossed_return_threshold = True
                        
                        if (crossed_return_threshold):
                            current_time = self.signal_timenum[i]
                            offset_time = (current_time - current_repetition_start_time).total_seconds()
                            if (offset_time >= min_trial_duration_seconds):
                                idx_of_rep_start = self.GetCorrespondingSignalIndexFromTimestamp(current_repetition_start_time)
                                verified_repetition_times.append(idx_of_rep_start)
                                is_positive_trial = not is_positive_trial
                                current_trial_state = "Ready"
                                print(f"Set trial state to: Ready at index {i}. VERIFIED REP")
                            else:
                                current_trial_state = "Ready"
                                print(f"Set trial state to: Ready at index {i}.")
            
        return verified_repetition_times

    #endregion

