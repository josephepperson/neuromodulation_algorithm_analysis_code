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

from RePlayAnalysisCore3.CustomFields.CustomFields import *
from RePlayAnalysisCore3.GameData.RePlayGameData import RePlayGameData
from RePlayAnalysisCore3.DataFiles.RePlayDataFileStatic import RePlayDataFileStatic
from RePlayAnalysisCore3.RePlayExercises import RePlayExercises
from RePlayAnalysisCore3.RePlayExercises import RePlayDevice

class RePlayGameDataFruitNinja(RePlayGameData):

    fruit_ninja_file_version = IntField()

    game_session_start_time = DateTimeField()
    game_session_duration = IntField()

    touch_info = ListField(DynamicField())
    remaining_time = ListField(FloatField())
    manager_data = ListField(DynamicField())
    game_data = ListField(DynamicField())
    num_touches = ListField(IntField())
    num_fruit = ListField(IntField())
    fruit_data = ListField(DynamicField())
    is_cutting = ListField(IntField())
    num_strokes = ListField(IntField())
    stroke_data = ListField(DynamicField())
    cut_velocity = ListField(FloatField())

    finish_time = DateTimeField()
    total_fruit_created = IntField()
    total_fruit_hit = IntField()
    total_bombs_created = IntField()
    total_bombs_hit = IntField()
    total_swipes = IntField()
    final_score = IntField()

    #region Constructor

    def __init__(self, *args, **values):
        super().__init__(*args, **values)

    #endregion

    #region Methods used while loading the data into the database from data files

    def ReadGameData(self, file_path, file_name, data_start_location):
        self.filepath = file_path
        self.filename = file_name
        self.__data_start_location = data_start_location

        self.game_session_start_time = datetime.min
        self.game_session_duration = 0
        self.fruit_ninja_file_version = 0

        self.signal_time = []
        self.signal_timenum = []
        self.signal_timeelapsed = []
        self.touch_info = []
        self.remaining_time = []

        self.manager_data = []
        self.game_data = []
        self.num_touches = []
        self.num_fruit = []
        self.fruit_data = []

        self.is_cutting = []
        self.num_strokes = []
        self.stroke_data = []

        self.cut_velocity = []
        self.bad_packet_count = 0
            
        #Grab the file size in bytes
        flength = os.stat(self.filename).st_size
        packet_type = 0

        with open(self.filename, 'rb') as f:

            # seek to the position in the file to begin reading trial information
            f.seek(self.__data_start_location)
            try:
                #Loop until end of file (minus 4 byte, since that's the final game information)
                while (f.tell() < flength - 4):
                    packet_type = RePlayDataFileStatic.read_byte_array(f, 'int')
                    
                    #Packet 1 indicates metadata for a session
                    if packet_type == 1:
                        timenum_read = RePlayDataFileStatic.read_byte_array(f, 'float64')
                        self.game_session_start_time = RePlayDataFileStatic.convert_matlab_datenum_to_python_datetime(timenum_read)
                        self.fruit_ninja_file_version = RePlayDataFileStatic.read_byte_array(f, 'int')
                        self.game_session_duration = RePlayDataFileStatic.read_byte_array(f, 'int')

                    elif packet_type == 2:
                        timenum_read = RePlayDataFileStatic.read_byte_array(f, 'float64')
                        self.signal_timenum.append(RePlayDataFileStatic.convert_matlab_datenum_to_python_datetime(timenum_read))
                        self.signal_timeelapsed.append(self.signal_timenum[-1]-self.signal_timenum[0])  
                        self.signal_time.append(self.signal_timeelapsed[-1].total_seconds())                    

                        num_touches = RePlayDataFileStatic.read_byte_array(f, 'int')
                        self.num_touches.append(num_touches)
                        
                        ind_touch_info = []
                        frame_touch_info = []
                        if num_touches > 0:
                            #For each touch, info is saved as Xpos, Ypos, ID, State
                            for _ in itertools.repeat(None, num_touches):
                                ind_touch_info = []
                                ind_touch_info.append(RePlayDataFileStatic.read_byte_array(f, 'float'))
                                ind_touch_info.append(RePlayDataFileStatic.read_byte_array(f, 'float'))
                                ind_touch_info.append(RePlayDataFileStatic.read_byte_array(f, 'int'))
                                ind_touch_info.append(RePlayDataFileStatic.read_byte_array(f, 'int'))
                                frame_touch_info.append(ind_touch_info)
                        else:
                            ind_touch_info.append(None)
                            ind_touch_info.append(None)
                            ind_touch_info.append(None)
                            ind_touch_info.append(None)
                            frame_touch_info.append(ind_touch_info)
                        
                        self.touch_info.append(frame_touch_info)

                        if (hasattr(self, "fruit_ninja_file_version")):
                            if (self.fruit_ninja_file_version >= 2):
                                self.cut_velocity.append(RePlayDataFileStatic.read_byte_array(f, 'double'))

                        self.remaining_time.append(RePlayDataFileStatic.read_byte_array(f, 'double'))

                        manager_data = RePlayDataFileStatic.read_byte_array(f, 'uint8')
                        self.manager_data.append(manager_data)

                        #Read in the values for the following game properties: FruitHit,
                        #Fruit Created, Bombs Hit, Max Fruit Speed, Fruit Spawn Interval, Bomb Spawn Interval
                        frame_game_data = []
                        if (manager_data):
                            frame_game_data.append(RePlayDataFileStatic.read_byte_array(f, 'int'))
                            frame_game_data.append(RePlayDataFileStatic.read_byte_array(f, 'int'))
                            frame_game_data.append(RePlayDataFileStatic.read_byte_array(f, 'int'))
                            frame_game_data.append(RePlayDataFileStatic.read_byte_array(f, 'int'))
                            frame_game_data.append(RePlayDataFileStatic.read_byte_array(f, 'int'))
                            frame_game_data.append(RePlayDataFileStatic.read_byte_array(f, 'int'))
                        else:
                            frame_game_data.append(None)
                            frame_game_data.append(None)
                            frame_game_data.append(None)
                            frame_game_data.append(None)
                            frame_game_data.append(None)
                            frame_game_data.append(None)

                        self.game_data.append(frame_game_data)

                        num_fruit = RePlayDataFileStatic.read_byte_array(f, 'int')
                        self.num_fruit.append(num_fruit)
                        
                        frame_fruit_data = []
                        ind_fruit_data = []

                        #fruit_id, fruit_speed, fruit_gravity, fruit_x, fruit_abs_y, fruit_is_alive, 
                        #fruit_is_obstacle, fruit_time
                        if num_fruit > 0:
                            for _ in itertools.repeat(None, num_fruit):
                                ind_fruit_data = []
                                ind_fruit_data.append(RePlayDataFileStatic.read_byte_array(f, 'int'))
                                ind_fruit_data.append(RePlayDataFileStatic.read_byte_array(f, 'int'))
                                ind_fruit_data.append(RePlayDataFileStatic.read_byte_array(f, 'float'))
                                ind_fruit_data.append(RePlayDataFileStatic.read_byte_array(f, 'int'))
                                ind_fruit_data.append(RePlayDataFileStatic.read_byte_array(f, 'int'))
                                ind_fruit_data.append(RePlayDataFileStatic.read_byte_array(f, 'uint8'))
                                ind_fruit_data.append(RePlayDataFileStatic.read_byte_array(f, 'uint8'))
                                ind_fruit_data.append(RePlayDataFileStatic.read_byte_array(f, 'float'))

                                frame_fruit_data.append(ind_fruit_data)
                        else:
                            ind_fruit_data.append(None)
                            ind_fruit_data.append(None)
                            ind_fruit_data.append(None)
                            ind_fruit_data.append(None)
                            ind_fruit_data.append(None)
                            ind_fruit_data.append(None)
                            ind_fruit_data.append(None)
                            ind_fruit_data.append(None)

                            frame_fruit_data.append(ind_fruit_data)

                        self.fruit_data.append(frame_fruit_data)

                        is_cutting = RePlayDataFileStatic.read_byte_array(f, 'uint8')
                        self.is_cutting.append(is_cutting)
                        
                        frame_stroke_data = []
                        ind_stroke_data = []

                        #stroke data: [time of stroke, xpos, ypos]
                        if (is_cutting):
                            num_strokes = RePlayDataFileStatic.read_byte_array(f, 'int')
                            self.num_strokes.append(num_strokes)
                            if num_strokes > 0:
                                for _ in itertools.repeat(None, num_strokes):
                                    ind_stroke_data = []
                                    timenum_read = RePlayDataFileStatic.read_byte_array(f, 'float64')
                                    ind_stroke_data.append(RePlayDataFileStatic.convert_matlab_datenum_to_python_datetime(timenum_read))
                                    ind_stroke_data.append(RePlayDataFileStatic.read_byte_array(f, 'float'))
                                    ind_stroke_data.append(RePlayDataFileStatic.read_byte_array(f, 'float'))
                                    frame_stroke_data.append(ind_stroke_data)
                            else:
                                ind_stroke_data.append(0)
                                ind_stroke_data.append(None)
                                ind_stroke_data.append(None)
                                frame_stroke_data.append(ind_stroke_data)
                        else:
                            self.num_strokes.append(0)
                            ind_stroke_data.append(None)
                            ind_stroke_data.append(None)
                            ind_stroke_data.append(None)
                            frame_stroke_data.append(ind_stroke_data)

                        self.stroke_data.append(frame_stroke_data)

                    #end of game data
                    elif packet_type == 3:
                        timenum_read = RePlayDataFileStatic.read_byte_array(f, 'float64')
                        self.finish_time = RePlayDataFileStatic.convert_matlab_datenum_to_python_datetime(timenum_read)
                        self.total_fruit_created = RePlayDataFileStatic.read_byte_array(f, 'int')
                        self.total_fruit_hit = RePlayDataFileStatic.read_byte_array(f, 'int')
                        self.total_bombs_created = RePlayDataFileStatic.read_byte_array(f, 'int')
                        self.total_bombs_hit = RePlayDataFileStatic.read_byte_array(f, 'int')
                        self.total_swipes = RePlayDataFileStatic.read_byte_array(f, 'int')
                        self.final_score = RePlayDataFileStatic.read_byte_array(f, 'int')

                    else:
                        self.bad_packet_count = self.bad_packet_count + 1
                        if (self.bad_packet_count > 10):
                            self.aborted_file = True
                            print("Aborting file because bad packet count exceeded 10 bad packets.")
                            return
                                                    
            except:
                print(f"\nError reading file. Packet type = {packet_type}")
                print(f'\nGame Crash detected during read of file: {self.filepath}')
                print(f"File location: {f.tell()}, Most recent packet type: {packet_type}")
                self.crash_detected = 1
    
    #endregion

    #region Methods to get basic session information

    def GetGameSignal (self, use_real_world_units = True, parent_data_file = None):
        result = []
        result_time = []
        cur_touch_id = -1
        start_x = 0
        start_y = 0
        start_t = 0

        if (self.signal_time is not None) and (len(self.signal_time) > 0):
            result_time = self.signal_time

            if ((hasattr(self, "cut_velocity")) and (len(self.cut_velocity) > 0)):
                result = self.cut_velocity
            else:
                for t_idx in range(0, len(self.signal_time)):
                    cur_cut_velocity = 0
                    touch = self.touch_info[t_idx]
                    if (touch is not None) and (len(touch) > 0):
                        touch = touch[0]
                        touch_x = touch[0]
                        touch_y = touch[1]
                        touch_id = touch[2]

                        if (touch_id is not None):
                            #A new touch is beginning
                            if (touch_id != cur_touch_id):
                                cur_touch_id = touch_id
                                start_x = touch_x
                                start_y = touch_y
                                start_t = self.signal_time[t_idx]
                            else:
                                #A touch is being continued
                                cur_distance = math.hypot(touch_x - start_x, touch_y - start_y)
                                delta_time = self.signal_time[t_idx] - start_t
                                cur_cut_velocity = cur_distance / delta_time
                    
                    result.append(cur_cut_velocity)

        basis_time = None
        if (len(self.signal_timenum) > 0):
            basis_time = self.signal_timenum[0]
            
        return (result, result_time, "Pixels per second", basis_time)
    
    #endregion

    #region Methods that are specific to calculating "repetitions" for Fruit Ninja

    def CalculateRepetitionData(self, exercise_id):
        touch_trajectories = self.CalculateTouchTrajectories()
        return self.CalculateFruitNinjaRepetitionData(touch_trajectories)

    def CalculateFruitNinjaRepetitionData (self, touch_trajectories):
        result_repetition_count = 0
        result_rep_start_idx = []

        if ((self.signal_time is not None) and (len(self.signal_time) > 0)):
            if (touch_trajectories is not None):
                result_repetition_count = len(touch_trajectories)

                for touch_key in touch_trajectories:
                    touch_object = touch_trajectories[touch_key]
                    touch_time_list = touch_object["t"]
                    touch_start_time = touch_time_list[0]
                    touch_start_idx = next(x[0] for x in enumerate(self.signal_time) if x[1] >= touch_start_time)
                    result_rep_start_idx.append(touch_start_idx)

        return (result_repetition_count, result_rep_start_idx)

    def CalculateTouchTrajectories(self):
        #Create an object to hold all the resulting touch trajectories
        touch_trajectories = {}

        #Let's iterate over the the "touch_info" object
        for t in range(0, len(self.touch_info)):
            time_elapsed = self.signal_time[t]
            for touch in self.touch_info[t]:
                if touch is not None:
                    if len(touch) >= 4:
                        touch_x = touch[0]
                        touch_y = touch[1]
                        touch_id = touch[2]
                        if (touch_id is not None):
                            if (not (touch_id in touch_trajectories)):
                                new_touch_object = {}
                                new_touch_object["x"] = []
                                new_touch_object["y"] = []
                                new_touch_object["t"] = []
                                touch_trajectories[touch_id] = new_touch_object

                            touch_trajectories[touch_id]["x"].append(touch_x)
                            touch_trajectories[touch_id]["y"].append(touch_y)
                            touch_trajectories[touch_id]["t"].append(time_elapsed)

                                
        
        return touch_trajectories

    #endregion

    #region Methods that are specific to performing data analysis on Fruit Ninja

    def CalculateObjectTrajectories(self, only_fruit = False):
        #Create an object to hold all the resulting touch trajectories
        object_trajectories = {}

        #Let's iterate over the the "touch_info" object
        for t in range(0, len(self.fruit_data)):
            time_elapsed = self.signal_time[t]

            for object_data in self.fruit_data[t]:
                if object_data is not None:
                    if len(object_data) >= 4:
                        object_id = object_data[0]
                        object_x = object_data[3]
                        object_y = object_data[4]
                        object_is_alive = object_data[5]
                        object_is_bomb = object_data[6]

                        #If the "only fruit" flag is set, and this is a bomb, then skip it
                        if (object_is_bomb and only_fruit):
                            continue
                        
                        if (object_id is not None):
                            if (not (object_id in object_trajectories)):
                                new_object = {}
                                new_object["t"] = []
                                new_object["x"] = []
                                new_object["y"] = []
                                new_object["is_alive"] = []
                                new_object["is_bomb"] = []
                                object_trajectories[object_id] = new_object

                            object_trajectories[object_id]["t"].append(time_elapsed)
                            object_trajectories[object_id]["x"].append(object_x)
                            object_trajectories[object_id]["y"].append(object_y)
                            object_trajectories[object_id]["is_alive"].append(object_is_alive)
                            object_trajectories[object_id]["is_bomb"].append(object_is_bomb)
        
        return object_trajectories
            
    def CalculateTotalFruitHit (self):
        total_fruit_hit = 0
        try:
            #The easiest way to get the total number of fruit hit
            total_fruit_hit = self.total_fruit_hit
        except:
            #The second way to get the total number of fruit hit
            try:
                if len(self.game_data) > 0:
                    final_frame = self.game_data[-1]
                    if (len(final_frame) > 0):
                        total_fruit_hit = final_frame[0]
            except:
                total_fruit_hit = None

        #The final way to get the total number of fruit hit
        if (total_fruit_hit is None):
            fruit_trajectories = self.CalculateObjectTrajectories(only_fruit=True)
            total_fruit_hit = 0
            for f_key in fruit_trajectories:
                f = fruit_trajectories[f_key]
                f_is_alive = f["is_alive"]
                if not (f_is_alive[-1]):
                    total_fruit_hit += 1      
        
        return total_fruit_hit

    def CalculateSwipeAccuracy(self):
        touch_trajectories = self.CalculateTouchTrajectories()
        fruit_trajectories = self.CalculateObjectTrajectories(only_fruit=True)

        total_fruit_hit = 0
        try:
            #The easiest way to get the total number of fruit hit
            total_fruit_hit = self.total_fruit_hit
        except:
            #The second way to get the total number of fruit hit
            try:
                if len(self.game_data) > 0:
                    final_frame = self.game_data[-1]
                    if (len(final_frame) > 0):
                        total_fruit_hit = final_frame[0]
            except:
                total_fruit_hit = None

        #The final way to get the total number of fruit hit
        if (total_fruit_hit is None):
            total_fruit_hit = 0
            for f_key in fruit_trajectories:
                f = fruit_trajectories[f_key]
                f_is_alive = f["is_alive"]
                if not (f_is_alive[-1]):
                    total_fruit_hit += 1

        total_touches = len(touch_trajectories)
        swipe_accuracy = 0
        try:
            swipe_accuracy = 100 * (total_fruit_hit / total_touches)
        except:
            swipe_accuracy = 0

        if (swipe_accuracy > 100):
            swipe_accuracy = 100

        return swipe_accuracy

    def CalculateTotalFruitMissed (self):
        fruit_trajectories = self.CalculateObjectTrajectories(only_fruit=True)
        total_fruit = 0
        total_fruit_hit = 0
        for f_key in fruit_trajectories:
            total_fruit += 1
            f = fruit_trajectories[f_key]
            f_is_alive = f["is_alive"]
            if not (f_is_alive[-1]):
                total_fruit_hit += 1      
        
        return (total_fruit - total_fruit_hit)

    def CalculateTotalBombsHit (self):
        total_fruit_hit = self.CalculateTotalFruitHit()
        object_trajectories = self.CalculateObjectTrajectories(only_fruit=False)
        total_objects = 0
        total_objects_hit = 0
        for f_key in object_trajectories:
            total_objects += 1
            f = object_trajectories[f_key]
            f_is_alive = f["is_alive"]
            if not (f_is_alive[-1]):
                total_objects_hit += 1

        total_bombs_hit = total_objects_hit - total_fruit_hit
        if (total_bombs_hit < 0):
            total_bombs_hit = 0
        
        return total_bombs_hit

    #endregion
