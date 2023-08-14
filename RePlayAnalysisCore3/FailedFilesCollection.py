from mongoengine import *
from .CustomFields.CustomFields import *
import pandas

from datetime import datetime
from datetime import timedelta
from dateutil import parser

class FailedFileRecord(Document):
    meta = {
        'collection':'FailedFiles'
    }    

    file_name = StringField()

    #Constructor
    def __init__(self, *args, **values):
        super().__init__(*args, **values)

    def populate_record(self, filename):
        self.file_name = filename

class FailedFilesCollection:
    
    @staticmethod
    def IsFileAlreadyLoaded_Shallow (filename):
        return (FailedFileRecord.objects(file_name=filename).count() > 0)

    @staticmethod
    def IsFileAlreadyLoaded (filename):
        return FailedFilesCollection.IsFileAlreadyLoaded_Shallow(filename)

    @staticmethod
    def AppendFileToCollection (filename):
        x = FailedFileRecord()
        x.populate_record(filename)
        x.save()
  


