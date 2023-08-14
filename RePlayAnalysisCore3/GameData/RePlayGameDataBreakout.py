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

class RePlayGameDataBreakout(RePlayGameData):

    breakout_file_version = IntField()
    
    start_time = DateTimeField()
    game_level = IntField()
    block_width = IntField()
    block_height = IntField()
    num_blocks = IntField()
    block_info = ListField(DynamicField())
    
    paddle_position = ListField(DynamicField())
    paddle_size = ListField(DynamicField())
    num_balls = ListField(IntField())
    ball_info = ListField(DynamicField())
    collision_time = ListField(FloatField())
    collided_block = ListField(DynamicField())

    #region Constructor

    def __init__(self, *args, **values):
        super().__init__(*args, **values)

    #endregion

    #region Methods used during the loading of the data file into the database

    def ReadGameData(self, file_path, file_name, data_start_location):
        self.filepath = file_path
        self.filename = file_name
        self.__data_start_location = data_start_location

        self.breakout_file_version = 0
        self.start_time = datetime.min
        self.game_level = 0
        self.difficulty = 0
        
        self.block_width = 0
        self.block_height = 0
        self.num_blocks = 0       
        self.block_info = []

        self.signal = []
        self.signal_timenum = []
        self.signal_timeelapsed = []
        self.signal_time = []

        self.paddle_position = []
        self.paddle_size = []
        self.num_balls = []
        self.ball_info = []
        self.collision_time = []
        self.collided_block = []

        self.rebaseline_time = []
        self.number_rebaseline_values = []
        self.rebaseline_values = []

        vns_algorithm_start_time = None
        self.vns_algorithm_is_frame_data_present = False
        self.vns_algorithm_timenum = []
        self.vns_algorithm_time = []
        self.vns_algorithm_should_trigger = []
        self.vns_algorithm_signal_value = []
        self.vns_algorithm_positive_threshold = []
        self.vns_algorithm_negative_threshold = []
        self.vns_algorithm_timing_allows_trigger = []

        #Grab the file size in bytes
        flength = os.stat(self.filename).st_size

        with open(self.filename, 'rb') as f:

            # seek to the position in the file to begin reading trial information
            f.seek(self.__data_start_location)

            try:
                while (f.tell() < flength - 4):
                    packet_type = RePlayDataFileStatic.read_byte_array(f, 'int')

                    try:
                        #Packet 1 indicates metadata for a session
                        if packet_type == 1:
                            timenum_read = RePlayDataFileStatic.read_byte_array(f, 'float64')
                            self.start_time = RePlayDataFileStatic.convert_matlab_datenum_to_python_datetime(timenum_read)
                            self.breakout_file_version = RePlayDataFileStatic.read_byte_array(f, 'int')
                            self.difficulty = RePlayDataFileStatic.read_byte_array(f, 'int')
                            self.game_level = RePlayDataFileStatic.read_byte_array(f, 'int')
                            self.block_width = RePlayDataFileStatic.read_byte_array(f, 'int')
                            self.block_height = RePlayDataFileStatic.read_byte_array(f, 'int')
                            self.num_blocks = RePlayDataFileStatic.read_byte_array(f, 'int')

                            set_blocks_info = []
                            for _ in range(0, self.num_blocks):
                                ind_block_info = []
                                
                                #read in the x and y coordinates of the block
                                ind_block_info.append(RePlayDataFileStatic.read_byte_array(f, 'float'))
                                ind_block_info.append(RePlayDataFileStatic.read_byte_array(f, 'float'))

                                # read in block type
                                temp_length = RePlayDataFileStatic.read_byte_array(f, 'int32')
                                ind_block_info.append(f.read(temp_length).decode())

                                #Read in the block durability
                                ind_block_info.append(RePlayDataFileStatic.read_byte_array(f, 'int'))

                                set_blocks_info.append(ind_block_info)
                                
                            self.block_info.append(set_blocks_info)

                        #Packet 2 indicates stream data
                        elif packet_type == 2:
                            timenum_read = RePlayDataFileStatic.read_byte_array(f, 'float64')
                            self.signal_timenum.append(RePlayDataFileStatic.convert_matlab_datenum_to_python_datetime(timenum_read))
                            self.signal_timeelapsed.append(self.signal_timenum[-1]-self.signal_timenum[0])
                            self.signal_time.append(self.signal_timeelapsed[-1].total_seconds())
                            self.signal.append(RePlayDataFileStatic.read_byte_array(f, 'double'))

                            #read in the x and y position of the paddle
                            pad_pos = []
                            pad_pos.append(RePlayDataFileStatic.read_byte_array(f, 'float'))
                            pad_pos.append(RePlayDataFileStatic.read_byte_array(f, 'float'))
                            self.paddle_position.append(pad_pos)

                            #read in the width and height of the paddle
                            pad_size = []
                            pad_size.append(RePlayDataFileStatic.read_byte_array(f, 'int'))    
                            pad_size.append(RePlayDataFileStatic.read_byte_array(f, 'int'))      
                            self.paddle_size.append(pad_size)

                            #read in information for each ball
                            num_balls = (RePlayDataFileStatic.read_byte_array(f, 'int'))
                            self.num_balls.append(num_balls)
                            set_balls_info = []
                            for _ in itertools.repeat(None, num_balls):
                                ind_ball_info = []

                                if (self.breakout_file_version >= 2):
                                    ind_ball_info.append(RePlayDataFileStatic.read_16byte_guid(f))
                                else:
                                    ind_ball_info.append(["UNKNOWN"])

                                #read in x,y position of ball
                                ind_ball_info.append(RePlayDataFileStatic.read_byte_array(f, 'float'))
                                ind_ball_info.append(RePlayDataFileStatic.read_byte_array(f, 'float'))
                                #read in ball speed
                                ind_ball_info.append(RePlayDataFileStatic.read_byte_array(f, 'float'))
                                #read in ball radius
                                ind_ball_info.append(RePlayDataFileStatic.read_byte_array(f, 'float'))

                                set_balls_info.append(ind_ball_info)
                            
                            self.ball_info.append(set_balls_info)

                        elif packet_type == 3:
                            self.collision_time.append(RePlayDataFileStatic.read_byte_array(f, 'float64'))

                            collided_block = []
                            collided_block.append(RePlayDataFileStatic.read_byte_array(f, 'float'))
                            collided_block.append(RePlayDataFileStatic.read_byte_array(f, 'float'))

                            #Durability
                            if self.breakout_file_version >= 2:
                                collided_block.append(RePlayDataFileStatic.read_byte_array(f, 'int32'))
                            else:
                                collided_block.append(float("NaN"))

                            self.collided_block.append(collided_block)

                        elif packet_type == 4:
                            timenum_read = RePlayDataFileStatic.read_byte_array(f, 'float64')
                            self.rebaseline_time.append(RePlayDataFileStatic.convert_matlab_datenum_to_python_datetime(timenum_read))

                            number_rebaseline_values = RePlayDataFileStatic.read_byte_array(f, 'int')
                            self.number_rebaseline_values.append(number_rebaseline_values)

                            temp_baselines = []
                            for _ in itertools.repeat(None, number_rebaseline_values):
                                temp_baselines.append(RePlayDataFileStatic.read_byte_array(f, 'double'))

                            self.rebaseline_values.append(temp_baselines)

                        elif packet_type == 5:
                            #This packet type exists for Breakout game file versions 2 and above
                            timenum_read = RePlayDataFileStatic.read_byte_array(f, 'float64')
                            converted_timestamp = RePlayDataFileStatic.convert_matlab_datenum_to_python_datetime(timenum_read)

                            num_chars = RePlayDataFileStatic.read_byte_array(f, 'int')
                            _ = f.read(num_chars).decode()
                            
                        elif packet_type == 6:
                            #This packet type exists for Breakout game file versions 2 and above
                            timenum_read = RePlayDataFileStatic.read_byte_array(f, 'float64')
                            converted_timestamp = RePlayDataFileStatic.convert_matlab_datenum_to_python_datetime(timenum_read)

                            num_chars = RePlayDataFileStatic.read_byte_array(f, 'int')
                            _ = f.read(num_chars).decode()
                            
                        elif packet_type == 7:
                            #This packet type exists for Breakout game file versions 2 and above
                            timenum_read = RePlayDataFileStatic.read_byte_array(f, 'float64')
                            converted_timestamp = RePlayDataFileStatic.convert_matlab_datenum_to_python_datetime(timenum_read)

                            num_chars = RePlayDataFileStatic.read_byte_array(f, 'int')
                            _ = f.read(num_chars).decode()

                        elif packet_type == 8:
                            #This packet type exists for Breakout game file versions 2 and above
                            timenum_read = RePlayDataFileStatic.read_byte_array(f, 'float64')
                            converted_timestamp = RePlayDataFileStatic.convert_matlab_datenum_to_python_datetime(timenum_read)

                        elif packet_type == 9:
                            #This packet type exists for Breakout game file versions 2 and above
                            timenum_read = RePlayDataFileStatic.read_byte_array(f, 'float64')
                            converted_timestamp = RePlayDataFileStatic.convert_matlab_datenum_to_python_datetime(timenum_read)

                            #game_difficulty of this level
                            RePlayDataFileStatic.read_byte_array(f, 'int')

                            #game_level of this level
                            RePlayDataFileStatic.read_byte_array(f, 'int')

                            #block_width for this level
                            RePlayDataFileStatic.read_byte_array(f, 'int')

                            #block_height for this level
                            RePlayDataFileStatic.read_byte_array(f, 'int')

                            #number of blocks for this level
                            num_blocks = RePlayDataFileStatic.read_byte_array(f, 'int')

                            #this is a more efficient way of looping a set number of times
                            for _ in itertools.repeat(None, num_blocks):
                                ind_block_info = []
                                
                                #x coordinate of block
                                RePlayDataFileStatic.read_byte_array(f, 'float')

                                #y coordinate of block
                                RePlayDataFileStatic.read_byte_array(f, 'float')

                                #block type
                                temp_length = RePlayDataFileStatic.read_byte_array(f, 'int32')
                                f.read(temp_length).decode()

                                #block durability
                                RePlayDataFileStatic.read_byte_array(f, 'int')

                        elif packet_type == 10:
                            #This is a VNS algorithm frame packet

                            #Read the timestamp of the packet and convert it to a Matlab timestamp
                            timenum_read = RePlayDataFileStatic.read_byte_array(f, 'float64')
                            converted_timestamp = RePlayDataFileStatic.convert_matlab_datenum_to_python_datetime(timenum_read)

                            #Read in the frame data
                            should_trigger_stim = RePlayDataFileStatic.read_byte_array(f, 'uint8')
                            vns_signal_val = RePlayDataFileStatic.read_byte_array(f, 'float64')
                            vns_pos_thresh = RePlayDataFileStatic.read_byte_array(f, 'float64')
                            vns_neg_thresh = RePlayDataFileStatic.read_byte_array(f, 'float64')
                            vns_timing_allows = RePlayDataFileStatic.read_byte_array(f, 'uint8')

                            self.vns_algorithm_is_frame_data_present = True
                            if (vns_algorithm_start_time is None):
                                vns_algorithm_start_time = converted_timestamp
                            seconds_elapsed = (converted_timestamp - vns_algorithm_start_time).total_seconds()

                            self.vns_algorithm_timenum.append(converted_timestamp)
                            self.vns_algorithm_time.append(seconds_elapsed)
                            self.vns_algorithm_should_trigger.append(should_trigger_stim)
                            self.vns_algorithm_signal_value.append(vns_signal_val)
                            self.vns_algorithm_positive_threshold.append(vns_pos_thresh)
                            self.vns_algorithm_negative_threshold.append(vns_neg_thresh)
                            self.vns_algorithm_timing_allows_trigger.append(vns_timing_allows)              

                        else:
                            self.bad_packet_count = self.bad_packet_count + 1
                            if (self.bad_packet_count > 10):
                                self.aborted_file = True
                                print("Aborting file because bad packet count exceeded 10 bad packets.")
                                return

                    except:
                        self.bad_packet_count = self.bad_packet_count + 1
                        if (self.bad_packet_count > 10):
                            self.aborted_file = True
                            print("Aborting file because bad packet count exceeded 10 bad packets.")
                            return

            except:
                print(f'\nGame Crash detected during read of file: {self.filepath.stem}')
                self.crash_detected = 1

    def DetermineSignal (self, replay_version_code, game_name, exercise_name, gain, sensitivity):
        #The following pseudocode illustrates how RePlay transforms the signal data before saving it
        #in the data file:
        '''
        debounce_size = 10;
        current_data = -Exercise.CurrentNormalizedValue; //CNV = CV * gain / sensitivity
                
        if (Exercise.ConvertSignalToVelocity) //"Flipping" and "Supination"
        {
            debounce_list.Add(current_data * 100.0f);
            debounce_list.LimitTo(debounce_size, true);
            if (debounce_list.Count == debounce_size)
            {
                current_data = TxBDC_Math.Diff(debounce_list).Average();
            }
        }

        bool stim = VNS.Determine_VNS_Triggering(DateTime.Now, current_data);        
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
                if (exercise_name == "Flipping") or (exercise_name == "Supination"):
                    self.signal_actual_units = f"Velocity ({exercise_units} / second)"
                else:
                    self.signal_actual_units = exercise_units

    #endregion

    #region Methods to get basic session information

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

    def GetNormalizedDifficulty(self):        
        replay_minimum_difficulty = 1
        replay_maximum_difficulty = 10

        replay_normalized_difficulty = (self.GetDifficulty()) / (replay_maximum_difficulty - replay_minimum_difficulty)
        return replay_normalized_difficulty                

    #endregion

    #region Methods specific to calculating analysis metrics for the Breakout game

    def CalculateBreakoutGameMetrics (self):
        #Initialize the results to nan
        num_balls_lost = float("NaN")
        balls_lost_per_minute = float("NaN")
        longest_ball_duration = float("NaN")
        average_interval = float("NaN")
        first_ball_lost_time = float("NaN")

        try:
            #Define the threshold that must be crossed by a ball for it to be considered as "lost"
            paddle_y_threshold = 1500

            #Get an array of the main ball position over time
            ball_1_ypos = []
            for i in range(0, len(self.ball_info)):
                success = False
                cur_all_ball_info = self.ball_info[i]
                if (len(cur_all_ball_info) > 0):
                    cur_ball_info = cur_all_ball_info[0]
                    if (len(cur_ball_info) >= 3):
                        cur_ypos = cur_ball_info[2]
                        ball_1_ypos.append(cur_ypos)
                        success = True
                
                if (not success):
                    ball_1_ypos.append(float("NaN"))

            main_ball_position_signal = np.array(ball_1_ypos)
            num_balls_signal = np.array(self.num_balls)
            timestamps_signal = np.array(self.signal_time)

            #Find indices where num_balls_signal is 1
            idx_where_only_one_ball = np.where(num_balls_signal == 1)
            main_ball_position_signal = main_ball_position_signal[idx_where_only_one_ball]
            timestamps_signal = timestamps_signal[idx_where_only_one_ball]

            #Now let's threshold the main ball position signal
            main_ball_position_signal[main_ball_position_signal < paddle_y_threshold] = 0
            main_ball_position_signal[main_ball_position_signal >= paddle_y_threshold] = 1
            main_ball_position_signal[np.isnan(main_ball_position_signal)] = 0
            diff_signal = np.diff(main_ball_position_signal)
            diff_signal[diff_signal < 0] = 0
            diff_signal = np.append(diff_signal, 0)

            idx_where_ball_was_lost = np.where(diff_signal == 1)[0]

            num_balls_lost = idx_where_ball_was_lost.size

            longest_timestamp = timestamps_signal[-1]

            if(num_balls_lost > 0):
                timestamps_of_lost_balls = timestamps_signal[idx_where_ball_was_lost]
                timestamps_of_lost_balls = np.insert(timestamps_of_lost_balls, 0, 0)
                inter_ball_loss_intervals = np.diff(timestamps_of_lost_balls)

                longest_ball_duration = max(inter_ball_loss_intervals)
                average_interval = np.nanmean(inter_ball_loss_intervals)
                balls_lost_per_minute = num_balls_lost / (longest_timestamp / 60.0)
                first_ball_lost_time = inter_ball_loss_intervals[0]
            else:
                longest_ball_duration = longest_timestamp
                average_interval = longest_timestamp
                balls_lost_per_minute = 0
                first_ball_lost_time = longest_timestamp
        except:
            pass

        return (num_balls_lost, balls_lost_per_minute, longest_ball_duration, average_interval, first_ball_lost_time)

    #endregion
    
