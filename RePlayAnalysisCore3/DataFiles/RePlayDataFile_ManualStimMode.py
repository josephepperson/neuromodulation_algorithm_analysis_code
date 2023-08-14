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

class RePlayDataFile_ManualStimMode(Document):
    meta = {
        'collection':'RePlayDataFile_ManualStimMode'
    }    
        
    subject_id = StringField(max_length = 200)
    game_id = StringField(max_length=200, default="Manual Stimulation")
    md5_checksum = StringField(default = None)
    filename = StringField()
    stim_request_times_all = ListField(DateTimeField())
    stim_request_times_sent_to_restore = ListField(DateTimeField())
    successful_stim_times = ListField(DateTimeField())
    failed_stim_times = ListField(DateTimeField())
    messages_datetimes = ListField(DateTimeField())
    messages = ListField(StringField())
    full_messages_datetimes = ListField(DateTimeField())
    full_messages = ListField(StringField())
    start_time = DateTimeField(default = None)
    end_time = DateTimeField(default = None)
    duration = FloatField(default = 0)
    
    def __init__(self, *args, **values):
        super().__init__(*args, **values)

    def InitiateFileRead(self, filepath, uid):
        self.filename = filepath
        self.subject_id = uid
        self.__md5_checksum()

    # This method calculates the md5 checksum of the file's contents
    # This can be used for file verification
    def __md5_checksum(self):
        hash_md5 = hashlib.md5()
        with open(self.filename, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        self.md5_checksum = hash_md5.hexdigest()         

    def parse_file (self):
        lines = []
        with open(self.filename, 'rb') as f:
            lines = f.readlines()
        
        #Iterate over each line from the file
        for i in range(0, len(lines)):
            #Get the current line
            current_line = lines[i].decode()

            #The first thing on each line is a time/date stamp, surrounded by parantheses.
            first_close_paren = current_line.find(')')
            if (first_close_paren > -1):
                ds_string = current_line[1:first_close_paren]
                ds_obj = datetime.strptime(ds_string, '%m/%d/%Y %I:%M:%S %p')
                current_message = current_line[first_close_paren+1:].strip()
                self.full_messages_datetimes.append(ds_obj)
                self.full_messages.append(current_message)

        self.analyze_messages()

    def analyze_messages (self):        
        #Make sure this object is clear
        self.stim_request_times_all = []
        self.stim_request_times_sent_to_restore = []
        self.successful_stim_times = []
        self.failed_stim_times = []
        self.messages_datetimes = []
        self.messages = []
        self.start_time = None
        self.end_time = None
        self.duration = 0

        #Iterate over each line from the file
        for i in range(0, len(self.full_messages)):
            #Get the current message
            current_message = self.full_messages[i]

            #Get the datetime of the current message
            ds_obj = self.full_messages_datetimes[i]

            #Check to see what kind of message this is
            if (current_message.find('Sent PCM status check request') > -1):
                pass
            elif (current_message.find('Return Message from ReStore') > -1):
                if (current_message.find('COMMAND_STATUS = STIM_SUCCESS') > -1):
                    self.successful_stim_times.append(ds_obj)
                elif (current_message.find('COMMAND_STATUS = STIM_FAILURE') > -1):
                    self.failed_stim_times.append(ds_obj)
            elif (current_message.find('Sent stim trigger request') > -1):
                self.stim_request_times_sent_to_restore.append(ds_obj)
            elif (current_message.find('A stimulation request was issued by touching the YELLOW puck.') > -1):
                self.stim_request_times_all.append(ds_obj)
            else:
                self.messages_datetimes.append(ds_obj)
                self.messages.append(current_message)

        if (len(self.full_messages_datetimes) > 0):
            self.start_time = self.full_messages_datetimes[0]
            if (len(self.full_messages_datetimes) > 1):    
                self.end_time = self.full_messages_datetimes[-1]
                self.duration = (self.end_time - self.start_time).total_seconds()
            else:
                self.duration = 0        