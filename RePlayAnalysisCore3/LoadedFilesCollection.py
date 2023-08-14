from mongoengine import *
from .CustomFields.CustomFields import *
import pandas

from datetime import datetime
from datetime import timedelta
from dateutil import parser

class LoadedFileRecord(Document):
    meta = {
        'collection':'LoadedFiles'
    }    

    uid = StringField()
    file_name = StringField()
    md5_checksum = StringField()

    #Constructor
    def __init__(self, *args, **values):
        super().__init__(*args, **values)

    def populate_record(self, uid, filename, md5checksum):
        self.uid = uid
        self.file_name = filename
        self.md5_checksum = md5checksum

class LoadedFilesCollection:
    
    @staticmethod
    def IsFileAlreadyLoaded_Shallow (filename):
        return (LoadedFileRecord.objects(file_name=filename).count() > 0)

    @staticmethod
    def IsFileAlreadyLoaded_Deep (filename, md5checksum):
        return (LoadedFileRecord.objects(
            Q(file_name=filename) & Q(md5_checksum=md5checksum)
        ).count() > 0)

    @staticmethod
    def IsFileAlreadyLoaded (filename, md5checksum = None):        
        if (md5checksum is None):
            return LoadedFilesCollection.IsFileAlreadyLoaded_Shallow(filename)
        else:
            return LoadedFilesCollection.IsFileAlreadyLoaded_Deep(filename, md5checksum)

    @staticmethod
    def AppendFileToCollection (participant_id, filename, md5checksum):
        x = LoadedFileRecord()
        x.populate_record(participant_id, filename, md5checksum)
        x.save()
  


