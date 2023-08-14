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
import math
from py_linq import Enumerable
import uuid

from RePlayAnalysisCore3.CustomFields.CustomFields import *
from RePlayAnalysisCore3.GameData.RePlayGameData import RePlayGameData
from RePlayAnalysisCore3.DataFiles.RePlayDataFileStatic import RePlayDataFileStatic
from RePlayAnalysisCore3.RePlayExercises import RePlayExercises
from RePlayAnalysisCore3.RePlayExercises import RePlayDevice

class RePlayGameDataTrafficRacer(RePlayGameData):

    traffic_racer_file_version = IntField()
    replay_version_code = IntField()

    start_time = DateTimeField()
    session_duration = IntField()
    num_lanes = IntField()
    lane_width = FloatField()

    current_score = ListField(IntField())
    remaining_time = ListField(IntField())
    player_vehicle_info = ListField(DynamicField())
    num_vehicles = ListField(IntField())
    vehicle_info = ListField(DynamicField())
    traffic_info = ListField(DynamicField())
    num_coins = ListField(IntField())
    coin_info = ListField(DynamicField())
    highlighted_lane = ListField(IntField())
    crash_events = ListField(DateTimeField())
    restart_events = ListField(DateTimeField())
    coin_capture_events = ListField(DateTimeField())
    coin_capture_guids = ListField(StringField())
    coin_guids = ListField(StringField())

    #region Constructor

    def __init__(self, *args, **values):
        super().__init__(*args, **values)

    #endregion

    #region Methods used when loading the data into the database from the data file

    def DefineRePlayVersion(self, replay_version_code):
        try:
            self.replay_version_code = int(replay_version_code)
        except:
            self.replay_version_code = 0

    def ReadGameData(self, file_path, file_name, data_start_location):

        self.filepath = file_path
        self.filename = file_name
        self.__data_start_location = data_start_location

        self.start_time = datetime.min
        self.traffic_racer_file_version = 0
        self.difficulty = 0
        self.session_duration = 0
        self.num_lanes = 0
        self.lane_width = 0

        self.current_score = []
        self.remaining_time = []

        self.signal = []
        self.signal_time = []
        self.signal_timenum = []
        self.signal_timeelapsed = []
        
        self.player_vehicle_info = []
        self.num_vehicles = []
        self.vehicle_info = []
        self.traffic_info = []
        self.num_coins = []
        self.coin_info = []
        self.highlighted_lane = []
        
        #Create lists for rebaselining information
        self.rebaseline_time = []
        self.number_rebaseline_values = []
        self.rebaseline_values = []

        #Create an empty list of crash events
        self.crash_events = []

        #Create an empty list of re-start events
        self.restart_events = []

        #Create an empty list of coin capture events
        self.coin_capture_events = []

        #Create an empty list of guids of all coins that were captured by the player
        self.coin_capture_guids = []

        #Create an empty list of guids of ALL coins
        self.coin_guids = []
        
        #Grab the file size in bytes
        flength = os.stat(self.filename).st_size

        #We need to handle a bug in data files from ALL RePlay versions through VERSION CODE 31:
        if (self.replay_version_code <= 31):

            self.traffic_racer_file_version = 2
            if (self.replay_version_code < 25):
                self.traffic_racer_file_version = 1

            self.difficulty = 0.1
            self.num_lanes = 4
            self.lane_width = 5
        #End of code handling the bug

        with open(self.filename, 'rb') as f:
            f.seek(self.__data_start_location)
            try:
                while (f.tell() < flength - 4):

                    packet_type = RePlayDataFileStatic.read_byte_array(f, 'int')

                    #Packet 1 indicates metadata for a session
                    if packet_type == 1:
                        timenum_read = RePlayDataFileStatic.read_byte_array(f, 'float64')
                        self.start_time = RePlayDataFileStatic.convert_matlab_datenum_to_python_datetime(timenum_read)
                        self.traffic_racer_file_version = RePlayDataFileStatic.read_byte_array(f, 'int')
                        self.difficulty = RePlayDataFileStatic.read_byte_array(f, 'float')
                        self.session_duration = RePlayDataFileStatic.read_byte_array(f, 'int')
                        self.num_lanes = RePlayDataFileStatic.read_byte_array(f, 'int')
                        self.lane_width = RePlayDataFileStatic.read_byte_array(f, 'float')

                    #Packet 2 indicates gamedata
                    elif packet_type == 2:
                        timenum_read = RePlayDataFileStatic.read_byte_array(f, 'float64')
                        self.signal_timenum.append(RePlayDataFileStatic.convert_matlab_datenum_to_python_datetime(timenum_read))
                        self.signal_timeelapsed.append(self.signal_timenum[-1]-self.signal_timenum[0])
                        self.signal_time.append(self.signal_timeelapsed[-1].total_seconds())

                        self.current_score.append(RePlayDataFileStatic.read_byte_array(f, 'int'))
                        self.remaining_time.append(RePlayDataFileStatic.read_byte_array(f, 'double'))
                        self.signal.append(RePlayDataFileStatic.read_byte_array(f, 'float'))

                        #Bug fix for ALL TRAFFIC RACER GAME DATA FILES FROM ALL REPLAY VERSIONS THROUGH VERSION CODE 31
                        if (self.replay_version_code <= 31):
                            if (len(self.signal_timenum) == 1):
                                self.start_time = self.signal_timenum[0]
                            if (len(self.remaining_time) == 1):
                                self.session_duration = self.remaining_time[0]
                        #End of code handling the bug
                        
                        #store the position (x, y) and then the velocity (x, y) in to the player_veh list
                        player_veh = []
                        player_veh.append(RePlayDataFileStatic.read_byte_array(f, 'float'))
                        player_veh.append(RePlayDataFileStatic.read_byte_array(f, 'float'))
                        player_veh.append(RePlayDataFileStatic.read_byte_array(f, 'float'))
                        player_veh.append(RePlayDataFileStatic.read_byte_array(f, 'float'))

                        self.player_vehicle_info.append(player_veh)

                        #save out the vehicle information for the traffic
                        num_vehicles = RePlayDataFileStatic.read_byte_array(f, 'int')
                        self.num_vehicles.append(num_vehicles)
                        all_vehicles_info = []

                        for _ in itertools.repeat(None, num_vehicles):
                            each_veh_info = []
                            #body width, height, vehicle x pos, vehicle y pos, veh x velocity, veh y velocity
                            if (self.traffic_racer_file_version >= 2):
                                list_of_bytes = RePlayDataFileStatic.read_16byte_guid(f)                            
                                bytes_object = bytes(list_of_bytes)
                                guid_object = uuid.UUID(bytes_le = bytes_object)
                                guid_str = str(guid_object)
                            each_veh_info.append(RePlayDataFileStatic.read_byte_array(f, 'float'))
                            each_veh_info.append(RePlayDataFileStatic.read_byte_array(f, 'float'))
                            each_veh_info.append(RePlayDataFileStatic.read_byte_array(f, 'float'))
                            each_veh_info.append(RePlayDataFileStatic.read_byte_array(f, 'float'))
                            each_veh_info.append(RePlayDataFileStatic.read_byte_array(f, 'float'))
                            each_veh_info.append(RePlayDataFileStatic.read_byte_array(f, 'float'))

                            #now add the veh_info list to the traffic info list
                            all_vehicles_info.append(each_veh_info)

                        self.traffic_info.append(all_vehicles_info)

                        #now save out the coin data
                        num_coins = RePlayDataFileStatic.read_byte_array(f, 'int')
                        self.num_coins.append(num_coins)
                        all_coin_info = []

                        for _ in itertools.repeat(None, num_coins):
                            each_coin_info = []
                            #position x, position y, width, height
                            guid_str = ''
                            if (self.traffic_racer_file_version >= 2):
                                list_of_bytes = RePlayDataFileStatic.read_16byte_guid(f)                            
                                bytes_object = bytes(list_of_bytes)
                                guid_object = uuid.UUID(bytes_le = bytes_object)
                                guid_str = str(guid_object)
                            each_coin_info.append(RePlayDataFileStatic.read_byte_array(f, 'float'))
                            each_coin_info.append(RePlayDataFileStatic.read_byte_array(f, 'float'))
                            each_coin_info.append(RePlayDataFileStatic.read_byte_array(f, 'float'))
                            each_coin_info.append(RePlayDataFileStatic.read_byte_array(f, 'float'))
                            each_coin_info.append(guid_str)
                            all_coin_info.append(each_coin_info)

                            if (guid_str not in self.coin_guids):
                                self.coin_guids.append(guid_str)

                        self.coin_info.append(all_coin_info)
                        self.highlighted_lane.append(RePlayDataFileStatic.read_byte_array(f, 'int'))

                    #Packet 3 indicates a rebaseline event
                    elif packet_type == 3:
                        timenum_read = RePlayDataFileStatic.read_byte_array(f, 'float64')
                        self.rebaseline_time.append(RePlayDataFileStatic.convert_matlab_datenum_to_python_datetime(timenum_read))

                        number_rebaseline_values = RePlayDataFileStatic.read_byte_array(f, 'int')
                        self.number_rebaseline_values.append(number_rebaseline_values)

                        temp_baselines = []
                        for _ in itertools.repeat(None, number_rebaseline_values):
                            temp_baselines.append(RePlayDataFileStatic.read_byte_array(f, 'double'))

                        self.rebaseline_values.append(temp_baselines)

                    #Packet 4 indicates a crash event
                    elif packet_type == 4:
                        if (self.traffic_racer_file_version >= 2):
                            timenum_read = RePlayDataFileStatic.read_byte_array(f, 'float64')
                            py_timenum = RePlayDataFileStatic.convert_matlab_datenum_to_python_datetime(timenum_read)
                            self.crash_events.append(py_timenum)

                    #Packet 5 indicates a re-start event (occurs after a crash)
                    elif packet_type == 5:
                        if (self.traffic_racer_file_version >= 2):
                            timenum_read = RePlayDataFileStatic.read_byte_array(f, 'float64')
                            py_timenum = RePlayDataFileStatic.convert_matlab_datenum_to_python_datetime(timenum_read)
                            self.restart_events.append(py_timenum)

                    #Packet 6 indicates a coin capture event
                    elif packet_type == 6:
                        if (self.traffic_racer_file_version >= 2):
                            timenum_read = RePlayDataFileStatic.read_byte_array(f, 'float64')
                            py_timenum = RePlayDataFileStatic.convert_matlab_datenum_to_python_datetime(timenum_read)

                            list_of_bytes = RePlayDataFileStatic.read_16byte_guid(f)                            
                            bytes_object = bytes(list_of_bytes)
                            guid_object = uuid.UUID(bytes_le = bytes_object)
                            guid_str = str(guid_object) 

                            self.coin_capture_events.append(py_timenum)   
                            self.coin_capture_guids.append(guid_str)                  

                    else:
                        self.bad_packet_count = self.bad_packet_count + 1
                        if (self.bad_packet_count > 10):
                            self.aborted_file = True
                            print("Aborting file because bad packet count exceeded 10 bad packets.")
                            return
            except:
                print(f'\nGame Crash detected during read of file: {self.filepath}')
                self.crash_detected = 1

    def DetermineSignal (self, replay_version_code, game_name, exercise_name, gain, sensitivity):
        #The following pseudocode illustrates how RePlay transforms the signal data before saving it
        #in the data file:
        '''
        //Transform the device exercise data to get the total lateral movement
        lateral_movement = -(float)Exercise.CurrentNormalizedValue;

        //Determine whether or not to stimulate
        bool stim = VNS.Determine_VNS_Triggering(DateTime.Now, lateral_movement);
        '''

        #Create some default values
        self.signal_actual_units = "Unknown"
        self.signal_actual = []

        #RePlay version code 30 is the first version that was used in the Baylor SCI trial.
        if (replay_version_code >= 30) and hasattr(self, "signal"):
            self.signal_actual = Enumerable(self.signal).select(lambda x: ((x * sensitivity) / gain)).to_list()

            #Determine the units for this signal
            exercise_tuple = Enumerable(RePlayExercises.exercises).where(lambda x: x[0] == exercise_name).first_or_default()
            if (exercise_tuple is not None):
                exercise_units = exercise_tuple[3]
                self.signal_actual_units = exercise_units        

    #endregion

    #region Methods used to obtain basic session information

    def GetGameSignal (self, use_real_world_units = True, parent_data_file = None):
        result_signal = []
        result_units = "Unknown"
        if (use_real_world_units) and hasattr(self, "signal_actual"):
            result_signal = self.signal_actual
            result_units = self.signal_actual_units
        elif hasattr(self, "signal"):
            result_signal = self.signal
            result_units = "Transformed game units"

        basis_time = None
        if (len(self.signal_timenum) > 0):
            basis_time = self.signal_timenum[0]

        return (result_signal, self.signal_time, result_units, basis_time)           

    def GetDifficulty(self):
        #Traffic Racer stores difficulty on a range of 0 to 1. The value 0.1 is the default.
        result = 0.1

        if (hasattr(self, "difficulty")):
            if (isinstance(self.difficulty, list)):
                if (len(self.difficulty) > 0):
                    result = self.difficulty[0]
            else:
                result = self.difficulty        

        #Traffic Racer stores difficulty on a range of 0 to 1. Let's divide by 0.1 to get a range of 0 to 10.
        result = round(result / 0.1)
                            
        return result

    def GetNormalizedDifficulty(self):        
        replay_minimum_difficulty = 1
        replay_maximum_difficulty = 10

        replay_normalized_difficulty = (self.GetDifficulty()) / (replay_maximum_difficulty - replay_minimum_difficulty)
        return replay_normalized_difficulty        

    #endregion

    #region Methods used to calculate analysis metrics that are specific to Traffic Racer

    def GetHighScore (self):
        result = 0
        if (len(self.current_score) > 0):
            result = max(self.current_score)
        return result

    def GetAttemptScores (self):
        result = []
        for i in range(0, len(self.current_score)):
            if (self.current_score == 0):
                prev_idx = i - 1
                if (prev_idx >= 0):
                    if (self.current_score[prev_idx] > 0):
                        result.append(self.current_score[prev_idx])
        return result

    def GetAverageAttemptScore (self):
        result = float("NaN")
        attempt_scores = self.GetAttemptScores()
        if (len(attempt_scores) > 0):
            result = float(np.nanmean(attempt_scores))
        return result

    def GetScorePerMinute (self):
        result = float("NaN")
        if (len(self.signal_time) > 0):
            mean_time_diff = float(np.nanmean(np.diff(self.signal_time)))

            numpy_score = np.array(self.current_score)
            diff_score = np.diff(numpy_score)
            diff_score = np.where(diff_score < 0, 0, diff_score)
            mean_diff_score = float(np.nanmean(diff_score))

            result = 60.0 * mean_diff_score / mean_time_diff

        return result

    def CalculatePercentTimeInTargetLane (self):
        TrafficRacer_SamplesToShift = 1200

        #Now, let's grab the participant's x-position at each timepoint
        x_position = [x[0] for x in self.player_vehicle_info]

        #Tranform the x position signal to lane ids for each timepoint
        lane_id_signal = self.TransformVehiclePositionSignalToLaneNumber(x_position)

        #Let's also grab the id of the "target" lane at each timepoint
        target_lane = self.highlighted_lane

        #FOR OLD REPLAY DATA FILES
        #Shift the target lane signal so that it is correct
        if (self.replay_version_code < 23):
            target_lane = self.TransformTargetLaneSignal(target_lane)
        #END OF CODE SEGMENT FOR OLD REPLAY DATA FILES
        
        #For each timepoint, determine if the lane the vehicle is in matches the target lane
        lane_match_signal = []
        for idx in range(len(target_lane)):
            try:
                cur_vehicle_lane = lane_id_signal[idx]
            except:
                cur_vehicle_lane = float("NaN")

            try:
                cur_target_lane = target_lane[idx] 
            except:
                cur_target_lane = float("NaN")
            is_match = (cur_vehicle_lane == cur_target_lane)
            lane_match_signal.append(is_match)
        
        lane_match_signal_for_calculation = lane_match_signal[TrafficRacer_SamplesToShift:]
        total_matches = sum(lane_match_signal_for_calculation)
        total_signal_length = len(lane_match_signal_for_calculation)

        match_lane_percentage = int((total_matches / total_signal_length) * 100)
        return match_lane_percentage

    #Given the full x-position signal of the participant's vehicle during a session of Traffic Racer,
    #this method will transform that signal into the lane id that the vehicle was in at each respective
    #timepoint.
    def TransformVehiclePositionSignalToLaneNumber (self, vehicle_position_x_signal):
        lane_id_signal = [self.DetermineLaneFromVehiclePosition(x) for x in vehicle_position_x_signal]
        return lane_id_signal

    #Given a "lane id", this method returns the X-position that is in the center of that lane on the screen.
    #This method is identical to the function GetCenterOfLane which is found in the RePlay Traffic Racer
    #game code. The "lane id" can be between 0 and 3 (because there are 4 lanes).
    def GetCenterOfLanePosition (self, lane_id):
        TrafficRacer_LaneWidth = 5
        TrafficRacer_NumLanes = 4
        return (TrafficRacer_LaneWidth * (lane_id - TrafficRacer_NumLanes / 2) + TrafficRacer_LaneWidth / 2)

    #Given an x-position of the vehicle on the screen, this method will return the lane in which the vehicle
    #resides. This method is identical to GetLane in the RePlay Traffic Racer game code.
    def DetermineLaneFromVehiclePosition (self, vehicle_position_x, tolerance = 0.1):
        TrafficRacer_LaneWidth = 5
        TrafficRacer_NumLanes = 4

        f = int(self.MapRange(vehicle_position_x, 
            -TrafficRacer_LaneWidth * TrafficRacer_NumLanes / 2, 
            TrafficRacer_LaneWidth * TrafficRacer_NumLanes / 2, 
            0, 
            TrafficRacer_NumLanes))
        return f

    # This function maps a numeric value from one range onto another range. It can optionally clamp
    # that value as well.
    def MapRange (self, val, oldrange_min, oldrange_max, newrange_min, newrange_max, clamp = False):
        if clamp:
            val = np.clip(val, oldrange_min, oldrange_max)
        return (val - oldrange_min) / (oldrange_max - oldrange_min) * (newrange_max - newrange_min) + newrange_min

    #In Traffic Racer, there is a bug in how the "target lane" is saved to the data files. Therefore,
    #before we process any data from a specific file, it is important that we transform the "target lane"
    #data from that file to be correct. 
    #
    #The bug in the data file is as follows: the game Traffic Racer creates "road segments" for the
    #car to drive on. Each road segment has a "highlighted lane", a.k.a "target lane". There are 10
    #road segments stored in memory at any point in time, and as an old road segment is phased out,
    #a new road segment is created and placed at the "end" of the road. The "highlighted lane" is
    #assigned to that new road seg
    @staticmethod
    def TransformTargetLaneSignal (target_lane_signal_input):

        #THIS NUMBER IS ONLY CORRECT AS LONG AS THE CAR IS MOVING AT 10 UNITS/SECOND.
        #If the car is moving at any other speed (which is the case under certain 
        #   circumstances when the game is played at a higher difficulty), then this
        #   code does not work!
        #
        #The bug in TrafficRacer needs to be fixed before we start using it at higher
        #   difficulty settings.   
        #
        #This number is calculated from the following:
        #The car moves at a velocity of 10 units/second.
        #Each road segment is 20 units long.
        #There are 10 road segments in the road.
        #The time to reach the end of the last road segment is therefore 20 seconds.
        #Samples are collected at 60 Hz.
        #The number of samples in 20 seconds is therefore 1200.
        #
        #Therefore we must shift the target lane signal by 1200 samples so that the 
        #   target lane at each timepoint is correct for where the car is currently 
        #   on the road.
        TrafficRacer_SamplesToShift = 1200
        samples_to_shift = TrafficRacer_SamplesToShift

        #Remove the last N elements from the list
        target_lane_signal_input = target_lane_signal_input[
            :len(target_lane_signal_input) - samples_to_shift
        ]

        #Prepend a bunch of NaNs to the beginning of the list
        result = [float("NaN")] * samples_to_shift
        result.extend(target_lane_signal_input)

        #Return the result
        return result

    #endregion
    