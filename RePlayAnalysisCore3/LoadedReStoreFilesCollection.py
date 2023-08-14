from mongoengine import *
from .CustomFields.CustomFields import *
import pandas

from datetime import datetime
from datetime import timedelta
from dateutil import parser

class LoadedReStoreFileRecord(Document):
    meta = {
        'collection':'LoadedReStoreFiles'
    }    

    file_name = StringField()
    md5_checksum = StringField()
    file_size = IntField()

    #Constructor
    def __init__(self, *args, **values):
        super().__init__(*args, **values)

    def populate_record(self, filename, md5checksum, filesize):
        self.file_name = filename
        self.md5_checksum = md5checksum
        self.file_size = filesize

class LoadedReStoreFilesCollection:
    
    @staticmethod
    def IsFileAlreadyLoaded_FileNameCheckOnly (filename):
        return (LoadedReStoreFileRecord.objects(file_name=filename).count() > 0)

    @staticmethod
    def IsFileAlreadyLoaded_FileNameAndSizeCheck (filename, filesize):
        return (LoadedReStoreFileRecord.objects(
            Q(file_name=filename) & Q(file_size=filesize)
        ).count() > 0)

    @staticmethod
    def IsFileAlreadyLoaded_ComprehensiveCheck (filename, filesize, checksum):
        return (LoadedReStoreFileRecord.objects(
            Q(file_name=filename) & Q(file_size=filesize) & Q(md5_checksum=checksum)
        ).count() > 0)

    @staticmethod
    def AppendFileToCollection (filename, md5checksum, filesize):
        x = LoadedReStoreFileRecord()
        x.populate_record(filename, md5checksum, filesize)
        x.save()
  


