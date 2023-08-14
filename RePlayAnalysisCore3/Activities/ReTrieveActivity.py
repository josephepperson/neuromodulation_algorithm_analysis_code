from mongoengine import *
import numpy
import re
import pandas
import os
import math

from RePlayAnalysisCore3.Activities.BaseActivity import BaseActivity
from RePlayAnalysisCore3.RePlayExercises import RePlayExercises
from RePlayAnalysisCore3.DataFiles.ReTrieveDataFile import ReTrieveDataFile
from RePlayAnalysisCore3.RePlayStudy import RePlayStudy

from RePlayAnalysisCore3.Activities.ReTrieveAnalysisCore import rtvPreprocess
from RePlayAnalysisCore3.Activities.ReTrieveAnalysisCore import rtvHelpers
from RePlayAnalysisCore3.Activities.ReTrieveAnalysisCore import rtvMeta

class ReTrieveActivity(BaseActivity):

    #region Fields

    datafile = GenericReferenceField()

    valid_retrieve_activity = BooleanField()

    set_name = StringField()
    set_id = IntField()
    set_difficulty = IntField()
    object_ids = ListField(FloatField())
    object_id_sequence = ListField(FloatField())
    object_correct_times = ListField(FloatField())
    object_search_times = ListField(FloatField())
    object_return_times = ListField(FloatField())

    restore_stim_attempts = DictField()
    restore_status_updates = DictField()
    restore_log = DictField()

    stim_times = ListField(FloatField())

    hand_location_times = ListField(FloatField())
    hand_location_xvals = ListField(FloatField())
    hand_location_yvals = ListField(FloatField())

    events_condensed = DictField()

    #endregion

    #region Constructor
    
    def __init__(self, *args, **values):
        super().__init__(*args, **values)
        self.activity_name = "ReTrieve"

    #endregion

    #region Methods that return stimulations logged by RePlay/ReTrieve for this activity

    def GetStimulationRequestsForActivity (self):
        #TO DO: Implement this
        return []

    def GetSuccessfulStimulationsForActivity (self):
        #TO DO: Implement this
        return []

    def GetFailedStimulationsForActivity (self):
        #TO DO: Implement this
        return []

    #endregion    
    
    #region Overrides

    def GetExerciseName(self):
        return self.activity_name

    def GetDifficulty(self):
        return self.set_difficulty

    def GetNormalizedDifficulty(self):
        try:
            retrieve_min_difficulty = 0
            retrieve_max_difficulty = 3
            retrieve_normalized_difficulty = (self.set_difficulty) / (retrieve_max_difficulty - retrieve_min_difficulty)
            return retrieve_normalized_difficulty
        except:
            return super().GetNormalizedDifficulty()

    def GetGameSignal (self, use_real_world_units = True, apply_trim = True):        
        try:
            hand_signal = {}
            hand_keylist = []
            prev_key = 0.0
            for key, value in self.events_condensed.items():
                if "HAND" in value:
                    hand_keylist.append(key)
            hand_keylist = sorted(hand_keylist)
            for key in hand_keylist:
                if "ENTER" in self.events_condensed[key]:
                    hand_signal[prev_key+.1] = 0
                    hand_signal[key] = 0
                    prev_key = key
                if "EXIT" in self.events_condensed[key]:
                    hand_signal[prev_key+.1] = 5
                    hand_signal[key] = 5
                    prev_key = key

            hand_signal_keys_list_unsorted = list(hand_signal.keys())
            hand_signal_values_unsorted = list(hand_signal.values())
            hand_signal_ts = sorted([float(x) for x in hand_signal_keys_list_unsorted])
            hand_signal_values = [x for _, x in sorted(zip(hand_signal_keys_list_unsorted, hand_signal_values_unsorted), key=lambda pair: float(pair[0]))]
            
            return (hand_signal_values, hand_signal_ts, "Hand Presence Signal", 0, len(hand_signal_ts), None) 
        except:
            return super().GetGameSignal(use_real_world_units, apply_trim)                       

    def GetRepetitionData(self):
        return (len(self.object_search_times), self.object_search_times)
        
    #endregion

    #region Methods that are similar to methods on RePlayActivity, but don't exactly match

    def GetVNSParameters(self):
        #TODO: extract VNS parameter data from ReTrieve datafiles and transform into the correct format
        pass
    
    def GetVNSSignal (self):
        try:
            stim_signal = numpy.ones(len(self.stim_times))
            return (stim_signal, self.stim_times, "Stim Timestamps", 0, len(stim_signal))
        except:
            return None

    #endregion    

    #region Methods for calculating analysis metrics for this activity

    def CalculateAnalysisMetrics (self):
        #Grab the names of all valid variables/metrics that we could calculate for this activity
        variables_to_calculate = RePlayExercises.get_available_variables_for_game(self.activity_name)

        #Iterate through each metric and calculate each one
        for i in range(0, len(variables_to_calculate)):
            self.CalculateIndividualAnalysisMetric(variables_to_calculate[i])

        #Update the master dataframe
        RePlayStudy.GetStudy().UpdateActivityInAggregatedMetrics(self)            

    def CalculateIndividualAnalysisMetric (self, variable_name):
        #Calculate the value of this metric
        variable_value = self.__calculate_variable_value(variable_name)

        #If this activity's tags does not create a Btree for "metrics", let's create it.
        self._assert_metrics_in_tags()

        #Insert the calculate value in the collection of tags    
        self.tags["metrics"][variable_name] = variable_value           

    def __calculate_variable_value (self, selected_variable_str):
        if (selected_variable_str in RePlayExercises.selectable_variables_common_independent):
            return float(self.__calculate_common_independent_variable(selected_variable_str))
        elif (selected_variable_str in RePlayExercises.selectable_variables_common_dependent):
            return float(self.__calculate_common_dependent_variable(selected_variable_str))
        else:
            idx_of_final_parantheses = selected_variable_str.rfind(")")
            if (idx_of_final_parantheses >= 0):
                altered_variable_str = selected_variable_str[(idx_of_final_parantheses+1):].strip()

                #Now let's see which game variable we should analyze and return
                return float(self.__calculate_game_variable(altered_variable_str))
            else:
                return float("NaN")

    def __calculate_common_independent_variable(self, selected_variable_str):
        if (selected_variable_str == "Difficulty"):
            return float(self.GetDifficulty())
        elif (selected_variable_str == "Duration"):
            return float(self.duration)
        else:
            return float("NaN")  

    def __calculate_common_dependent_variable(self, selected_variable_str):
        result = float("NaN")
        if (selected_variable_str == "VNS trigger events [logged by ReStore]"):
            result = len(self.GetStimulationsFromReStoreDatalogs())
        elif (selected_variable_str == "Total repetitions"):
            (total_reps, _) = self.GetRepetitionData()
            result = total_reps

        if (result is None):
            result = float("NaN")
        return result

    def __calculate_game_variable (self, variable_name):
        result = float("NaN")

        if (variable_name == "Percent correct"):
            num_objects_returned = len(self.object_return_times)
            if (num_objects_returned > 0):
                num_correct_objects_returned = numpy.count_nonzero(self.object_correct_times)
                result = (float(num_correct_objects_returned) / float(num_objects_returned)) * 100.0
        elif (variable_name == "Retrieval rate"):
            num_objects_returned = len(self.object_return_times)
            if (self.duration > 0):
                session_duration_minutes = float(self.duration) / 60.0
                result = float(num_objects_returned) / session_duration_minutes
        elif (variable_name == "Success rate"):
            session_duration_minutes = float(self.duration) / 60.0
            if (self.duration > 0):
                num_correct_objects_returned = numpy.count_nonzero(self.object_correct_times)
                result = float(num_correct_objects_returned) / session_duration_minutes
        elif (variable_name == "Mean search time per object"):
            if (len(self.object_search_times) > 0):
                result = numpy.nanmean(self.object_search_times) / 60.0 #Units of minutes
        elif (variable_name == "Total search time"):
            if (len(self.object_search_times) > 0):
                result = numpy.sum(self.object_search_times) / 60.0 #Units of minutes

        return result

    #endregion

    #region Methods specific to the ReTrieveActivity class

    def ParseFilename (self, filename):
        
        tentative_datetime = None
        tentative_UID = None

        #Parse Date
        dateFormatIndex = 0
        dateString = ""
        for datetimeRegexFormat in rtvMeta.DATETIME_REGEX_FORMATS:
            try:
                dateString = re.search(datetimeRegexFormat, filename).group(0)
                tentative_datetime = rtvHelpers.stringToDatetime(dateString, rtvMeta.DATETIME_FORMATS[dateFormatIndex])
                break
            except Exception as e:
                dateFormatIndex = dateFormatIndex + 1
                pass

        #Parse UID
        try:
            tentative_UID = filename.partition(dateString)[0]
            tentative_UID = tentative_UID.rstrip('_')
        except Exception as e:
            print(str(e))

        #If recorded data in the file and filename are mismatched, throw a warning
        if self.uid != tentative_UID:
            print("\tWARNING: UID = " + str(self.uid) + " does not match " + filename)
        if self.start_time != tentative_datetime:
            print("\tWARNING: Date = " + rtvHelpers.datetimeToString(self.start_time, rtvMeta.DATETIME_FORMATS[0]) + " does not match " + filename)

        return (tentative_datetime, tentative_UID)

    def PopulateReTrieveActivity (self, retrieve_datafile_object, prioritize_filename = False):
        #Assign the datafile to this activity
        self.datafile = retrieve_datafile_object

        #Get filename without path or extension
        filename = os.path.splitext(self.datafile.filename)[0] 
        
        if (isinstance(self.datafile, ReTrieveDataFile)):
            #Copy the json data into the activity
            self.raw_json_data = self.datafile.json_data

            #If UID was recorded in this file, use it
            if "Meta-UID" in self.raw_json_data.keys():
                self.uid = self.raw_json_data["Meta-UID"]
            
            #If Date was recorded in this file, use it
            if self.raw_json_data["Meta-Date"]:
                for datetimeFormat in rtvMeta.DATETIME_FORMATS:
                    try:
                        self.start_time = rtvHelpers.stringToDatetime(self.raw_json_data["Meta-Date"], datetimeFormat)
                    except Exception as e:
                        pass
            else:
                print("ERROR: No date contained in " + filename)

            #If filename is prioritized over internal data, parse the filename for Date and UID
            if (prioritize_filename):
                #Extract Date from filename
                try:
                    #Extract optional_datetime from filename for comparison
                    (tentative_datetime, tentative_uid) = self.ParseFilename(filename)
                    self.start_time = tentative_datetime
                    self.uid = tentative_uid
                except Exception as e:
                    raise e
            
            #Extract restore data if present
            if ("Restore-Event-Log" in self.raw_json_data):
                self.restore_log = self.raw_json_data["Restore-Event-Log"]
            if ("Restore-Status-Updates" in self.raw_json_data):
                self.restore_status_updates = self.raw_json_data["Restore-Status-Updates"]
            if ("Restore-Stim-Attempts" in self.raw_json_data):
                self.restore_stim_attempts = self.raw_json_data["Restore-Stim-Attempts"]

            #Clean our data for analysis
            cleanedData = rtvPreprocess.cleanDataForAnalysis(self.raw_json_data)

            #If our data isn't empty, do some finishing calculations
            if len(cleanedData) > 0:

                [
                    setName,
                    setID,
                    setDiff,
                    objectSearchTimes,
                    numObjectsReturned,
                    tapsRecorded,
                    IDsequence,
                    objectIDs,
                    handLocTimes,
                    Xloc,
                    Yloc,
                    ec,
                    ecKeys,
                    sessionTime,
                    stimTimes,
                    numStims,
                ] = cleanedData

                
                # Directly transfer cleaned data to this object

                self.set_difficulty = 1
                for k in rtvMeta.difficultySwitcher.keys():
                    if (rtvMeta.difficultySwitcher[k] == setDiff):
                        self.set_difficulty = k
                
                self.set_id = setID
                self.set_name = setName
                self.object_search_times = objectSearchTimes
                self.object_correct_times = tapsRecorded
                self.object_id_sequence = IDsequence
                self.object_ids = objectIDs
                self.duration = sessionTime
                self.stim_times = stimTimes

                if (self.duration is None):
                    self.duration = float("NaN")
                
                # Combine associated lists in to single objects
                self.events_condensed = {str(k): v for k, v in zip(ecKeys, ec)}
                self.hand_loc = [(time, x, y) for time, x, y in zip(handLocTimes, Xloc, Yloc)]

                # Calculate Object Return Time
                obj_return_keylist = []
                for key, value in self.events_condensed.items():
                    if "BLOCK" in value:
                        obj_return_keylist.append(float(key))
                obj_return_keylist = sorted(obj_return_keylist)
                self.object_return_times = obj_return_keylist                

                # Mark valid activity
                self.valid_retrieve_activity = True
            else:
                # Invalid retrieve datafile
                self.valid_retrieve_activity = False

    def GetSetID(self):
        return self.set_id

    def GetSetName(self):
        return self.set_name

    def GetDuration(self):
        return self.duration

    def GetNumRepetitions(self):
        return len(self.object_return_times)

    def GetObjectReturnTimes (self):
        return self.object_return_times

    def GetObjectCorrectTimes (self):
        return self.object_correct_times

    def GetPercentCorrect (self):
        self._assert_metrics_in_tags()
        result = float("NaN")
        if ("Percent correct" in self.tags["metrics"]):
            result = self.tags["metrics"]["Percent correct"]
        return result

    def GetRetrievalRate (self):
        self._assert_metrics_in_tags()
        result = float("NaN")
        if ("Retrieval rate" in self.tags["metrics"]):
            result = self.tags["metrics"]["Retrieval rate"]
        return result

    def GetSuccessRate (self):
        self._assert_metrics_in_tags()
        result = float("NaN")
        if ("Success rate" in self.tags["metrics"]):
            result = self.tags["metrics"]["Success rate"]
        return result

    def GetMeanSearchTime (self):
        self._assert_metrics_in_tags()
        result = float("NaN")
        if ("Mean search time per object" in self.tags["metrics"]):
            result = self.tags["metrics"]["Mean search time per object"]
        return result

    def GetTotalSearchTime (self): 
        self._assert_metrics_in_tags()
        result = float("NaN")
        if ("Total search time" in self.tags["metrics"]):
            result = self.tags["metrics"]["Total search time"]
        return result

    def GetCorrectTimes (self):
        try:
            correct_signal = map(1, numpy.arange(0,len(self.object_correct_times)))
            return (correct_signal, self.object_correct_times, "Correct Object Timestamps", 0, int(self.duration))
        except:
            return None

    def GetSearchTimes (self):
        return self.object_search_times

    def GetStimRequestInfo (self):
        return self.restore_stim_attempts

    #endregion    

