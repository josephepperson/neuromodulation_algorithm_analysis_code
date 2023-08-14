from mongoengine import *
import hashlib
import json
import os

class ReTrieveDataFile(Document):
    meta = {
        'collection':'ReTrieveDataFile'
    }    

    md5_checksum = StringField()
    filepath = StringField()
    filename = StringField()
    json_data = DictField()

    def __init__(self, *args, **values):
        super().__init__(*args, **values)

    def __calculate_md5_checksum(self):
        hash_md5 = hashlib.md5()
        if (os.path.exists(self.filepath)):
            with open(self.filepath, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            self.md5_checksum = hash_md5.hexdigest()

    def ReadFile(self, filepath):
        #Save the filepath
        self.filepath = filepath
        self.filename = os.path.basename(filepath)

        #Calculate the md5 checksum of the file
        self.__calculate_md5_checksum()

        #Read in the JSON data
        if (os.path.exists(filepath)):
            with open(filepath) as json_file:
                self.json_data = json.load(json_file)     
