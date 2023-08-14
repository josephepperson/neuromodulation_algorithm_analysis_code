from mongoengine import *
from .CustomFields.CustomFields import *
import pandas

from datetime import datetime
from datetime import timedelta
from dateutil import parser

class ReStoreStimulation(Document):
    meta = {
        'collection':'ReStoreStimulations'
    }        

    ipg_id = StringField()
    is_successful = BooleanField()
    stimulation_datetime = DateTimeField()
    stimulation_details = DictField()

    uid = StringField()
    file_name = StringField()
    md5_checksum = StringField()

    #Constructor
    def __init__(self, *args, **values):
        super().__init__(*args, **values)

    def populate_record(self, ipg_id, is_successful, stim_dt, stim_details):
        self.ipg_id = ipg_id
        self.is_successful = is_successful
        self.stimulation_datetime = stim_dt
        self.stimulation_details = stim_details

    def populate_record_known_uid(self, uid, ipg_id, is_successful, stim_dt, stim_details):
        self.uid = uid
        self.ipg_id = ipg_id
        self.is_successful = is_successful
        self.stimulation_datetime = stim_dt
        self.stimulation_details = stim_details        

class ReStoreStimulationCollection:

    @staticmethod
    def AppendStimToCollection_UnknownUID (ipg_id, is_successful, stim_dt, stim_details):
        x = ReStoreStimulation()
        x.populate_record(ipg_id, is_successful, stim_dt, stim_details)
        x.save()        

    @staticmethod
    def AppendStimToCollection_KnownUID (uid, ipg_id, is_successful, stim_dt, stim_details):
        x = ReStoreStimulation()
        x.populate_record_known_uid(uid, ipg_id, is_successful, stim_dt, stim_details)
        x.save()

        