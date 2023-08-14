from mongoengine import *
import json
import pandas
import hashlib

class ReStoreDataFile(Document):
    meta = {
        'collection':'ReStoreDataFile'
    }

    filename = StringField()
    md5_checksum = StringField()
    pcm_events = ListField(StringField())
    pcm_events_secret = ListField(StringField())
    
    def __init__(self, *args, **values):
        super().__init__(*args, **values)

    # This method calculates the md5 checksum of the file's contents
    # This can be used for file verification
    def __md5_checksum(self):
        hash_md5 = hashlib.md5()
        with open(self.filename, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        self.md5_checksum = hash_md5.hexdigest()         

    def ReadFile(self, full_path, debug = False):
        #Save the filename
        self.filename = full_path

        #Calculate and save the md5 checksum of the file
        self.__md5_checksum()

        #Create an empty list to hold all of the PCM events
        self.pcm_events = []

        #Create a second empty list to hold SECRET events. We, as researchers, are BLINDED to these events.
        self.pcm_events_secret = []

        #Iterate through each line of the log file and parse each line.
        encoded_str = ""
        success_count = 0
        error_count = 0
        secret_count = 0
        with open(full_path, 'r') as json_file:
            file_lines = json_file.readlines()
            for line in file_lines:
                try:
                    #Attempt to the parse the line as JSON
                    result = json.loads(line)

                    #If parsing was successful, then add this PCM event to the list of all PCM events
                    self.pcm_events.append(result)
                    success_count += 1

                    #If parsing was successful, then check and see if we have previously loaded a blinded event
                    if (len(encoded_str) > 0):
                        #If so, add the completed blinded event to the list of all blinded events
                        self.pcm_events_secret.append(encoded_str)
                        encoded_str = ""
                        secret_count += 1            
                except:
                    #If parsing was unsuccessful, then treat this line as part of a blinded event.
                    line = line.strip()
                    encoded_str += line
                    error_count += 1

        #At the end, check and see if we have one last blinded event to add to the list of blinded events
        if (len(encoded_str) > 0):
            self.pcm_events_secret.append(encoded_str)
            encoded_str = ""
            secret_count += 1            

        #If the debugging flag is set to True, then print out some information about this file.
        if (debug):
            print(f"Non-blinded events: {success_count}")
            print(f"Blinded events: {secret_count}")

            all_event_commands = [x["COMMAND"] for x in self.pcm_events]
            all_unique_event_commands = set(all_event_commands)

            command_count_dict = {}
            for c in all_unique_event_commands:
                command_count_dict[c] = 0

            for pcm_event_command in all_event_commands:
                command_count_dict[pcm_event_command] += 1

            df = pandas.DataFrame(list(command_count_dict.items()),columns = ['COMMAND','COUNT'])
            print("")
            print("Summary of non-blinded events: ")
            print(df)