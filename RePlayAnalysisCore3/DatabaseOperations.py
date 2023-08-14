from multiprocessing.managers import BaseManager
from mongoengine import *

import sys
import os.path as o
import ntpath
import pandas
import os
from os import walk
from os import listdir
from os.path import isfile, join
from pathlib import Path
import colorama
from colorama import Fore
from colorama import Style
import traceback
import json
from py_linq import Enumerable
from datetime import datetime
import time
import math

from RePlayAnalysisCore3.LoadedFilesCollection import *
from RePlayAnalysisCore3.FailedFilesCollection import *
from RePlayAnalysisCore3.Activities.BaseActivity import BaseActivity
from RePlayAnalysisCore3.Activities.RePlayActivity_ManualStimMode import RePlayActivity_ManualStimMode
from RePlayAnalysisCore3.Activities.ReTrieveActivity import ReTrieveActivity
from RePlayAnalysisCore3.Activities.RePlayActivity import RePlayActivity
from RePlayAnalysisCore3.Activities.RePlayActivity_ManualStimMode import RePlayActivity_ManualStimMode
from RePlayAnalysisCore3.DataFiles.RePlayDataFile import RePlayDataFile
from RePlayAnalysisCore3.DataFiles.RePlayDataFile_ManualStimMode import RePlayDataFile_ManualStimMode
from RePlayAnalysisCore3.DataFiles.ReStoreDataFile import ReStoreDataFile
from RePlayAnalysisCore3.DataFiles.ReTrieveDataFile import ReTrieveDataFile
from RePlayAnalysisCore3.DataFiles.RePlayDataFileStatic import RePlayDataFileStatic
from RePlayAnalysisCore3.RePlayParticipant import RePlayParticipant
from RePlayAnalysisCore3.RePlayUtilities import RePlayUtilities
from RePlayAnalysisCore3.RePlayVisit import RePlayVisit
from RePlayAnalysisCore3.RePlayStudy import RePlayStudy
from RePlayAnalysisCore3.LoadedReStoreFilesCollection import *
from RePlayAnalysisCore3.ReStoreStimulationCollection import *
from RePlayAnalysisCore3.ReStoreStimulationCollection import ReStoreStimulation, ReStoreStimulationCollection


class DatabaseOperations:

    @staticmethod
    def UpdateDatabase(
        json_config_filename, 
        json_participant_reference_filename, 
        json_fixes_filename,
        log_file_name, 
        load_files, 
        reload_flagged_files,
        use_shallow_file_precheck, 
        load_restore_files, 
        load_all_restore_files,
        update_metadata, 
        max_allowed_duration_seconds
    ):

        #Keep track of how long this takes to execute
        script_start_time = time.perf_counter()

        #Initialize colorama
        colorama.init()

        #Let's get the project participant json file
        participant_reference_json = None
        if (os.path.exists(json_participant_reference_filename)):
            print("SUCCESS: JSON participants file found")
            with open(json_participant_reference_filename) as json_file:
                json_data = json.load(json_file)
                participant_reference_json = json_data
        else:
            print("UNABLE TO FIND JSON PARTICIPANTS FILE!")

        #Let's get the json "fixes" file
        fixes_json = None
        if (os.path.exists(json_fixes_filename)):
            print("SUCCESS; JSON fixes file found")
            with open(json_fixes_filename) as json_file:
                fixes_json = json.load(json_file)
        else:
            print("UNABLE TO FIND JSON FIXES FILE!")   

        #Create some empty variables that will be used to hold the locations of the replay data, the restore data,
        #and the database
        replay_data_location = []
        restore_data_location = []
        only_folders_with_matching_uids = False

        #Open the configuration file and get the necessary paths
        if (os.path.exists(json_config_filename)):
            print("SUCCESS: JSON config file found.")
            with open(json_config_filename) as json_file:
                json_data = json.load(json_file)
                if ("database_location" in json_data):
                    db_path = json_data["database_location"]

                if ("replay_data_location" in json_data):
                    replay_data_location = json_data["replay_data_location"]

                if ("restore_data_location" in json_data):
                    restore_data_location = json_data["restore_data_location"]

                if ("only_folders_with_matching_uids" in json_data):
                    only_folders_with_matching_uids = json_data["only_folders_with_matching_uids"]
        else:
            print("UNABLE TO FIND JSON CONFIG FILE!");

        #Open a connection to the database
        current_db_name = json_data["database_name"]
        print(f"Database Name: {current_db_name}")
        db_connection = DatabaseOperations.__open_database(json_data["database_name"])

        #Now get a reference to the study object
        replay_study = RePlayStudy.GetStudy()

        #Set the "last update" timestamp on the database to be the current date/time
        replay_study.last_update = datetime.utcnow()
        replay_study.all_update_datetimes.append(replay_study.last_update)
        replay_study.save()

        #Remove bad stuff
        DatabaseOperations.__remove_bad_db_stuff(fixes_json)

        #Load all the files into the database
        if (load_files):
            DatabaseOperations.__load_files_into_database(participant_reference_json, replay_data_location, fixes_json, log_file_name, only_folders_with_matching_uids, use_shallow_file_precheck, script_start_time, max_allowed_duration_seconds)

            #Associate activities with visits
            DatabaseOperations.__associate_activities_with_visits()

        if (reload_flagged_files):
            #Reload flagged sessions
            DatabaseOperations.__reload_flagged_sessions(participant_reference_json, replay_data_location, fixes_json)

        #Update the visits dataframe
        DatabaseOperations.__update_visits_dataframe()

        #Make sure that each participant has the correct IPGID
        all_participants = RePlayParticipant.objects()
        for current_participant in all_participants:
            if (current_participant.uid in participant_reference_json):
                if ("ipgid" in participant_reference_json[current_participant.uid]):
                    if ("ipgid" not in current_participant.tags) or (current_participant.tags["ipgid"] != participant_reference_json[current_participant.uid]["ipgid"]):
                        current_participant.tags["ipgid"] = participant_reference_json[current_participant.uid]["ipgid"]
                        current_participant.save()

        #Load ReStore stimulation data logs
        if (load_restore_files):
            DatabaseOperations.__load_restore_datalogs(participant_reference_json, restore_data_location, load_all_restore_files, use_shallow_file_precheck, script_start_time, max_allowed_duration_seconds)

        script_end_time = time.perf_counter()
        print(f"SCRIPT RUNNING DURATION: {script_end_time - script_start_time} seconds")
        print(f"CURRENT DATETIME: {datetime.now().isoformat()}")
        print(f"Database Name: {current_db_name}")

        #Update the metadata
        if (update_metadata):
            DatabaseOperations.__update_metadata(script_start_time, max_allowed_duration_seconds)
            print(f"Database Name: {current_db_name}")

        #Close the connection to the database
        db_connection.close()

    @staticmethod
    def OpenDatabase (db_name):
        return DatabaseOperations.__open_database(db_name)

    @staticmethod
    def __open_database (db_name):
        #Connect to the MongoDB database
        db_connection = connect(db_name)

        #Now return the object
        return (db_connection)

    @staticmethod
    def __is_participant_match (participant_reference_json, current_participant_name):
        if (current_participant_name in participant_reference_json):
            #If any of the participant id keys matches the string that was passed in by the user,
            #then return "true".
            return True
        else:
            #Otherwise, let's iterate through each participant and check to see if the string
            #passed in by the user matches any "aliases" defined in the participants json.
            all_pids = participant_reference_json.keys()
            for pid in all_pids:
                if ("aliases" in participant_reference_json[pid]):
                    cur_pid_aliases = participant_reference_json[pid]["aliases"]
                    matching_alias = Enumerable(cur_pid_aliases).where(lambda x: x == current_participant_name).first_or_default()
                    if (matching_alias is not None):
                        #If a match was found, then return "true".
                        return True
        
        #If no match was found, then we return "false".
        return False

    @staticmethod 
    def __get_correct_participant_id (participant_reference_json, participant_id):
        #See if the participant id is an incorrect alias for a correct participant id
        if (participant_id not in participant_reference_json):
            all_pids = participant_reference_json.keys()
            for cur_correct_pid in all_pids:
                if "aliases" in participant_reference_json[cur_correct_pid]:
                    cur_aliases = participant_reference_json[cur_correct_pid]["aliases"]
                    matching_alias = Enumerable(cur_aliases).where(lambda x: x == participant_id).first_or_default()
                    if (matching_alias is not None):

                        #If a match was found, then store the correct participant ID
                        participant_id = cur_correct_pid

                        #Now break out of this loop. No need to be here anymore.
                        break             

        return participant_id

    @staticmethod 
    def __remove_bad_db_stuff (fixes_json):
        all_participants = RePlayParticipant.objects()

        fixes = fixes_json["fixes"]
        for current_fix in fixes:
            bad_uid = current_fix["uid_in_file"]
            visit_date = datetime.fromisoformat(current_fix["start_datetime"]).date()
            files = current_fix["files"]

            current_participant = next((x for x in all_participants if x.uid == bad_uid), None)
            if (current_participant is not None):
                current_visit = next((x for x in current_participant.children if (x.start_time.date() == visit_date)), None)
                if (current_visit is not None):
                    act_to_remove = []
                    filenames_found = []

                    for i in range(0, len(current_visit.children)):
                        current_activity = current_visit.children[i]
                        if (isinstance(current_activity, RePlayActivity)):
                            controller_filename = ""
                            gamedata_filename = ""
                            if (current_activity.controller_data is not None):
                                controller_filename = current_activity.controller_data.filename
                            if (current_activity.game_data is not None):
                                gamedata_filename = current_activity.game_data.filename
                            
                            if (controller_filename in files) or (gamedata_filename in files):
                                #Save the filenames
                                if (controller_filename in files):
                                    filenames_found.append(controller_filename)
                                if (gamedata_filename in files):
                                    filenames_found.append(gamedata_filename)

                                #Mark the activity to remove it from the list in the future
                                if not (current_activity in act_to_remove):
                                    act_to_remove.append(current_activity)
                        elif (isinstance(current_activity, RePlayActivity_ManualStimMode)):
                            if (current_activity.datafile is not None):
                                filename = current_activity.datafile.filename
                                if (filename in files):
                                    filenames_found.append(filename)
                                    if not (current_activity in act_to_remove):
                                        act_to_remove.append(current_activity)
                        elif (isinstance(current_activity, ReTrieveActivity)):
                            if (current_activity.datafile is not None):
                                filename = current_activity.datafile.filename
                                if (filename in files):
                                    filenames_found.append(filename)
                                    if not (current_activity in act_to_remove):
                                        act_to_remove.append(current_activity)                                    

                    if (len(act_to_remove) > 0) or (len(filenames_found) > 0):
                        #Remove all marked activities
                        for a in act_to_remove:
                            current_activity.parent = None                            
                            current_visit.children.remove(a)
                            current_activity.delete()
                        current_visit.save()

                        #If this visit is now empty, then remove it
                        if (len(current_visit.children) == 0):
                            current_visit.parent = None
                            current_participant.children.remove(current_visit)
                            current_visit.delete()
                            current_participant.save()

                        #Remove found filenames from the list of loaded filenames
                        for f in filenames_found:
                            matching_files_list = LoadedFileRecord.objects(file_name = f)
                            for matching_file in matching_files_list:
                                matching_file.delete()

    @staticmethod
    def __check_fixes_json_for_uid_adjustment(fixes_json, filename):
        fixes_list = fixes_json["fixes"]
        for i in range(0, len(fixes_list)):
            current_fix = fixes_list[i]
            if ("files" in current_fix) and ("uid_actual" in current_fix):
                current_fix_files_list = current_fix["files"]
                if (filename in current_fix_files_list):
                    return current_fix["uid_actual"]
        return ""

    @staticmethod
    def __create_list_of_files_to_load (replay_data_paths, participant_reference_json, only_folders_with_matching_uids):
        #Walk the directory tree and find all relevant files
        print ("Walking the directory tree to find relevant files...")
        f = []
        if (only_folders_with_matching_uids):
            for replay_path_x in replay_data_paths:
                #List all subfolders of this path
                subfolders = []
                if (os.path.exists(replay_path_x)):
                    subfolders = os.listdir(replay_path_x)

                #Iterate over each subfolder
                for current_subfolder_name in subfolders:
                    #Concatenate the subfolder to the base path
                    current_full_path = os.path.join(replay_path_x, current_subfolder_name)

                    #Verify if this is a folder (rather than a file)
                    if (os.path.isdir(current_full_path)):
                        #Now let's verify that this folder belongs to a participant that we care about
                        match_found = DatabaseOperations.__is_participant_match(participant_reference_json, current_subfolder_name)

                        if (match_found):
                            #If a match was found, then let's add all sub-folders to the list of files that we want to load
                            for (dirpath, _, filenames) in walk(current_full_path):
                                for fn in filenames:
                                    f.extend([[dirpath, fn]])
        else:
            #Recursively add every file in the folders/sub-folders to the list
            for replay_path_x in replay_data_paths:
                for (dirpath, _, filenames) in walk(replay_path_x):
                    for fn in filenames:
                        f.extend([[dirpath, fn]])            

        
        #Return the list of files to load
        return f

    @staticmethod
    def __handle_loading_retrieve_datafile (participant_reference_json, fixes_json, this_full_file_path, this_file):
        success = False
        try:
            this_file_data = ReTrieveDataFile()
            this_file_data.ReadFile(this_full_file_path)

            current_activity = ReTrieveActivity()
            current_activity.PopulateReTrieveActivity(this_file_data)

            success = True
        except Exception as e:
            return (0, e)
        
        if success:
            #Grab the participant id from the file
            participant_id = current_activity.uid

            #Get the corrected participant ID if there is a fix associated with this file
            possible_uid = DatabaseOperations.__check_fixes_json_for_uid_adjustment(fixes_json, this_file[1])
            if (possible_uid != "") and (possible_uid != participant_id):
                participant_id = possible_uid            

            #See if the participant id is an incorrect alias for a correct participant id
            participant_id = DatabaseOperations.__get_correct_participant_id(participant_reference_json, participant_id)

            #Make sure to correct the participant ID in the file data structure
            if (participant_id != current_activity.uid):
                current_activity.uid = participant_id

            #Add this participant to our data structure (or get the existing participant already
            # in the data structure).
            current_participant = RePlayParticipant.objects(uid = participant_id).first()
            if (current_participant is None):
                current_participant = RePlayParticipant()
                current_participant.uid = participant_id
                current_participant.save()

            #Get the date of this session
            session_date = current_activity.start_time

            #Add a "visit" for this participant that represents this date, or get the existing visit
            #in the data structure that already represents this date.
            current_visit = next((x for x in current_participant.children if x.start_time.date() == session_date.date()), None)
            if (current_visit is None):
                current_visit = RePlayVisit()
                current_visit.start_time = session_date.replace(hour=0, minute=0, second=0, microsecond=0)
                current_visit.end_time = session_date.replace(hour=23, minute=59, second=59, microsecond=0)
                current_visit.parent = current_participant
                current_visit.save()

                current_participant.children.append(current_visit)
                current_participant.save()

            #Check to see if this file has already been loaded into the database
            already_loaded = LoadedFilesCollection.IsFileAlreadyLoaded(this_file[1], this_file_data.md5_checksum)

            #If it has not already been loaded into the database, then let's place it into the db
            if not already_loaded:
                try:
                    #Associate the parent visit of this activity
                    current_activity.parent = current_visit

                    #Save the data file and activity
                    this_file_data.save()
                    current_activity.save()

                    #Add this file to the list of loaded files
                    LoadedFilesCollection.AppendFileToCollection(participant_id, this_file[1], this_file_data.md5_checksum)

                    #Update the current visit
                    current_visit.children.append(current_activity)
                    current_visit.save()
                    
                    return (2, None)
                except Exception as e:
                    return (0, e)

            else:
                return (1, None)

        return (0, None)

    @staticmethod
    def __handle_loading_replay_datafile (participant_reference_json, fixes_json, this_full_file_path, this_file, force_reload = False):
        success = False
        try:
            this_file_data = RePlayDataFile()
            this_file_data.InitiateFileRead(this_full_file_path)
            success = True
        except Exception as ex:
            return (0, None)
        
        if success:
            #Grab the participant id from the file
            participant_id = this_file_data.subject_id

            #Get the corrected participant ID if there is a fix associated with this file
            possible_uid = DatabaseOperations.__check_fixes_json_for_uid_adjustment(fixes_json, this_file[1])
            if (possible_uid != "") and (possible_uid != participant_id):
                participant_id = possible_uid              

            #See if the participant id is an incorrect alias for a correct participant id
            participant_id = DatabaseOperations.__get_correct_participant_id(participant_reference_json, participant_id)

            #Make sure to correct the participant ID in the file data structure
            if (participant_id != this_file_data.subject_id):
                this_file_data.subject_id = participant_id

            #Add this participant to our data structure (or get the existing participant already
            # in the data structure).
            current_participant = RePlayParticipant.objects(uid = participant_id).first()
            if (current_participant is None):
                current_participant = RePlayParticipant()
                current_participant.uid = participant_id
                current_participant.save()

            #Get the date of this session
            session_date = this_file_data.session_start

            #Add a "visit" for this participant that represents this date, or get the existing visit
            #in the data structure that already represents this date.
            current_visit = next((x for x in current_participant.children if x.start_time.date() == session_date.date()), None)
            if (current_visit is None):
                current_visit = RePlayVisit()
                current_visit.start_time = session_date.replace(hour=0, minute=0, second=0, microsecond=0)
                current_visit.end_time = session_date.replace(hour=23, minute=59, second=59, microsecond=0)
                current_visit.parent = current_participant
                current_visit.save()

                current_participant.children.append(current_visit)
                current_participant.save(cascade=True)

            #Check to see if this file has already been loaded into the database
            already_loaded = LoadedFilesCollection.IsFileAlreadyLoaded(this_file[1], this_file_data.md5_checksum)

            if (not already_loaded):
                #If the file has not already been loaded, try to load the file's data into memory
                try:
                    #Read the whole file
                    this_file_data.ReadData(True)

                    #Save this data file to the database
                    this_file_data.save()

                    #Add this file to the list of loaded files
                    LoadedFilesCollection.AppendFileToCollection(participant_id, this_file[1], this_file_data.md5_checksum)                    

                    #Update the list of activities
                    DatabaseOperations.__associate_datafile_with_activity(this_file_data)
                    
                    return (2, None)
                except Exception as e:
                    return (0, e)

            else:

                #If the user wants to force a reload of this data file
                if (force_reload):
                    #Read the whole file
                    this_file_data.ReadData(True)

                    #Save this file to the database
                    this_file_data.save()    

                    #Add this file to the list of loaded files
                    LoadedFilesCollection.AppendFileToCollection(participant_id, this_file[1], this_file_data.md5_checksum)                    

                    #The final step of associating this datafile with an activity will be saved as a 
                    #task for the caller of this function.
                    return (2, this_file_data)

                else:
                    return (1, None)

        return (0, None)

    @staticmethod
    def __handle_loading_replay_manual_stim_datafile(participant_reference_json, fixes_json, this_full_file_path, this_file, potential_uid):
        success = False
        try:
            this_file_data = RePlayDataFile_ManualStimMode()
            this_file_data.InitiateFileRead(this_full_file_path, potential_uid)
            this_file_data.parse_file()

            current_activity = RePlayActivity_ManualStimMode()
            current_activity.populate_activity(this_file_data)

            success = True
        except Exception as e:
            return (0, e)
        
        if success:
            #Grab the participant id from the file
            participant_id = this_file_data.subject_id

            #Get the corrected participant ID if there is a fix associated with this file
            possible_uid = DatabaseOperations.__check_fixes_json_for_uid_adjustment(fixes_json, this_file[1])
            if (possible_uid != "") and (possible_uid != participant_id):
                participant_id = possible_uid            

            #See if the participant id is an incorrect alias for a correct participant id
            participant_id = DatabaseOperations.__get_correct_participant_id(participant_reference_json, participant_id)

            #Make sure to correct the participant ID in the file data structure
            if (participant_id != this_file_data.subject_id):
                this_file_data.subject_id = participant_id

            #Add this participant to our data structure (or get the existing participant already
            # in the data structure).
            current_participant = RePlayParticipant.objects(uid = participant_id).first()
            if (current_participant is None):
                current_participant = RePlayParticipant()
                current_participant.uid = participant_id
                current_participant.save()

            #Get the date of this session
            session_date = this_file_data.start_time

            if session_date is not None:
                #Add a "visit" for this participant that represents this date, or get the existing visit
                #in the data structure that already represents this date.
                current_visit = next((x for x in current_participant.children if x.start_time.date() == session_date.date()), None)
                if (current_visit is None):
                    current_visit = RePlayVisit()
                    current_visit.start_time = session_date.replace(hour=0, minute=0, second=0, microsecond=0)
                    current_visit.end_time = session_date.replace(hour=23, minute=59, second=59, microsecond=0)
                    current_visit.parent = current_participant
                    current_visit.save()

                    current_participant.children.append(current_visit)
                    current_participant.save()

                #Check to see if this file has already been loaded into the database
                already_loaded = LoadedFilesCollection.IsFileAlreadyLoaded(this_file[1], this_file_data.md5_checksum)

                #If it has not already been loaded into the database, then let's place it into the db
                if not already_loaded:
                    try:
                        #Associate the parent visit of this activity
                        current_activity.parent = current_visit

                        #Save the data file and activity
                        this_file_data.save()
                        current_activity.save()

                        #Add this file to the list of loaded files
                        LoadedFilesCollection.AppendFileToCollection(participant_id, this_file[1], this_file_data.md5_checksum)

                        #Update the current visit
                        current_visit.children.append(current_activity)
                        current_visit.save()
                        
                        return (2, None)
                    except Exception as e:
                        return (0, e)

            else:
                return (1, None)

        return (0, None)

    @staticmethod
    def __load_files_into_database (participant_reference_json, replay_data_paths, fixes_json, log_file_name, only_folders_with_matching_uids, use_shallow_file_precheck, script_start_time, max_allowed_duration_seconds):

        #Open the log file to output messages that the user may want to see afterwards
        log_file_handle = open(log_file_name, 'w')

        #Create the list of files to load
        f = DatabaseOperations.__create_list_of_files_to_load(replay_data_paths, participant_reference_json, only_folders_with_matching_uids)

        print(f"Found {len(f)} files. Filtering out files that have previously been loaded...")

        #Filter out files that have already been loaded
        filtered_f = []
        all_loaded_files_successful = LoadedFileRecord.objects()
        all_loaded_files_failed = FailedFileRecord.objects()
        all_loaded_files_successful = [x.file_name for x in all_loaded_files_successful]
        all_loaded_files_failed = [x.file_name for x in all_loaded_files_failed]
        for f_idx in range(0, len(f)):
            this_file = f[f_idx]

            #Make sure the file we are checking is the correct file type...
            is_potential_replay_file = this_file[1].lower().endswith(".txt")
            is_potential_retrieve_file = this_file[1].lower().endswith(".json")
            is_potential_manual_stim_file = (this_file[1].startswith("TherapistMode")) and (this_file[1].endswith(".txt"))

            if (is_potential_replay_file or is_potential_retrieve_file or is_potential_manual_stim_file):
                if (use_shallow_file_precheck):
                    
                    #Check to see if this filename matches the filenames of any files already loaded
                    if (this_file[1] in all_loaded_files_successful):
                        continue

                    if (this_file[1] in all_loaded_files_failed):
                        continue           

                    #If we reach this point in the loop, it means the file has not yet been loaded
                    #So let's add this file to our filtered list of files to load
                    filtered_f.append(this_file)
        
        #Now set f to be the filtered list
        f = filtered_f

        #If files were found, let's check to see if they exist in the database already
        print(f"Loading {len(f)} files into the database...")
        loaded_previously = 0
        loaded_successfully = 0
        loaded_unrecognized = 0
        loaded_failed = 0
        loaded_db_failed = 0
        if len(f) > 0:
            #Iterate through each file that was found...
            for this_file in f:
                #Make sure that we still have time to handle this file, if we are on a time limit
                if (max_allowed_duration_seconds > 0):
                    current_script_time = time.perf_counter()
                    elapsed_time_since_start = current_script_time - script_start_time
                    if (elapsed_time_since_start >= max_allowed_duration_seconds):
                        #If too much time has elapsed, then break out of the loop.
                        #We will simply handle loading the rest of the files another day.
                        break

                #Make sure the file we are checking is the correct file type...
                is_potential_replay_file = this_file[1].lower().endswith(".txt")
                is_potential_retrieve_file = this_file[1].lower().endswith(".json")
                is_potential_manual_stim_file = (this_file[1].startswith("TherapistMode")) and (this_file[1].endswith(".txt"))

                if (is_potential_replay_file or is_potential_retrieve_file or is_potential_manual_stim_file):
                    #Do an initial read of the file's metadata
                    this_full_file_path = this_file[0] + "/" + this_file[1]

                    #If the user wants us to do a shallow pre-check on the filename before loading in the file,
                    #we will do that here. Normally we do a "deep" check on the file which includes comparing
                    #the md5 checksum as well, but that requires actually loading the file into memory. It's faster
                    #to just compare filenames.
                    #if (use_shallow_file_precheck):
                        #Check to see if this filename matches the filenames of any files already loaded
                    #    is_file_already_loaded = LoadedFilesCollection.IsFileAlreadyLoaded_Shallow(this_file[1])

                        #If there is a match...
                    #    if (is_file_already_loaded):
                            #Then skip everything else in this iteration of the loop. Go on to the next file (the
                            # next iteration of the loop).
                    #        continue

                    if (is_potential_retrieve_file):

                        #Attempt to load the ReTrieve datafile into the database
                        (retrieve_result, retrieve_exception) = DatabaseOperations.__handle_loading_retrieve_datafile(participant_reference_json, fixes_json, this_full_file_path, this_file)

                        #Now report the result to the user
                        if (retrieve_result is None or retrieve_result == 0):

                            loaded_failed = loaded_failed + 1
                            FailedFilesCollection.AppendFileToCollection(this_file[1])

                            if (retrieve_exception):
                                print("\t" + retrieve_exception)
                            print("FAILED TO LOAD RETRIEVE FILE " + this_file[1])
                            log_file_handle.write(this_file[1] + "\n")
                            
                        elif (retrieve_result == 1):
                            print(this_file[1] + " was previously loaded into the database.")    
                            loaded_previously = loaded_previously + 1                        
                        elif (retrieve_result == 2):
                            print("Successfully loaded file: " + this_file[1] + " (Partial commit complete)")
                            loaded_successfully = loaded_successfully + 1

                    elif (is_potential_replay_file) and (not is_potential_manual_stim_file):

                        (replay_result, replay_exception) = DatabaseOperations.__handle_loading_replay_datafile(participant_reference_json, fixes_json, this_full_file_path, this_file)
                        if (replay_result == 0):

                            loaded_failed = loaded_failed + 1
                            FailedFilesCollection.AppendFileToCollection(this_file[1])

                            if (replay_exception is not None):
                                traceback.print_exc()
                                print(replay_exception.__class__)
                                print("FAILED TO LOAD FILE: " + this_file[1])
                                log_file_handle.write(this_file[1] + "\n")
                            else:
                                print ("THIS FILE DOESN'T LOOK LIKE A REPLAY FILE: " + this_file[1])
                            
                        elif (replay_result == 1):
                            print(this_file[1] + " was previously loaded into the database.")    
                            loaded_previously = loaded_previously + 1                                                            
                            loaded_successfully = loaded_successfully + 1                            
                        elif (replay_result == 2):
                            print("Successfully loaded file: " + this_file[1] + " (Partial commit complete)")
                            loaded_successfully = loaded_successfully + 1

                    elif (is_potential_manual_stim_file):
                        
                        #Parase the paths to get the potential UID
                        (h1, _) = ntpath.split(this_file[0])
                        (h2, _) = ntpath.split(h1)
                        (_, t3) = ntpath.split(h2)
                        potential_uid = t3

                        (replay_result, replay_exception) = DatabaseOperations.__handle_loading_replay_manual_stim_datafile(participant_reference_json, fixes_json, this_full_file_path, this_file, potential_uid)
                        if (replay_result == 0):

                            loaded_failed = loaded_failed + 1
                            FailedFilesCollection.AppendFileToCollection(this_file[1])

                            if (replay_exception is not None):
                                traceback.print_exc()
                                print(replay_exception.__class__)
                                print("FAILED TO LOAD FILE: " + this_file[1])
                                log_file_handle.write(this_file[1] + "\n")
                            else:
                                print ("THIS FILE DOESN'T LOOK LIKE A MANUAL STIM FILE: " + this_file[1])

                        elif (replay_result == 1):
                            print(this_file[1] + " was previously loaded into the database.")    
                            loaded_previously = loaded_previously + 1                       
                        elif (replay_result == 2):
                            print("Successfully loaded file: " + this_file[1] + " (Partial commit complete)")
                            loaded_successfully = loaded_successfully + 1

        #Commit the transaction to the database
        print ("Committing ALL phase 2 changes...", end = "")
        print (f"Loaded {loaded_successfully} files successfully.")
        print (f"Failed to load {loaded_failed} files.")
        print (f"Total files that were meant to be loaded: {len(f)}")
        print ("Complete")

        log_file_handle.close()  

    @staticmethod
    def __associate_activities_with_visits ():
        #Now let's go through and find activities that need parent visits
        all_participants = RePlayParticipant.objects()
        all_existing_uids = [x.uid for x in all_participants]
        activity_list = BaseActivity.objects()
        invalid_parent_count = 0
        for i in range(0, len(activity_list)):
            current_activity = activity_list[i]

            #ReTrieve data files and activities are tightly coupled, we can skip over them on this stage.
            if (isinstance(current_activity, ReTrieveActivity)):
                continue

            try:
                current_activity_parent = current_activity.parent
            except:
                print(f"Found activity with invalid parent! Activity UID = {current_activity.uid}, activity = {current_activity.activity_name}, start time = {current_activity.start_time.isoformat()}")
                invalid_parent_count += 1
                continue

            if (current_activity.parent is None):
                activity_time = current_activity.start_time

                #Iterate over participants and visits
                for p in all_participants:
                    for v in p.children:
                        #If this activity falls within this visit for this participant, then maybe it belongs
                        #to this participant...
                        is_time_in_range = (activity_time.date() == v.start_time.date())
                        if (is_time_in_range):
                            do_i_parent = True

                            if (current_activity.uid == p.uid):
                                #If the participant IDs match, then it definitely belongs
                                do_i_parent = True
                            elif (current_activity.uid in all_existing_uids):
                                #If the participant ID matches a DIFFERENT participant, then it does NOT belong
                                do_i_parent = False
                            else:
                                #Otherwise, assume it belongs
                                do_i_parent = True
                            
                            #Set the parent visit of this activity if the flag is true
                            if (do_i_parent):
                                current_activity.parent = v
                                current_activity.save()

                                v.children.append(current_activity)
                                v.is_dirty = True
                                v.save()

        #Commit the transaction to the database
        print (f"Number of activities with invalid parents: {invalid_parent_count}")
        print ("Committing phase 5 changes...", end = "")
        print ("Complete")        

    @staticmethod
    def __associate_datafile_with_activity(session_data_file_object):
        #Grab the participant ID and the start time of the session
        participant_id = session_data_file_object.subject_id
        activity_name = session_data_file_object.game_id
        session_start_time = session_data_file_object.session_start

        #Generate the table names for this data file
        is_gamedata_file = session_data_file_object.data_type
        
        #Figure out the duration of the session
        session_duration = float("nan")
        session_data = session_data_file_object.AccessData()
        if ((session_data is not None) and (hasattr(session_data, "signal_time")) and (len(session_data.signal_time) > 0)):
            #Grab the last element of the "signal time" array
            #This should be essentially how long the session was
            session_duration = session_data.signal_time[-1]            
        
        #Now let's see if there is already a row in the database that
        #we can just update, or let's see if we need to create a new
        #row in the database.
        time_allowance = 5
        found = False

        #Iterate over all existing activities in the activity list
        activity_list = BaseActivity.objects()
        for i in range(0, len(activity_list)):
            cur_activity = activity_list[i]

            #Check to see if the UID and activity name match
            if ((cur_activity.uid == participant_id) and (cur_activity.activity_name == activity_name)):
                cur_start = cur_activity.start_time
                time_delta = session_start_time - cur_start
                time_delta_total_seconds = abs(time_delta.total_seconds())
                if (time_delta_total_seconds <= time_allowance):
                    found = True

                    #Set the duration of the activity using the session data we have available.
                    #If this is a game data session, it automatically overrides any pre-existing duration data in the activity
                    if ((math.isnan(cur_activity.duration)) or (is_gamedata_file and not math.isnan(session_duration))):
                        cur_activity.duration = session_duration

                    #If this is a game data file, then set the game data object of the current activity
                    if (is_gamedata_file and (cur_activity.game_data is None)):
                        cur_activity.SetGameData(session_data_file_object)
                    elif (cur_activity.controller_data is None):
                        #Otherwise, set the controller data object
                        cur_activity.SetControllerData(session_data_file_object)
                    
                    cur_activity.save()

        #If we did not find any records that matched the criteria for "updating",
        #then we should INSERT a new record into the list
        if not found:
            new_activity = RePlayActivity()
            new_activity.uid = participant_id
            new_activity.activity_name = activity_name
            new_activity.start_time = session_start_time
            new_activity.duration = session_duration

            if (is_gamedata_file):
                new_activity.SetGameData(session_data_file_object)
            else:
                new_activity.SetControllerData(session_data_file_object)
            
            new_activity.save()

    @staticmethod
    def __load_restore_datalogs (participant_reference_json, restore_data_location, LoadAllReStoreFiles, use_shallow_file_precheck, script_start_time, max_allowed_duration_seconds):
        #The purpose of this portion of code is to load ReStore data logs into the database
        #There are some unique challenges associated with ReStore data logs:
        #   1. Unlike RePlay data files, just because a ReStore data file exists, that does not mean the file is COMPLETE.
        #       It is possible that ReStore may continue to add more data to that file in the future. This means that
        #       when we UPDATE the database, we need to look at ReStore data files that we have loaded in previously to 
        #       see if they have changed.
        #   2. While the file names are likely to be unique, there is no guarantee. They are a date/time stamp of when 
        #       the file was created.
        #   3. The best way to uniquely identify any ReStore event is to look at the combination of the event's start time
        #       and the IPG ID.

        #LoadAllReStoreFiles value:
        #0 = only load previously unseen files and previously unseen stims
        #1 = drop ALL previously loaded files and stims, load EVERYTHING fresh
        #2 = drop all file records and load all files in fresh, but don't drop stim records. Only load in previously unseen stims

        #If the user is requesting to re-load ALL ReStore files, the go ahead and drop the collection that currently exists
        if (LoadAllReStoreFiles == 1):
            ReStoreStimulation.drop_collection()
            LoadedReStoreFileRecord.drop_collection()
        elif (LoadAllReStoreFiles == 2):
            LoadedReStoreFileRecord.drop_collection()

        #This dictionary will hold a simple count of every command that was issued
        #This dictionary is not placed into the database. It is only used within this script for debugging purposes.
        command_map = {}

        #This dictionary will hold a simple count of the result of every QUICK_STIM command
        #This dictionary is not placed into the database. It is only used within this script for debugging purposes.
        quick_stim_result_map = {}

        #Create a dictionary to hold each unique stimulation event that we load in from data files
        unique_stimulations = {}

        #Create a dictionary to hold each unique failed stimulation event that we load from the data files
        unique_failed_stimulations = {}

        #Navigate the file structure to find all files that may be candidates to load in
        f = []
        for restore_data_location_x in restore_data_location:
            for (dirpath, _, filenames) in walk(restore_data_location_x):
                for fn in filenames:
                    f.extend([[dirpath, fn]])

        #If we found at least 1 file...
        if (len(f) > 0):

            #Iterate through each file that was found...
            for this_file in f:
                #Make sure that we still have time to handle this file, if we are on a time limit
                if (max_allowed_duration_seconds > 0):
                    current_script_time = time.perf_counter()
                    elapsed_time_since_start = current_script_time - script_start_time
                    if (elapsed_time_since_start >= max_allowed_duration_seconds):
                        #If too much time has elapsed, then break out of the loop.
                        #We will simply handle loading the rest of the files another day.
                        break

                #Compose the full file path
                this_full_file_path = this_file[0] + "/" + this_file[1]

                #Get the file's size
                current_file_size = os.path.getsize(this_full_file_path)

                #Check if the user wants us to do a "shallow" pre-check of the filename before actually
                #opening the file and loading it into memory...
                if (use_shallow_file_precheck and (LoadAllReStoreFiles == 0)):
                    #If the filename already exists in the keys...
                    if (LoadedReStoreFilesCollection.IsFileAlreadyLoaded_FileNameAndSizeCheck(this_file[1], current_file_size)):
                        #Then go to the next file (the next iteration of the loop)...
                        continue

                print(f"{Fore.GREEN}Attempting to load file: {this_file[1]}{Style.RESET_ALL}")

                this_file_stim_count = 0
                this_file_bad_stim_count = 0
                this_file_bad_bad_stim_count = 0
                this_file_good_stim_count = 0
                this_file_bad_good_stim_count = 0
                duplicate_stims = 0

                #For each file that we load in, we will keep track of the "most recent" IPG ID from a good stim.
                #The purpose of this is to help us identify the IPG ID that bad stims belong to.
                #While this isn't a perfect system, it will likely correctly identify the participant for about
                #95% of bad stims.
                most_recent_good_stim_ipgid = None

                #Attempt to load in the ReStore data file
                restore_data_file = None
                try:
                    restore_data_file = ReStoreDataFile()
                    restore_data_file.ReadFile(this_full_file_path)
                except:
                    restore_data_file = None

                if (restore_data_file is not None):
                    #Check to see if this file is contained in the dictionary of loaded restore files
                    checksum_match = False
                    if (LoadedReStoreFilesCollection.IsFileAlreadyLoaded_ComprehensiveCheck(this_file[1], current_file_size, restore_data_file.md5_checksum)):
                        checksum_match = True

                    #If this file does not match a previously loaded file, then let's continue to load it in...
                    if ((not checksum_match) or (LoadAllReStoreFiles > 0)):

                        #Add this restore data file with its checksum to the dictionary (or update the current dictionary entry)
                        LoadedReStoreFilesCollection.AppendFileToCollection(this_file[1], restore_data_file.md5_checksum, current_file_size)

                        #Iterate over each event in the data file
                        for pcm_event in restore_data_file.pcm_events:
                            #Get the command for this event
                            pcm_command = pcm_event["COMMAND"]

                            #For statistical tracking purposes, track how many times we have seen this command
                            if (pcm_command in command_map):
                                command_map[pcm_command] += 1
                            else:
                                command_map[pcm_command] = 1
                            
                            #If this is a quick stim command
                            if (pcm_command == "QUICK_STIM"):
                                this_file_stim_count += 1

                                #For statistical tracking purposes, track the various results from the quick stim commands
                                quick_stim_result = pcm_event["RESULT"]
                                if (quick_stim_result in quick_stim_result_map):
                                    quick_stim_result_map[quick_stim_result] += 1
                                else:
                                    quick_stim_result_map[quick_stim_result] = 1

                                #If this was a "successful" stim
                                if (quick_stim_result == "STIM_SUCCESS"):
                                    #Make sure that the stimulation event has an IPGID, EVENT_START, and START_TIME.
                                    if (("IPGID" in pcm_event) and ("EVENT_START" in pcm_event) and ("START_TIME" in pcm_event)):
                                        #If we reach this point in the code, we know we have found a "good" stim.
                                        this_file_good_stim_count += 1

                                        #Make a Python datetime event from the current pcm event
                                        cur_stim_datetime = RePlayUtilities.convert_restore_event_to_datetime(pcm_event["START_TIME"], pcm_event["EVENT_START"])                                

                                        #Grab the IPG ID from this event
                                        cur_ipgid = pcm_event["IPGID"]

                                        #Now also store the current IPG ID in the "most recent IPG ID" variable, for the purpose of helping
                                        #us to identify the participant of bad stims in another part of the code
                                        most_recent_good_stim_ipgid = cur_ipgid

                                        #Now we need to check if this stimulation was already loaded in previously from another file
                                        if (cur_ipgid in unique_stimulations):
                                            if (cur_stim_datetime in unique_stimulations[cur_ipgid]):
                                                #Do nothing. This stimulation has been dealt with previously.
                                                duplicate_stims += 1
                                            else:
                                                #Add this stimulation to the dictionary
                                                unique_stimulations[cur_ipgid][cur_stim_datetime] = pcm_event
                                        else:
                                            #Create a sub-dictionary for this ipgid
                                            unique_stimulations[cur_ipgid] = {}

                                            #Add this stimulation to the dictionary
                                            unique_stimulations[cur_ipgid][cur_stim_datetime] = pcm_event
                                    else:
                                        #If we reach this point in the code, we have found a "STIM_SUCCESS" event,
                                        #but it does not contain all the appropriate JSON parameters that we need to
                                        #determine WHO received the stimulation and WHEN the stimulation occurred.
                                        this_file_bad_good_stim_count += 1
                                else:
                                    #If we reach this point in the code, we have found a stimulation event that did NOT
                                    #result in success.
                                    
                                    #Check to see if the proper timestamps are present
                                    if (("EVENT_START" in pcm_event) and ("START_TIME" in pcm_event) and (most_recent_good_stim_ipgid is not None)):
                                        #If we reach this point in the code, we've found a failed stim that does contain a timestamp.
                                        this_file_bad_stim_count += 1

                                        #Transform the timestamp to something we can work with
                                        cur_stim_datetime = RePlayUtilities.convert_restore_event_to_datetime(pcm_event["START_TIME"], pcm_event["EVENT_START"])

                                        #Place this failed stimulation event in our dictionary of failed stims
                                        if (most_recent_good_stim_ipgid in unique_failed_stimulations):
                                            if (cur_stim_datetime in unique_failed_stimulations[most_recent_good_stim_ipgid]):
                                                #Do nothing. This stimulation has been dealt with previously.
                                                pass
                                            else:
                                                #Add this stimulation to the dictionary
                                                unique_failed_stimulations[most_recent_good_stim_ipgid][cur_stim_datetime] = pcm_event
                                        else:
                                            #Create a sub-dictionary for this ipgid
                                            unique_failed_stimulations[most_recent_good_stim_ipgid] = {}

                                            #Add this stimulation to the dictionary
                                            unique_failed_stimulations[most_recent_good_stim_ipgid][cur_stim_datetime] = pcm_event

                                    else:
                                        #If we reach this point in the code, we've found a failed stim that doesn't have a timestamp.
                                        this_file_bad_bad_stim_count += 1

                        #Print some messages to the user.
                        print(f"\tThis file contains {this_file_stim_count} stimulations.")
                        print(f"\t{this_file_good_stim_count} stimulations were successful.")
                        print(f"\t{this_file_bad_good_stim_count} stimulations were apparently successful, but don't have the appropriate attributes.")
                        print(f"\t{this_file_bad_stim_count} stimulations failed, had a corresponding timestamp, and could tentatively be associated with an IPG ID.")
                        print(f"\t{this_file_bad_bad_stim_count} stimulations failed, but lacked a corresponding timestamp or could not be given an IPG ID.")
                        print(f"\tFinished loading file. {duplicate_stims} successful stimulations were duplicates from other files.")
                    else:
                        #We reach this point if the md5 checksum of this file matched another file that was previously loaded
                        print("\tSKIPPING this file. The file's checksum matches a previously loaded file.")

        #Now, having reached this point, we have loaded in all of the stimulations.
        #So now we need to associate each stimulation with a participant.
        #Each RePlayParticipant object should have an attribute describing the IPG ID for that participant.
        #With that information, we can save these stimulations for each respective participant.

        all_participants = RePlayParticipant.objects()
        existing_stimulations_in_db = ReStoreStimulation.objects()
        for p in all_participants:
            #Check to see if an ipgid has been defined for this participant.
            #Also check to make sure the CORRECT ipgid is defined for each participant.
            if (p.uid in participant_reference_json):
                #If it does exist, let's grab it...
                cur_participant_reference_json = participant_reference_json[p.uid]
                if ("ipgid" in cur_participant_reference_json) and (cur_participant_reference_json["ipgid"] is not None):
                    #And let's assign it to the tags for this participant
                    cur_participant_correct_ipgid = cur_participant_reference_json["ipgid"]
                    
                    #Now check to see if the ipgid needs to be defined (or corrected) in the database
                    if (("ipgid" not in p.tags) or 
                        (("ipgid" in p.tags) and (p.tags["ipgid"] is None)) or
                        (("ipgid" in p.tags) and (p.tags["ipgid"] != cur_participant_correct_ipgid))):        

                        p.tags["ipgid"] = cur_participant_correct_ipgid

            #Now, if an ipgid has been defined for this participant...
            if ("ipgid" in p.tags):
                current_ipgid = p.tags["ipgid"]

                #Grab all stimulations currently existing in the database for this participant/ipg
                current_ipg_existing_stimulations = [x for x in existing_stimulations_in_db if (x.ipg_id == current_ipgid)]

                #Find the ipgid key in the unique stims dictionary
                if (current_ipgid is not None) and (current_ipgid in unique_stimulations):

                    #Now let's find the current IPG ID in the unique stims dictionary
                    if (current_ipgid in unique_stimulations):

                        #Grab the stims for this participant, while also removing them from the dictionary
                        this_participant_new_stimulations = unique_stimulations.pop(current_ipgid)

                        #Print a message to the user
                        print(f"{Fore.CYAN}Associating ReStore logged stimulations (n = {len(this_participant_new_stimulations)}) for participant {p.uid} with IPG ID {current_ipgid}{Style.RESET_ALL}")
                    
                        #Store the new stimulations in the restore stimulation collection of the database
                        for key, value in this_participant_new_stimulations.items():
                            matching_stims = [x for x in current_ipg_existing_stimulations if (x.stimulation_datetime == key)]
                            if (len(matching_stims) == 0):
                                ReStoreStimulationCollection.AppendStimToCollection_KnownUID(p.uid, current_ipgid, True, key, value)

                        #Grab the failed stims for this participant, while also removing them from the dictionary
                        this_participant_new_failed_stimulations = unique_failed_stimulations.pop(current_ipgid)

                        #Print a message to the user
                        print(f"{Fore.CYAN}Associating ReStore logged FAILED stimulations (n = {len(this_participant_new_failed_stimulations)}) for participant {p.uid} with IPG ID {current_ipgid}{Style.RESET_ALL}")

                        #Store the new stimulations in the restore stimulation collection of the database
                        for key, value in this_participant_new_failed_stimulations.items():
                            matching_stims = [x for x in current_ipg_existing_stimulations if (x.stimulation_datetime == key)]
                            if (len(matching_stims) == 0):
                                ReStoreStimulationCollection.AppendStimToCollection_KnownUID(p.uid, current_ipgid, False, key, value)

                    #Now let's see if there are any "orphaned" stims that should be associated with this participant
                    matching_orphaned_stims = [x for x in current_ipg_existing_stimulations if (
                            (x.uid is None) or 
                            ((x.uid is not None) and (x.uid == ""))
                        )
                    ]
                    
                    #Store the orphaned stimulations with the matching participant
                    for matching_orphaned_stim in matching_orphaned_stims:
                        matching_orphaned_stim.uid = p.uid
                        matching_orphaned_stim.save()

        #Now, if there is anything remaining in the "unique_stimulations" dictionary, those are considered "orphaned stims".
        #We do not have a participant with whom we can associate these stimulations at this time, but it's possible that
        #sometime in the future we will be able to associate these stimulations with a participant.
        #For now, we will store them as "orphaned stims" without a UID
        for key, value in unique_stimulations.items():
            #key = the participant's ipgid
            #value = dictionary of stims with key-value pairs of (timestamp, json).

            #Print a message to the user
            print(f"{Fore.CYAN}Placing orphaned stims in database (n = {len(value)}) for IPG ID {key}{Style.RESET_ALL}")

            #Grab all stimulations currently existing in the database for this participant/ipg
            current_ipg_existing_stimulations = [x for x in existing_stimulations_in_db if (x.ipg_id == key)]

            #Now iterate through each stim and place it in the BTree if it is not yet already there.
            #key2 = timestamp for the stim
            #value2 = full json for the stim
            orphaned_counter = 0
            for key2, value2 in value.items():

                matching_stims = [x for x in current_ipg_existing_stimulations if (x.stimulation_datetime == key2)]
                if (len(matching_stims) == 0):
                    ReStoreStimulationCollection.AppendStimToCollection_UnknownUID(key, True, key2, value2)
                    orphaned_counter += 1

            #Print a message to the user
            print(f"{Fore.CYAN}n = {orphaned_counter} orphaned stims successfully placed for IPG ID {key}{Style.RESET_ALL}. Other stims were duplicates.")

        #Now, let's see if there is anything remaining in the "unique failed stims" dictionary. If so, they are considered
        #"orphaned failed stims". We will save them in the database and associate them with a participant on a later run
        #of this script.
        for key, value in unique_failed_stimulations.items():
            #key = the participant's ipgid
            #value = dictionary of stims with key-value pairs of (timestamp, json).

            #Grab all stimulations currently existing in the database for this participant/ipg
            current_ipg_existing_stimulations = [x for x in existing_stimulations_in_db if (x.ipg_id == key)]

            #Print a message to the user
            print(f"{Fore.CYAN}Placing orphaned FAILED stims in database (n = {len(value)}) for IPG ID {key}{Style.RESET_ALL}")

            #Now iterate through each stim and place it in the BTree if it is not yet already there.
            #key2 = timestamp for the stim
            #value2 = full json for the stim
            orphaned_counter = 0
            for key2, value2 in value.items():

                matching_stims = [x for x in current_ipg_existing_stimulations if (x.stimulation_datetime == key2)]
                if (len(matching_stims) == 0):
                    ReStoreStimulationCollection.AppendStimToCollection_UnknownUID(key, False, key2, value2)
                    orphaned_counter += 1

            #Print a message to the user
            print(f"{Fore.CYAN}n = {orphaned_counter} orphaned FAILED stims successfully placed for IPG ID {key}{Style.RESET_ALL}. Other stims were duplicates.")

        #Now, let's update the activity and visit dataframes in the RePlay study object with the most up-to-date stimulation counts
        DatabaseOperations.__associate_restore_stims_with_activities_dataframe()
        DatabaseOperations.__associate_restore_stims_with_visits_dataframe()

        #Commit the transaction to the database
        print ("Committing phase 6 changes...", end = "")
        print ("Complete")

    @staticmethod
    def __associate_restore_stims_with_activities_dataframe():
        print("ASSOCIATING RESTORE STIMULATIONS WITH ACTIVITIES")
        print("Fetching study...")
        baylor_study = RePlayStudy.GetStudy()

        print("Fetching activity metrics dataframe...")
        df = baylor_study.GetAggregatedMetricsDataFrame()

        print("Fetching stimulation objects...")
        stims = list(ReStoreStimulation.objects(is_successful = True))

        uid_col_idx = df.columns.get_loc("Participant ID")
        visit_date_col_idx = df.columns.get_loc("Visit Date")
        st_col_idx = df.columns.get_loc("Start Time")
        dur_col_idx = df.columns.get_loc("Duration")
        restore_stims_col_idx = df.columns.get_loc("VNS trigger events [logged by ReStore]")

        current_participant_id = ""
        current_visit_date = ""

        current_participant_stims = []
        current_visit_stims = []

        df_length = len(df)

        for row_idx in range(0, df_length):
            #Print a message to the user
            print(f"Processing row {row_idx+1}/{df_length} of activities dataframe")

            #Get the data elements from this row that are important to us
            uid = df.iloc[row_idx, uid_col_idx]
            visit_date = df.iloc[row_idx, visit_date_col_idx]
            st = df.iloc[row_idx, st_col_idx]
            dur = df.iloc[0, dur_col_idx]

            #Create a date object with the visit date information
            vd = datetime.fromisoformat(visit_date).date()

            #Calculate the start/end time of the activity
            dt = datetime.fromisoformat(st)
            dt2 = dt + timedelta(seconds=dur)

            reset_visit = False
            if (uid != current_participant_id):
                current_participant_id = uid
                current_participant_stims = [x for x in stims if x.uid == uid]
                reset_visit = True
            
            if (visit_date != current_visit_date) or reset_visit:
                current_visit_date = visit_date
                current_visit_stims = [x for x in current_participant_stims if x.stimulation_datetime.date() == vd]

            if (len(current_visit_stims) > 0):
                current_activity_stims = [x for x in current_visit_stims if ((x.stimulation_datetime >= dt) and (x.stimulation_datetime <= dt2))]
                stim_count = len(current_activity_stims)
                if (df.iloc[row_idx, restore_stims_col_idx] != stim_count):
                    df.iloc[row_idx, restore_stims_col_idx] = stim_count
                    
        baylor_study.SaveAggregatedMetricsDataFrame()

    @staticmethod
    def __associate_restore_stims_with_visits_dataframe():
        print("ASSOCIATING RESTORE STIMULATIONS WITH VISITS")
        print("Fetching study...")
        baylor_study = RePlayStudy.GetStudy()

        print("Fetching visit metrics dataframe...")
        df = baylor_study.GetVisitMetricsDataFrame()

        print("Fetching stimulation objects...")
        stims = list(ReStoreStimulation.objects())

        uid_col_idx = df.columns.get_loc("Participant ID")
        visit_date_col_idx = df.columns.get_loc("Visit Date")
        restore_stims_col_idx = df.columns.get_loc("Total successful VNS trigger events [logged by ReStore]")
        failed_stims_col_idx = df.columns.get_loc("Total failed VNS trigger events [logged by ReStore]")

        current_participant_id = ""

        current_participant_stims = []
        current_visit_successful_stims = []
        current_visit_failed_stims = []

        df_length = len(df)

        for row_idx in range(0, df_length):
            #Print a message to the user
            print(f"Processing row {row_idx+1}/{df_length}")

            #Get the data elements from this row that are important to us
            uid = df.iloc[row_idx, uid_col_idx]
            visit_date = df.iloc[row_idx, visit_date_col_idx]

            #Create a date object with the visit date information
            vd = datetime.fromisoformat(visit_date).date()

            if (uid != current_participant_id):
                current_participant_id = uid
                current_participant_stims = [x for x in stims if x.uid == uid]
            
            current_visit_stims = [x for x in current_participant_stims if x.stimulation_datetime.date() == vd]

            current_visit_successful_stims = [x for x in current_visit_stims if x.is_successful]
            current_visit_failed_stims = [x for x in current_visit_stims if not x.is_successful]
            success_stim_count = len(current_visit_successful_stims)
            failed_stim_count = len(current_visit_failed_stims)

            if (df.iloc[row_idx, restore_stims_col_idx] != success_stim_count):
                df.iloc[row_idx, restore_stims_col_idx] = success_stim_count

            if (df.iloc[row_idx, failed_stims_col_idx] != failed_stim_count):
                df.iloc[row_idx, failed_stims_col_idx] = failed_stim_count

        baylor_study.SaveVisitMetricsDataFrame()

    @staticmethod
    def __update_visits_dataframe():
        print("UPDATING VISITS DATAFRAME")
        print("Fetching study...")
        baylor_study = RePlayStudy.GetStudy()

        all_participants = RePlayParticipant.objects()
        for current_participant in all_participants:
            visits = current_participant.children
            for visit_idx in range(0, len(visits)):
                current_visit = visits[visit_idx]
                print(f"Processing participant {current_participant.uid}, visit {visit_idx+1}/{len(visits)}")
                baylor_study.UpdateVisitInVisitMetrics(current_visit, False)

        baylor_study.SaveVisitMetricsDataFrame()        

    @staticmethod
    def __update_metadata(script_start_time, max_allowed_duration_seconds):
        #Print a statement to the user
        print("BEGINNING METADATA CALCULATION")

        #Initialize colorama
        colorama.init()

        #Get the study object
        root = RePlayStudy.GetStudy()

        #Iterate over each participant
        all_participants = RePlayParticipant.objects()
        total_participants = len(all_participants)
        p_idx = 1
        for p in all_participants:

            #Make sure that we still have time to handle this participant, if we are on a time limit
            if (max_allowed_duration_seconds > 0):
                current_script_time = time.perf_counter()
                elapsed_time_since_start = current_script_time - script_start_time
                if (elapsed_time_since_start >= max_allowed_duration_seconds):
                    #If too much time has elapsed, then break out of the loop.
                    #We will simply handle loading the rest of the files another day.
                    break

            if (p.uid is None):
                print("{Fore.RED}Skipping participant with id of NONE{Style.RESET_ALL}")
                p_idx += 1
                continue

            print(f"{Fore.RED}Calculating metadata for participant {p.uid}{Style.RESET_ALL} ({p_idx}/{total_participants})")
            p_idx += 1

            p.CalculateAnalysisMetrics()
            p.is_dirty = False
            p.save()

            #Now let's also make sure the post-hoc-calculated VNS signal has been calculated for each activity
            #So let's iterate over each visit
            for v in p.children:
                #And iterate over each activity
                for a in v.children:
                    #Make sure we are working with a REPLAY activity (not a ReTrieve activity or a Manual Stim Mode activity)
                    if (isinstance(a, RePlayActivity)):
                        #Check to see if the VNS signal has already been calculated for this activity
                        #If not, then calculate it
                        a.GetVNSSignal()

        script_end_time = time.perf_counter()
        print(f"SCRIPT RUNNING DURATION: {script_end_time - script_start_time} seconds")
        print(f"CURRENT DATETIME: {datetime.now().isoformat()}")

        print ("DONE!")
                
    @staticmethod
    def __reload_flagged_sessions(participant_reference_json, replay_data_location, fixes_json):

        #Print a message to the user
        print("Currently reloading flagged sessions")
        
        #Get the study object
        current_study = RePlayStudy.GetStudy()

        #Walk the file tree
        f = DatabaseOperations.__create_list_of_files_to_load(replay_data_location, participant_reference_json, True)

        #Get the filenames only
        filenames_only = [row[1] for row in f]

        #Make a copy of the list of flagged activities
        flagged_activity_list = list(current_study.flagged_sessions)

        #Iterate over the list of flagged activities
        for current_activity_id in flagged_activity_list:

            #Get the current activity from the database
            current_activity = None
            try:
                current_activity = BaseActivity.objects.get(id=current_activity_id)
            except:
                pass

            print(f"Attempting to reload activity with id {current_activity_id}")

            controller_data_session_duration = float("nan")
            game_data_session_duration = float("nan")

            #If we successfully fetched the activity from the database...
            if (isinstance(current_activity, RePlayActivity)):

                #Get the participant id
                current_participant_id = current_activity.uid

                #Print a message to the user
                print(f"The activity was found in the database. The UID is {current_participant_id}")
                
                #Get the filename of the controller data file
                controller_data_filename = ""
                if (current_activity.controller_data is not None):
                    controller_data_filename = current_activity.controller_data.filename

                    #Print a message to the user
                    print(f"This activity contains the following controller data file: {controller_data_filename}")

                    #See if this filename is in the list of files that are possible to load in
                    index_of_file = -1
                    try:
                        index_of_file = filenames_only.index(controller_data_filename)
                    except:
                        index_of_file = -1

                        #Print a message to the user
                        print("WARNING: This file was NOT found in the file system! Skipping this file...")

                    #If the filename was found, let's load it in
                    if (index_of_file >= 0):
                        #Print a message to the user
                        print("The file was found in the file system. Loading file...")

                        #Get the path where the file is located
                        this_file_parameter = f[index_of_file]

                        #Set the full path + filename combination
                        this_full_file_path = this_file_parameter[0] + "/" + this_file_parameter[1]

                        #Load in the RePlay data file
                        (retval, datafile_object) = DatabaseOperations.__handle_loading_replay_datafile(participant_reference_json, fixes_json, this_full_file_path, this_file_parameter, True)

                        #If the new datafile was successfully loaded
                        if (retval == 2) and (datafile_object is not None):
                            #Print a message to the user
                            print("The file was successfully loaded. Now associating the file with the activity...")

                            #Get the existing controller data RePlayDataFile object
                            controller_data_datafile_object = current_activity.controller_data

                            #Get the existing controller data RePlayControllerData object
                            controller_data_data_object = controller_data_datafile_object.AccessData()

                            #Unlink the old data file from the activity
                            current_activity.SetControllerData(None)

                            #Eliminate the existing controller data RePlayControllerData object from the database
                            controller_data_data_object.delete()

                            #Eliminate the existing controller data RePlayDataFile object from the database
                            controller_data_datafile_object.delete()

                            #Set the new RePlayDataFile object as the controller data for the activity
                            current_activity.SetControllerData(datafile_object)                       

                            #Save the activity
                            current_activity.save()     

                            #Get the duration of the session according to the controller data object
                            session_data = datafile_object.AccessData()
                            if ((session_data is not None) and (hasattr(session_data, "signal_time")) and (len(session_data.signal_time) > 0)):
                                #Grab the last element of the "signal time" array
                                #This should be essentially how long the session was
                                controller_data_session_duration = session_data.signal_time[-1]                                 

                            #Print a message to the user
                            print("This file has been successfully processed.")
                        else:
                            print("WARNING: There was an issue loading the datafile into the database!")
                else:
                    print("This activity does not contain a CONTROLLER DATA file.")

                #Get the filename of the game data file
                game_data_filename = ""
                if (current_activity.game_data is not None):
                    game_data_filename = current_activity.game_data.filename

                    #Print a message to the user
                    print(f"This activity contains the following game data file: {game_data_filename}")                    
                else:
                    print("This activity does not contain a GAME DATA file. Attempting to find game data file...")
                    if (controller_data_filename != ""):
                        print("Composing possible game data file name using the controller data file name...")
                        controller_data_filename_parts = os.path.splitext(controller_data_filename)
                        game_data_filename = controller_data_filename_parts[0] + "_gamedata.txt"

                        print(f"Composed game data file name: {game_data_filename}")
                    else:
                        print("Unable to compose an acceptable game data file name. Skipping this...")

                #If the game data filename is not an empty string...
                if (game_data_filename != ""):
                    #Print a message to the user
                    print(f"Attempting to load game data file...")

                    #See if this filename is in the list of files that are possible to load in
                    index_of_file = -1
                    try:
                        index_of_file = filenames_only.index(game_data_filename)
                    except:
                        index_of_file = -1

                        #Print a message to the user
                        print("WARNING: This file was NOT found in the file system! Skipping this file...")

                    #If the filename was found, let's load it in
                    if (index_of_file >= 0):
                        #Print a message to the user
                        print("The file was found in the file system. Loading file...")

                        #Get the path where the file is located
                        this_file_parameter = f[index_of_file]

                        #Set the full path + filename combination
                        this_full_file_path = this_file_parameter[0] + "/" + this_file_parameter[1]

                        #Load in the RePlay data file
                        (retval, datafile_object) = DatabaseOperations.__handle_loading_replay_datafile(participant_reference_json, fixes_json, this_full_file_path, this_file_parameter, True)

                        #If the new datafile was successfully loaded
                        if (retval == 2) and (datafile_object is not None):
                            #Print a message to the user
                            print("The file was successfully loaded. Now associating the file with the activity...")

                            #Get the existing game data RePlayDataFile object
                            game_data_datafile_object = current_activity.game_data

                            #Get the existing game data RePlayGameData object
                            game_data_data_object = None
                            if (game_data_datafile_object is not None):
                                game_data_data_object = game_data_datafile_object.AccessData()

                            #Unlink the old data file from the activity
                            current_activity.SetGameData(None)

                            #Eliminate the existing controller data RePlayControllerData object from the database
                            if (game_data_data_object is not None):
                                try:
                                    game_data_data_object.delete()
                                except:
                                    print("Error while deleting game_data_data_object")

                            #Eliminate the existing controller data RePlayDataFile object from the database
                            if (game_data_datafile_object is not None):
                                try:
                                    game_data_datafile_object.delete()
                                except:
                                    print("Error while deleting game_data_datafile_object")

                            #Set the new RePlayDataFile object as the controller data for the activity
                            current_activity.SetGameData(datafile_object)                       

                            #Save the activity
                            current_activity.save()     

                            #Get the duration of the session according to the game data object
                            session_data = datafile_object.AccessData()
                            if ((session_data is not None) and (hasattr(session_data, "signal_time")) and (len(session_data.signal_time) > 0)):
                                #Grab the last element of the "signal time" array
                                #This should be essentially how long the session was
                                game_data_session_duration = session_data.signal_time[-1]                              

                            #Print a message to the user
                            print("This file has been successfully processed.")
                        else:
                            print("WARNING: There was an issue loading the datafile into the database!")
                else:
                    print("No acceptable game data filename was found to load in...")


                #Set the duration for the activity
                if (not math.isnan(game_data_session_duration)):
                    current_activity.duration = game_data_session_duration
                    current_activity.save()
                else:
                    if (not math.isnan(controller_data_session_duration)):
                        current_activity.duration = controller_data_session_duration
                        current_activity.save()

            else:
                #Print a message to the user
                print("WARNING: This activity was not found in the database!")

            #Remove the current activity from the list of flagged sessions
            current_study.RemoveSessionFlag(current_activity_id)
