from mongoengine import *
from bson import BSON

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

from RePlayAnalysisCore3.ControllerData.RePlayControllerData import RePlayControllerData
from RePlayAnalysisCore3.GameData.RePlayGameData import RePlayGameData
from RePlayAnalysisCore3.GameData.RePlayGameDataBreakout import RePlayGameDataBreakout
from RePlayAnalysisCore3.GameData.RePlayGameDataFruitArchery import RePlayGameDataFruitArchery
from RePlayAnalysisCore3.GameData.RePlayGameDataFruitNinja import RePlayGameDataFruitNinja
from RePlayAnalysisCore3.GameData.RePlayGameDataRepetitionsMode import RePlayGameDataRepetitionsMode
from RePlayAnalysisCore3.GameData.RePlayGameDataSpaceRunner import RePlayGameDataSpaceRunner
from RePlayAnalysisCore3.GameData.RePlayGameDataTrafficRacer import RePlayGameDataTrafficRacer
from RePlayAnalysisCore3.GameData.RePlayGameDataTyperShark import RePlayGameDataTyperShark

from RePlayAnalysisCore3.DataFiles.RePlayDataFileStatic import RePlayDataFileStatic

from RePlayAnalysisCore3.VNS.RePlayVNSParameters import RePlayVNSParameters
from RePlayAnalysisCore3.VNS.RePlayVNSParameters import SmoothingOptions
from RePlayAnalysisCore3.VNS.RePlayVNSParameters import Stage1_Operations
from RePlayAnalysisCore3.VNS.RePlayVNSParameters import Stage2_Operations
from RePlayAnalysisCore3.VNS.RePlayVNSParameters import BufferExpirationPolicy

class RePlayDataFile(Document):
    meta = {
        'collection':'RePlayDataFile'
    }

    controller_data = GenericReferenceField()
    game_data = GenericReferenceField()
    controller_data_gridfs = FileField()
    game_data_gridfs = FileField()
    exceeds_mongodb_size_limit = BooleanField(default=False)

    vns_algorithm_parameters = EmbeddedDocumentField(RePlayVNSParameters)

    subject_id = StringField(max_length=200)
    md5_checksum = StringField()
    version = IntField()
    replay_build_date = DateTimeField()
    replay_version_name = StringField()
    replay_version_code = StringField()
    tablet_id = StringField()
    game_id = StringField()
    exercise_id = StringField()
    device_type = StringField()
    data_type = IntField()
    session_start = DateTimeField()
    standard_range = FloatField()
    actual_range = FloatField()
    gain = FloatField()
    crash_detected = IntField()
    aborted_file = BooleanField()
    bad_packet_count = IntField()
    filepath = StringField()
    filename = StringField()
    launched_from_assignment = IntField()
    total_stimulations = IntField()

    def __init__(self, *args, **values):
        super().__init__(*args, **values)
        self.controller_data_gridfs_in_memory = None
        self.game_data_gridfs_in_memory = None

    def InitiateFileRead(self, filepath):
        self.filepath = filepath
        self.filename = os.path.basename(filepath)

        self.__md5_checksum()
        self.__read_meta_data()

    # This method calculates the md5 checksum of the file's contents
    # This can be used for file verification
    def __md5_checksum(self):
        hash_md5 = hashlib.md5()
        with open(self.filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        self.md5_checksum = hash_md5.hexdigest()

    def __read_meta_data(self):
        # print(f'Reading metadata from file: {self.filepath.stem}')
        # open the file and parse through to grab the meta data
        with open(self.filepath, 'rb') as f:
            # seek to beginning of file and read the first 4 bytes: version number
            f.seek(0)
            self.version = RePlayDataFileStatic.read_byte_array(f, 'int32')

            if self.version < 7:
                # Read in the subject id
                temp_length = RePlayDataFileStatic.read_byte_array(f, 'int32')
                self.subject_id = f.read(temp_length).decode()

                # read in the game id
                temp_length = RePlayDataFileStatic.read_byte_array(f, 'int32')
                self.game_id = f.read(temp_length).decode()

                # read in exercise id
                temp_length = RePlayDataFileStatic.read_byte_array(f, 'int32')
                self.exercise_id = f.read(temp_length).decode()

                # read in device type
                temp_length = RePlayDataFileStatic.read_byte_array(f, 'int32')
                self.device_type = f.read(temp_length).decode()

                # read in data type. 0: Controller data; 1: Game Data
                self.data_type = RePlayDataFileStatic.read_byte_array(f, 'uint8')

                # read in the start time
                temp_time = RePlayDataFileStatic.read_byte_array(f, 'float64')
                self.session_start = RePlayDataFileStatic.convert_matlab_datenum_to_python_datetime(temp_time)

                #If this is file version 6, then let's read in a few more pieces of metadata
                if (self.version == 6):
                    # read in standard range for the current exercise
                    self.standard_range = RePlayDataFileStatic.read_byte_array(f, 'double')

                    # read in gain for the current exercise
                    self.gain = RePlayDataFileStatic.read_byte_array(f, 'double')

                    # read in actual range for the current exercise
                    self.actual_range = RePlayDataFileStatic.read_byte_array(f, 'double')

                # data location starts here
                self.__data_start_location = f.tell()

            elif self.version >= 7:

                # read in the start time
                temp = RePlayDataFileStatic.read_byte_array(f, 'float64')
                self.replay_build_date = RePlayDataFileStatic.convert_matlab_datenum_to_python_datetime(temp)

                # Read in the version name
                temp_name = RePlayDataFileStatic.read_byte_array(f, 'int32')
                self.replay_version_name = f.read(temp_name).decode()

                # Read in the version code
                temp_code = RePlayDataFileStatic.read_byte_array(f, 'int32')
                self.replay_version_code = f.read(temp_code).decode()

                # Read in the tablet ID
                temp_id = RePlayDataFileStatic.read_byte_array(f, 'int32')
                self.tablet_id = f.read(temp_id).decode()

                # Read in the subject id
                temp_length = RePlayDataFileStatic.read_byte_array(f, 'int32')
                self.subject_id = f.read(temp_length).decode()

                # read in the game id
                temp_length = RePlayDataFileStatic.read_byte_array(f, 'int32')
                self.game_id = f.read(temp_length).decode()

                # read in exercise id
                temp_length = RePlayDataFileStatic.read_byte_array(f, 'int32')
                self.exercise_id = f.read(temp_length).decode()

                # read in device type
                temp_length = RePlayDataFileStatic.read_byte_array(f, 'int32')
                self.device_type = f.read(temp_length).decode()

                # read in data type. 0: Controller data; 1: Game Data
                self.data_type = RePlayDataFileStatic.read_byte_array(f, 'uint8')

                # read in the start time
                temp_time = RePlayDataFileStatic.read_byte_array(f, 'float64')
                self.session_start = RePlayDataFileStatic.convert_matlab_datenum_to_python_datetime(temp_time)

                # read in standard range for the current exercise
                self.standard_range = RePlayDataFileStatic.read_byte_array(f, 'double')

                # read in gain for the current exercise
                self.gain = RePlayDataFileStatic.read_byte_array(f, 'double')

                # read in actual range for the current exercise
                self.actual_range = RePlayDataFileStatic.read_byte_array(f, 'double')

                #Read in a byte that indicates whether this session was launched from the "assignment" in RePlay
                if (self.version >= 10):
                    self.launched_from_assignment = RePlayDataFileStatic.read_byte_array(f, 'uint8')

                    #Read in VNS algorithm parameter information
                    if (self.version >= 11):
                        self.__read_vns_parameters_object(f)
                
                # data location starts here
                self.__data_start_location = f.tell()

            #Scan to end to figure out when to stop looping when reading game information
            if self.data_type == 0:
                # seek to the end of file and read the final 8 bytes
                f.seek(-8, 2)
                
                # grab the file position for end of data
                self.__data_end_location = f.tell()

                # grab the number of stimulations in the file
                self.total_stimulations = RePlayDataFileStatic.read_byte_array(f, 'int32')

                # grab the number of data samples in the file
                self.__total_frames = RePlayDataFileStatic.read_byte_array(f, 'int32')
                
            elif self.data_type == 1:
                # seek to the end of file and read the final 8 bytes
                f.seek(-4, 2)
                
                # grab the file position for end of data
                self.__data_end_location = f.tell()

                # grab the number of data samples in the file
                self.__total_frames = RePlayDataFileStatic.read_byte_array(f, 'int32')

            self.crash_detected = 0

    def AccessData(self):
        result = None

        if (self.exceeds_mongodb_size_limit):
            if (self.data_type == 0):
                if (self.controller_data_gridfs_in_memory is None):
                    data_bson = self.controller_data_gridfs.read()
                    if (data_bson is not None):
                        data_dict = BSON.decode(data_bson)
                        self.controller_data_gridfs_in_memory = RePlayControllerData._from_son(data_dict)
                        result = self.controller_data_gridfs_in_memory
                else:
                    result = self.controller_data_gridfs_in_memory
            elif (self.data_type == 1):
                if (self.game_data_gridfs_in_memory is None):
                    data_bson = self.game_data_gridfs.read()
                    if (data_bson is not None):
                        data_dict = BSON.decode(data_bson)

                        game_data = None
                        if self.game_id == 'FruitArchery':
                            game_data = RePlayGameDataFruitArchery._from_son(data_dict)
                        elif self.game_id == 'RepetitionsMode':
                            game_data = RePlayGameDataRepetitionsMode._from_son(data_dict)
                        elif self.game_id == 'ReCheck':
                            game_data = RePlayGameDataRepetitionsMode._from_son(data_dict)
                        elif self.game_id == 'TrafficRacer':
                            game_data = RePlayGameDataTrafficRacer._from_son(data_dict)
                        elif self.game_id == 'Breakout':
                            game_data = RePlayGameDataBreakout._from_son(data_dict)
                        elif self.game_id == 'SpaceRunner':
                            game_data = RePlayGameDataSpaceRunner._from_son(data_dict)
                        elif self.game_id == 'FruitNinja':
                            game_data = RePlayGameDataFruitNinja._from_son(data_dict)
                        elif self.game_id == 'TyperShark':
                            game_data = RePlayGameDataTyperShark._from_son(data_dict)
                        else:
                            game_data = RePlayGameData._from_son(data_dict)

                        self.game_data_gridfs_in_memory = game_data
                        result = game_data
                else:
                    result = self.game_data_gridfs_in_memory
        else:
            if (self.controller_data is not None):
                result = self.controller_data
            elif (self.game_data is not None):
                result = self.game_data

        return result

    def ReadData (self, trash_controller_device_data = False):
        if self.data_type == 0:
            self.__read_controller_data(trash_controller_device_data)

        elif self.data_type == 1:
            self.__read_game_data()

        else:
            print("Unidentified data type detected")

        self.__save_controller_and_game_data()

    def __read_vns_parameters_object (self, f):
        #Read in the VNS algorithm parameters "save version"
        vns_algo_params_save_version = RePlayDataFileStatic.read_byte_array(f, 'int32')

        #Read in the number of bytes saved as part of the VNS algo parameters
        vns_algo_params_num_bytes = RePlayDataFileStatic.read_byte_array(f, 'int32')

        #Read in the actual parameters
        vns_algo_enabled = RePlayDataFileStatic.read_byte_array(f, 'uint8')
        vns_algo_min_isi_ms = RePlayDataFileStatic.read_byte_array(f, 'double')
        vns_algo_desired_isi_ms = RePlayDataFileStatic.read_byte_array(f, 'double')
        vns_algo_selectivity = RePlayDataFileStatic.read_byte_array(f, 'double')
        vns_algo_compensatory_selectivity = RePlayDataFileStatic.read_byte_array(f, 'double')
        vns_algo_lookback_window = RePlayDataFileStatic.read_byte_array(f, 'double')
        vns_algo_smoothing_window = RePlayDataFileStatic.read_byte_array(f, 'double')
        vns_algo_noise_floor = RePlayDataFileStatic.read_byte_array(f, 'double')
        vns_algo_trig_pos = RePlayDataFileStatic.read_byte_array(f, 'uint8')
        vns_algo_trig_neg = RePlayDataFileStatic.read_byte_array(f, 'uint8')
        vns_algo_selectivity_controlled = RePlayDataFileStatic.read_byte_array(f, 'uint8')
        n = RePlayDataFileStatic.read_byte_array(f, 'int32')
        vns_algo_s1_smoothing = f.read(n).decode()
        n = RePlayDataFileStatic.read_byte_array(f, 'int32')
        vns_algo_s2_smoothing = f.read(n).decode()
        n = RePlayDataFileStatic.read_byte_array(f, 'int32')
        vns_algo_s1_operation = f.read(n).decode()
        n = RePlayDataFileStatic.read_byte_array(f, 'int32')
        vns_algo_s2_operation = f.read(n).decode()

        if vns_algo_s1_smoothing == "None":
            vns_algo_s1_smoothing = "NoSmoothing"
        if vns_algo_s2_smoothing == "None":
            vns_algo_s2_smoothing = "NoSmoothing"
        if vns_algo_s1_operation == "None":
            vns_algo_s1_operation = "NoOperation"

        if (vns_algo_params_save_version >= 2):
            vns_algo_typershark_lookback_size = RePlayDataFileStatic.read_byte_array(f, 'int32')
        else:
            vns_algo_typershark_lookback_size = float("NaN")

        if (vns_algo_params_save_version >= 3):
            n = RePlayDataFileStatic.read_byte_array(f, 'int32')
            vns_algo_lookback_expiration_policy = f.read(n).decode()
            vns_algo_lookback_window_capacity = RePlayDataFileStatic.read_byte_array(f, 'int32')
        else:
            vns_algo_lookback_expiration_policy = "TimeLimit"
            vns_algo_lookback_window_capacity = 0

        if (vns_algo_params_save_version >= 4):
            vns_algo_kernel_size = RePlayDataFileStatic.read_byte_array(f, 'double')
        else:
            vns_algo_kernel_size = 0

        #Create a vns algorithm parameters object and property on the class
        self.vns_algorithm_parameters = RePlayVNSParameters()
        self.vns_algorithm_parameters.Enabled = bool(vns_algo_enabled)
        self.vns_algorithm_parameters.Minimum_ISI = timedelta(milliseconds=vns_algo_min_isi_ms)
        self.vns_algorithm_parameters.Desired_ISI = timedelta(milliseconds=vns_algo_desired_isi_ms)
        self.vns_algorithm_parameters.Selectivity = vns_algo_selectivity
        self.vns_algorithm_parameters.CompensatorySelectivity = vns_algo_compensatory_selectivity
        self.vns_algorithm_parameters.LookbackWindow = timedelta(milliseconds=vns_algo_lookback_window)
        self.vns_algorithm_parameters.SmoothingWindow = timedelta(milliseconds=vns_algo_smoothing_window)
        self.vns_algorithm_parameters.NoiseFloor = vns_algo_noise_floor
        self.vns_algorithm_parameters.TriggerOnPositive = bool(vns_algo_trig_pos)
        self.vns_algorithm_parameters.TriggerOnNegative = bool(vns_algo_trig_neg)
        self.vns_algorithm_parameters.SelectivityControlledByDesiredISI = bool(vns_algo_selectivity_controlled)
        self.vns_algorithm_parameters.Stage1_Smoothing = SmoothingOptions[vns_algo_s1_smoothing]
        self.vns_algorithm_parameters.Stage2_Smoothing = SmoothingOptions[vns_algo_s2_smoothing]
        self.vns_algorithm_parameters.Stage1_Operation = Stage1_Operations[vns_algo_s1_operation]
        self.vns_algorithm_parameters.Stage2_Operation = Stage2_Operations[vns_algo_s2_operation]
        self.vns_algorithm_parameters.TyperSharkLookbackSize = vns_algo_typershark_lookback_size
        self.vns_algorithm_parameters.VNS_AlgorithmParameters_SaveVersion = vns_algo_params_save_version
        self.vns_algorithm_parameters.LookbackWindowExpirationPolicy = BufferExpirationPolicy[vns_algo_lookback_expiration_policy]
        self.vns_algorithm_parameters.LookbackWindowCapacity = vns_algo_lookback_window_capacity
        self.vns_algorithm_parameters.SmoothingKernelSize = timedelta(milliseconds=vns_algo_kernel_size)

    def SaveControllerAndGameData (self):
        self.__save_controller_and_game_data()

    def __save_controller_and_game_data(self):
        #The MongoDB size limit for documents is 16 MB. 
        #If we exceed this size, we need to use GridFS to large document storage
        size_limit = 16777216

        #Check the size of the current object when encoded into BSON
        if (self.controller_data is not None):
            controller_data_bson_encoded = BSON.encode(self.controller_data.to_mongo())
            if (len(controller_data_bson_encoded) > size_limit):
                self.controller_data_gridfs.new_file()
                self.controller_data_gridfs.write(controller_data_bson_encoded)
                self.controller_data_gridfs.close()
                self.controller_data = None
                self.exceeds_mongodb_size_limit = True
            else:
                self.controller_data.save()


        elif (self.game_data is not None):
            game_data_bson_encoded = BSON.encode(self.game_data.to_mongo())
            if (len(game_data_bson_encoded) > size_limit):
                self.game_data_gridfs.new_file()
                self.game_data_gridfs.write(game_data_bson_encoded)
                self.game_data_gridfs.close()
                self.game_data = None
                self.exceeds_mongodb_size_limit = True
            else:
                self.game_data.save()

    def __read_controller_data(self, trash_controller_device_data):
        self.controller_data = RePlayControllerData()
        self.controller_data.ReadControllerData(self.filepath, self.device_type, self.__data_start_location, trash_controller_device_data)

    def __read_game_data(self):    
        #Determine what kind of object we need to create based on which game was played
        if self.game_id == 'FruitArchery':
            self.game_data = RePlayGameDataFruitArchery()
        elif self.game_id == 'RepetitionsMode':
            self.game_data = RePlayGameDataRepetitionsMode()
        elif self.game_id == 'ReCheck':
            self.game_data = RePlayGameDataRepetitionsMode()
        elif self.game_id == 'TrafficRacer':
            self.game_data = RePlayGameDataTrafficRacer()
            self.game_data.DefineRePlayVersion(self.replay_version_code)
        elif self.game_id == 'Breakout':
            self.game_data = RePlayGameDataBreakout()
        elif self.game_id == 'SpaceRunner':
            self.game_data = RePlayGameDataSpaceRunner()
        elif self.game_id == 'FruitNinja':
            self.game_data = RePlayGameDataFruitNinja()
        elif self.game_id == 'TyperShark':
            self.game_data = RePlayGameDataTyperShark()
            self.game_data.DefineVersion(self.version)
        else:
            self.game_data = RePlayGameData()

        #Read the game data for this game session
        self.game_data.ReadGameData(self.filepath, self.filepath, self.__data_start_location)
        if ((int(self.replay_version_code) >= 30) or 
            ((self.game_id == 'ReCheck') and (int(self.replay_version_code) >= 11))):
            
            self.game_data.DetermineSignal(
                int(self.replay_version_code), 
                self.game_id, 
                self.exercise_id, 
                self.gain, 
                self.standard_range)
        else:
            self.__convert_signal_to_actual_signal()

    def __convert_signal_to_actual_signal(self):
        
        #This function takes the signal from the game_self and converts it in to the "actual" signal, which is
        #a real unit such as grams, degrees, etc.

        #Check the list of changes for the different versions of replay to understand why certain values need to be converted
        #For details: https://docs.google.com/document/d/1wh-MwtG-2Y4iCSw5NpmOZo-8WCiXHdiuKi9bg1N4t_o/edit?usp=sharing
        if self.version <= 6:
            #Loadcell values on pucks can be multiplied by 19.230769 to convert the analog value to Grams

            controller_sensitivity={}

            #Weak
            controller_sensitivity['RepetitionsMode'] = {'Isometric Handle': 50, 'Isometric Knob': 50, 'Isometric Wrist': 50, 'Isometric Pinch': 50,
                    'Isometric Pinch Left': 50, 'Range of Motion Handle': 50, 'Range of Motion Knob': 50, 'Range of Motion Wrist': 50, 
                    'Flipping': 50, 'Supination': 50, 'Finger Twists': 50, 'Flyout': 50, 'Wrist Flexion': 50, 'Bicep Curls': 10, 'Rolling': 10, 
                    'Shoulder Abduction': 10, 'Shoulder Extension': 10, 'Wrist Deviation': 10, 'Rotate': 10, 'Grip': 50, 'Touches': 50, 
                    'Clapping': 50, 'Finger Tap': 50, 'Key Pinch': 50, 'Reach Across': 50, 'Reach Diagonal': 50, 'Reach Out': 50, 'Thumb Opposition': 50}

            
            #Medium 
            controller_sensitivity['Breakout'] = {'Isometric Handle': 100, 'Isometric Knob': 100, 'Isometric Wrist': 100, 'Isometric Pinch': 100,
                    'Isometric Pinch Left': 100, 'Range of Motion Handle': 100, 'Range of Motion Knob': 100, 'Range of Motion Wrist': 100, 
                    'Flipping': 100, 'Supination': 100, 'Finger Twists': 100, 'Flyout': 100, 'Wrist Flexion': 100, 'Bicep Curls': 25, 'Rolling': 25, 
                    'Shoulder Abduction': 25, 'Shoulder Extension': 25, 'Wrist Deviation': 25, 'Rotate': 25, 'Grip': 100, 'Touches': 100, 
                    'Clapping': 100, 'Finger Tap': 100, 'Key Pinch': 100, 'Reach Across': 100, 'Reach Diagonal': 100, 'Reach Out': 100, 'Thumb Opposition': 100}

            
            #Weak
            controller_sensitivity['TrafficRacer'] = {'Isometric Handle': 50, 'Isometric Knob': 50, 'Isometric Wrist': 50, 'Isometric Pinch': 50,
                    'Isometric Pinch Left': 50, 'Range of Motion Handle': 50, 'Range of Motion Knob': 50, 'Range of Motion Wrist': 50, 
                    'Flipping': 50, 'Supination': 50, 'Finger Twists': 50, 'Flyout': 50, 'Wrist Flexion': 50, 'Bicep Curls': 10, 'Rolling': 10, 
                    'Shoulder Abduction': 10, 'Shoulder Extension': 10, 'Wrist Deviation': 10, 'Rotate': 10, 'Grip': 50, 'Touches': 50, 
                    'Clapping': 50, 'Finger Tap': 50, 'Key Pinch': 50, 'Reach Across': 50, 'Reach Diagonal': 50, 'Reach Out': 50, 'Thumb Opposition': 50}

                
            #Medium 
            controller_sensitivity['SpaceRunner'] = {'Isometric Handle': 100, 'Isometric Knob': 100, 'Isometric Wrist': 100, 'Isometric Pinch': 100,
                    'Isometric Pinch Left': 100, 'Range of Motion Handle': 100, 'Range of Motion Knob': 100, 'Range of Motion Wrist': 100, 
                    'Flipping': 100, 'Supination': 100, 'Finger Twists': 100, 'Flyout': 100, 'Wrist Flexion': 100, 'Bicep Curls': 25, 'Rolling': 25, 
                    'Shoulder Abduction': 25, 'Shoulder Extension': 25, 'Wrist Deviation': 25, 'Rotate': 25, 'Grip': 100, 'Touches': 100, 
                    'Clapping': 100, 'Finger Tap': 100, 'Key Pinch': 100, 'Reach Across': 100, 'Reach Diagonal': 100, 'Reach Out': 100, 'Thumb Opposition': 100}

            

            #If this is a game we can apply gain to
            if self.game_id in ['Breakout', 'SpaceRunner', 'TrafficRacer']:
                gain = controller_sensitivity[self.game_id][self.exercise_id]
                self.game_data.signal_actual = list(np.asarray(self.game_data.signal) * gain)
            elif self.game_id == 'FruitArchery':
                self.game_data.signal_actual = self.game_data.signal
            elif self.game_id == 'RepetitionsMode':
                #In Repetitions Mode, when the Exercise_SaveData file version was 6 or below, we saved out
                #raw data to the data file, NOT normalized data. No gain factor was applied to the saved data.
                #Therefore, we will not multiply the signal by any gain factor in the following code.
                self.game_data.signal_actual = self.game_data.signal
            else:
                pass
        
        #in version >= 7, the actual_range was saved so we can convert using that value instead of that table above
        else:
            if self.game_id in ['Breakout', 'SpaceRunner', 'TrafficRacer']:
                self.game_data.signal_actual = list(np.asarray(self.game_data.signal) * self.actual_range)

            elif self.game_id in ['FruitArchery', 'RepetitionsMode', 'ReCheck']:
                if (int(self.replay_version_code) >= 27):
                    self.game_data.signal_actual = self.game_data.signal_not_normalized
                elif (self.replay_build_date > datetime(2019, 11, 19)):
                    #In Repetitions Mode, all saved data files with versions 7 or above used game data file version 3 or above.
                    #On November 19th 2019, a change was made to the Repetitions Mode data files. They now save the normalized data
                    #instead of the raw data. Therefore, we need to account for this. All data files that come from a build
                    #of RePlay with a build data that is November 19th 2019 or later need to multiply by the gain factor to get
                    #the real data.                    
                    self.game_data.signal_actual = list(np.asarray(self.game_data.signal) * self.actual_range)
                else:
                    self.game_data.signal_actual = self.game_data.signal
            else:
                pass

