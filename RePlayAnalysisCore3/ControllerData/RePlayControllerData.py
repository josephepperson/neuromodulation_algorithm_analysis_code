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

from RePlayAnalysisCore3.CustomFields.CustomFields import *
from RePlayAnalysisCore3.GameData.RePlayGameData import RePlayGameData
from RePlayAnalysisCore3.DataFiles.RePlayDataFileStatic import RePlayDataFileStatic

class RePlayControllerData(Document):
    meta = {
        'allow_inheritance': True,
        'collection':'RePlayControllerData'
    }

    controller_data_file_version = IntField()
    filename = StringField()
    device_type = StringField()
    is_session_handedness_known = BooleanField()
    is_session_left_handed = BooleanField()
    signal_time = ListField(FloatField())
    signal_timenum = ListField(DateTimeField())
    signal_timeelapsed = ListField(TimedeltaField())
    stim_times = ListField(DateTimeField())
    stim_times_successful = ListField(DateTimeField())
    restore_messages = ListField(DynamicField())

    gyro = ListField(DynamicField())
    acc = ListField(DynamicField())
    mag = ListField(DynamicField())
    quat = ListField(DynamicField())
    loadcell = ListField(DynamicField())
    touch = ListField(DynamicField())
    battery = ListField(DynamicField())

    replay_signal = ListField(FloatField())
    replay_loadcell1_signal = ListField(FloatField())
    replay_loadcell2_signal = ListField(FloatField())
    replay_calibration_data = ListField(DynamicField())

    touch_position = ListField(DynamicField())

    def __init__(self, *args, **values):
        super().__init__(*args, **values)

    def ReadControllerData(self, filename, device_type, data_start_location, trash_device_data = False):
        self.controller_data_file_version = 0

        self.filename = filename
        self.device_type = device_type
        self.__data_start_location = data_start_location
        self.is_session_handedness_known = False
        self.is_session_left_handed = False        

        # pre-allocate all of the numpy arrays
        self.signal_time = []
        self.signal_timenum = []
        self.signal_timeelapsed = []
        self.stim_times = []
        self.stim_times_successful = []
        self.restore_messages = []

        #Grab the file size in bytes
        flength = os.stat(self.filename).st_size

        if self.device_type == 'FitMi':
            self.gyro = []
            self.acc = []
            self.mag = []
            self.quat = []
            self.loadcell = []
            self.touch = []
            self.battery = []
        
        elif ((self.device_type == 'RePlay') or (self.device_type == 'ReCheck')):
            self.replay_signal = []
            self.replay_loadcell1_signal = []
            self.replay_loadcell2_signal = []
            self.replay_calibration_data = []

        elif self.device_type == 'Touchscreen':
            self.touch_position = []
        else:
            print("Unidentified controller detected")
            return

        with open(self.filename, 'rb') as f:
            f.seek(self.__data_start_location)
            try:
                while (f.tell() < flength - 8):
                    f_tell = f.tell()
                    packet_type = RePlayDataFileStatic.read_byte_array(f, 'int')

                    # if this is a puck data packet id = 1
                    if packet_type == 1:
                        timenum_read = RePlayDataFileStatic.read_byte_array(f, 'float64')
                        self.signal_timenum.append(RePlayDataFileStatic.convert_matlab_datenum_to_python_datetime(timenum_read))
                        self.signal_timeelapsed.append(self.signal_timenum[-1]-self.signal_timenum[0])
                        self.signal_time.append(self.signal_timeelapsed[-1].total_seconds())

                        packet_acc_data = []
                        packet_gyro_data = []
                        packet_mag_data = []
                        packet_quat_data = []
                        packet_loadcell = []
                        packet_touch = []
                        packet_battery = []

                        # Loop through both pucks
                        for _ in itertools.repeat(None, 2):

                            #skip over the next puck identifier int32
                            puck_num = RePlayDataFileStatic.read_byte_array(f, 'int32')

                            #store the 3axis acceleration data in to a temporary list
                            acc_data = []
                            acc_data.append(RePlayDataFileStatic.read_byte_array(f, 'int32'))
                            acc_data.append(RePlayDataFileStatic.read_byte_array(f, 'int32'))
                            acc_data.append(RePlayDataFileStatic.read_byte_array(f, 'int32'))
                            packet_acc_data.append(acc_data)

                            #store the 3axis gyro data in to a temporary list
                            gyro_data = []
                            gyro_data.append(RePlayDataFileStatic.read_byte_array(f, 'int32'))
                            gyro_data.append(RePlayDataFileStatic.read_byte_array(f, 'int32'))
                            gyro_data.append(RePlayDataFileStatic.read_byte_array(f, 'int32'))
                            packet_gyro_data.append(gyro_data)

                            #store the 3axis mag data in to a temporary list
                            mag_data = []
                            mag_data.append(RePlayDataFileStatic.read_byte_array(f, 'double'))
                            mag_data.append(RePlayDataFileStatic.read_byte_array(f, 'double'))
                            mag_data.append(RePlayDataFileStatic.read_byte_array(f, 'double'))
                            packet_mag_data.append(mag_data)

                            quat_data = []
                            quat_data.append(RePlayDataFileStatic.read_byte_array(f, 'double'))
                            quat_data.append(RePlayDataFileStatic.read_byte_array(f, 'double'))
                            quat_data.append(RePlayDataFileStatic.read_byte_array(f, 'double'))
                            quat_data.append(RePlayDataFileStatic.read_byte_array(f, 'double'))
                            packet_quat_data.append(quat_data)

                            packet_loadcell.append(RePlayDataFileStatic.read_byte_array(f, 'int32'))
                            packet_touch.append(RePlayDataFileStatic.read_byte_array(f, 'int8'))
                            packet_battery.append(RePlayDataFileStatic.read_byte_array(f, 'int32'))


                        self.acc.append(packet_acc_data)
                        self.gyro.append(packet_gyro_data)
                        self.mag.append(packet_mag_data)
                        self.quat.append(packet_quat_data)

                        self.loadcell.append(packet_loadcell)
                        self.touch.append(packet_touch)
                        self.battery.append(packet_battery)

                    #if this is a replay data packet
                    elif packet_type == 2:
                        timenum_read = RePlayDataFileStatic.read_byte_array(f, 'float64')
                        self.signal_timenum.append(RePlayDataFileStatic.convert_matlab_datenum_to_python_datetime(timenum_read))
                        self.signal_timeelapsed.append(self.signal_timenum[-1]-self.signal_timenum[0])
                        self.signal_time.append(self.signal_timeelapsed[-1].total_seconds())

                        self.replay_signal.append(RePlayDataFileStatic.read_byte_array(f, 'double'))

                    # if this is a stim packet
                    elif packet_type == 3:
                        timenum_read = RePlayDataFileStatic.read_byte_array(f, 'float64')
                        self.stim_times.append(RePlayDataFileStatic.convert_matlab_datenum_to_python_datetime(timenum_read))

                    #if this is a touchscreen packet
                    elif packet_type == 4:
                        timenum_read = RePlayDataFileStatic.read_byte_array(f, 'float64')
                        self.signal_timenum.append(RePlayDataFileStatic.convert_matlab_datenum_to_python_datetime(timenum_read))
                        self.signal_timeelapsed.append(self.signal_timenum[-1]-self.signal_timenum[0])
                        self.signal_time.append(self.signal_timeelapsed[-1].total_seconds())

                        touch_pos = []
                        touch_pos.append(RePlayDataFileStatic.read_byte_array(f, 'float'))
                        touch_pos.append(RePlayDataFileStatic.read_byte_array(f, 'float'))
                        self.touch_position.append(touch_pos)
            
                    #This handles any messages from ReStore that were saved into the file
                    elif packet_type == 5:
                        restore_msg = RePlayDataFileStatic.read_restore_message(f)
                        self.restore_messages.append(restore_msg)
                        if (("secondary" in restore_msg) and ("time" in restore_msg)):
                            time = restore_msg["time"]
                            secondary = restore_msg["secondary"]
                            if ("COMMAND_STATUS" in secondary):
                                is_stim_success = secondary["COMMAND_STATUS"]
                                if (is_stim_success == "STIM_SUCCESS"):
                                    self.stim_times_successful.append(time)

                    #This handles reading RePlay isometric task raw values
                    elif packet_type == 6:
                        timenum_read = RePlayDataFileStatic.read_byte_array(f, 'float64')
                        lc1_val = RePlayDataFileStatic.read_byte_array(f, 'float64')
                        lc2_val = RePlayDataFileStatic.read_byte_array(f, 'float64')
                        self.signal_timenum.append(RePlayDataFileStatic.convert_matlab_datenum_to_python_datetime(timenum_read))
                        self.signal_timeelapsed.append(self.signal_timenum[-1]-self.signal_timenum[0])
                        self.signal_time.append(self.signal_timeelapsed[-1].total_seconds())
                        self.replay_loadcell1_signal.append(lc1_val)
                        self.replay_loadcell2_signal.append(lc2_val)

                    #This handles reading RePlay isometric task calibration values
                    elif packet_type == 7:
                        timenum_read = RePlayDataFileStatic.read_byte_array(f, 'float64')
                        b1_val = RePlayDataFileStatic.read_byte_array(f, 'float64')
                        b2_val = RePlayDataFileStatic.read_byte_array(f, 'float64')
                        s1_val = RePlayDataFileStatic.read_byte_array(f, 'float64')
                        s2_val = RePlayDataFileStatic.read_byte_array(f, 'float64')

                        calibration_tuple = (timenum_read, b1_val, b2_val, s1_val, s2_val)
                        self.replay_calibration_data.append(calibration_tuple)

                    #This handles reading RePlay range-of-motion task calibration values
                    elif packet_type == 8:
                        timenum_read = RePlayDataFileStatic.read_byte_array(f, 'float64')
                        b1_val = RePlayDataFileStatic.read_byte_array(f, 'float64')

                        calibration_tuple = (timenum_read, b1_val)
                        self.replay_calibration_data.append(calibration_tuple)

                    #This handles reading the handedness of the session
                    elif packet_type == 9:
                        timenum_read = RePlayDataFileStatic.read_byte_array(f, 'float64')
                        is_left_handed_int8 = RePlayDataFileStatic.read_byte_array(f, 'int8')
                        self.is_session_handedness_known = True
                        self.is_session_left_handed = False
                        if (is_left_handed_int8 == 1):
                            self.is_session_left_handed = True
                        
                    else:
                        pass
            except ValueError:
                print(f'\nGame Crash detected during read of file: {self.filename}')
                self.crash_detected = 1
        
        #If the user has specified that the controller device data should be trashed...
        #(This is normally a space-saving measure, since the device data is used less often than the game data)
        if trash_device_data:
            self.signal_time = []
            self.signal_timenum = []
            self.signal_timeelapsed = []

            if self.device_type == 'FitMi':
                self.gyro = []
                self.acc = []
                self.mag = []
                self.quat = []
                self.loadcell = []
                self.touch = []
                self.battery = []
            
            elif ((self.device_type == 'RePlay') or (self.device_type == 'ReCheck')):
                self.replay_signal = []
                self.replay_loadcell1_signal = []
                self.replay_loadcell2_signal = []
                self.replay_calibration_data = []

            elif self.device_type == 'Touchscreen':
                self.touch_position = []         




