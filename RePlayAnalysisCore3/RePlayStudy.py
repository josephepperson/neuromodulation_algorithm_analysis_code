import warnings

from RePlayAnalysisCore3.RePlayStudyAggregatedMetrics import RePlayStudyAggregatedMetrics
from RePlayAnalysisCore3.RePlayStudyAggregatedVisitMetrics import RePlayStudyAggregatedVisitMetrics
warnings.simplefilter(action='ignore', category=FutureWarning)

from mongoengine import *
from numpy.core.records import fromarrays
from scipy.io import savemat
import pandas
import json
from bson import BSON

from RePlayAnalysisCore3.RePlayExercises import RePlayExercises
from RePlayAnalysisCore3.LoadedFilesCollection import *
from RePlayAnalysisCore3.RePlayUtilities import RePlayUtilities
from RePlayAnalysisCore3.RePlayVisit import RePlayVisit

class RePlayStudy(Document):
    #A class-level field to hold the singleton instance of this class
    singleton_instance = None

    #Defining some metadata telling the db what collection to use for this class
    meta = {
        'collection':'RePlayStudy',
        'strict':False
    }    

    #region Fields that ARE saved to the database

    study_name = StringField()
    study_groups = DictField()
    last_update = DateTimeField()
    all_update_datetimes = ListField(DateTimeField())

    aggregated_metrics_object = GenericReferenceField()
    visit_metrics_object = GenericReferenceField()

    aggregated_metrics_object_gridfs = FileField()
    visit_metrics_object_gridfs = FileField()

    flagged_sessions = ListField(StringField())

    #This field is deprecated. It remains here temporarily for some backward compatibility and for porting purposes.
    aggregated_metrics = DictField()

    #endregion

    #region Constructor and singleton getter

    def __init__(self, *args, **values):
        super().__init__(*args, **values)
        self.aggregated_metrics_df = None
        self.is_aggregated_metrics_loaded = False

        self.visit_metrics_df = None
        self.is_visit_metrics_loaded = False

    @staticmethod
    def GetStudy(force_read_from_db = False):
        if (RePlayStudy.singleton_instance is None) or (force_read_from_db):
            #Check to see if a study already exists in the database
            if (RePlayStudy.objects().count() > 0):
                #If so, return the study object
                RePlayStudy.singleton_instance = RePlayStudy.objects().first()
            else:
                #If no study exists yet, then create one, save it to the database, and return it
                RePlayStudy.singleton_instance = RePlayStudy().save()

        return RePlayStudy.singleton_instance

    #endregion

    #region The folowing methods are for dealing with flagged sessions

    def FlagSessionForReloading (self, session_id_str):
        if (session_id_str not in self.flagged_sessions):
            self.flagged_sessions.append(session_id_str)
            self.save()

    def RemoveSessionFlag (self, session_id_str):
        if (session_id_str in self.flagged_sessions):
            self.flagged_sessions.remove(session_id_str)
            self.save()

    def IsSessionFlagged (self, session_id_str):
        if (session_id_str in self.flagged_sessions):
            return True
        else:
            return False

    #endregion

    #region The following methods are for dealing with visit metrics

    _visit_keys_for_filtering = [
        "Object ID", 
        "Participant ID", 
        "Participant Group Name",
        "Visit Date", 
        "Is Participant Excluded",
        "Is Visit Excluded"
    ]    

    def _assert_visit_metrics_object(self):
        #if (self.visit_metrics_object is None) or (not (isinstance(self.visit_metrics_object, RePlayStudyAggregatedVisitMetrics))):
        #    self.visit_metrics_object = RePlayStudyAggregatedVisitMetrics()
        #    self.visit_metrics_object.save()
        #    self.save()
        return

    def _load_visit_metrics_dataframe_if_not_already_loaded(self):
        if (not self.is_visit_metrics_loaded):
            self._load_visit_metrics_dataframe()

    def _load_visit_metrics_dataframe (self):
        self._assert_visit_metrics_object()

        visit_metrics_bson = self.visit_metrics_object_gridfs.read()
        visit_metrics_dict = BSON.decode(visit_metrics_bson)
        self.visit_metrics_df = pandas.read_json(json.dumps(visit_metrics_dict))

        #self.visit_metrics_df = pandas.read_json(json.dumps(self.visit_metrics_object.aggregated_visit_metrics))
        self._create_visit_metrics_if_necessary()
        self.is_visit_metrics_loaded = True

    def _save_visit_metrics_dataframe (self):
        self._assert_visit_metrics_object()

        visit_metrics_dict = json.loads(pandas.DataFrame.to_json(self.visit_metrics_df))
        visit_metrics_bson = BSON.encode(visit_metrics_dict)
        self.visit_metrics_object_gridfs.new_file()
        self.visit_metrics_object_gridfs.write(visit_metrics_bson)
        self.visit_metrics_object_gridfs.close()

        #self.visit_metrics_object.aggregated_visit_metrics = json.loads(pandas.DataFrame.to_json(self.visit_metrics_df))
        #self.visit_metrics_object.save()
        self.save()

        self.is_visit_metrics_loaded = True
    
    def _create_visit_metrics_if_necessary (self):
        if (len(self.visit_metrics_df.columns) == 0):
            keys = []
            keys.extend(RePlayStudy._visit_keys_for_filtering)
            keys.extend(RePlayVisit.visit_metrics)
            self.visit_metrics_df = pandas.DataFrame([], columns=keys)
            self._save_visit_metrics_dataframe()

    def GetVisitMetricsDataFrame(self):
        self._load_visit_metrics_dataframe_if_not_already_loaded()
        return self.visit_metrics_df

    def SaveVisitMetricsDataFrame(self):
        self._save_visit_metrics_dataframe()

    def UpdateVisitInVisitMetrics(self, visit, save_df = True):
        self._load_visit_metrics_dataframe_if_not_already_loaded()

        if ("metrics" not in visit.tags):
            return

        participant = visit.parent
        if (participant is None):
            return            

        visit_object_id = str(visit.pk)
        indices_that_match = self.visit_metrics_df[self.visit_metrics_df["Object ID"] == visit_object_id].index.to_list()
        if (len(indices_that_match) > 0):
            idx = indices_that_match[0]

            #Update the columns used for filtering
            self.visit_metrics_df.loc[idx, "Participant Group Name"] = participant.group
            self.visit_metrics_df.loc[idx, "Is Participant Excluded"] = participant.excluded
            self.visit_metrics_df.loc[idx, "Is Visit Excluded"] = visit.excluded

            #Update the columns that contain calculated analysis metrics
            metrics = RePlayVisit.get_all_visit_metrics(False)
            for var in metrics:
                prepended_var = RePlayVisit.convert_to_qualified_visit_metric_string(var)

                #Make sure a column exists in the dataframe for this metric
                if (var not in self.visit_metrics_df.columns):
                    #If a column does not yet exist, let's make a column, and populate it with
                    #default values
                    self.visit_metrics_df[var] = float("NaN")

                #Now add the value of this metric to the dataframe
                if (prepended_var in visit.tags["metrics"]):
                    self.visit_metrics_df.loc[idx, var] = visit.tags["metrics"][prepended_var]
                else:
                    self.visit_metrics_df.loc[idx, var] = float("NaN")            
        else:
            #Create a new row that we will append to the dataframe
            df_newrow = {}

            #Insert keys for each of the variables used for filtering the data
            df_newrow["Object ID"] = visit_object_id
            df_newrow["Participant ID"] = participant.uid
            df_newrow["Participant Group Name"] = participant.group
            df_newrow["Visit Date"] = visit.start_time.date().isoformat()
            df_newrow["Is Participant Excluded"] = participant.excluded
            df_newrow["Is Visit Excluded"] = visit.excluded

            #Insert keys for each of the analysis metrics
            metrics = RePlayVisit.get_all_visit_metrics(False)
            for var in metrics:
                prepended_var = RePlayVisit.convert_to_qualified_visit_metric_string(var)
                if (prepended_var in visit.tags["metrics"]):
                    df_newrow[var] = visit.tags["metrics"][prepended_var]
                else:
                    df_newrow[var] = float("NaN")

            #Add the row to the dataframe
            self.visit_metrics_df = self.visit_metrics_df.append(df_newrow, ignore_index=True)            

        #Save the dataframe to the database
        if (save_df):
            self._save_visit_metrics_dataframe()

    #endregion

    #region The following methods are for dealing with aggregated metrics

    _keys_for_filtering = [
        "Object ID", 
        "Participant ID", 
        "Participant Group Name",
        "Visit Date", 
        "Start Time", 
        "Is Participant Excluded",
        "Is Visit Excluded",
        "Is Activity Excluded",
        "Activity Game Name",
        "Activity Exercise Name",
        "Activity Hand Used"
    ]

    def _assert_aggregated_metrics_object (self):
        #if (self.aggregated_metrics_object is None) or (not (isinstance(self.aggregated_metrics_object, RePlayStudyAggregatedMetrics))):
        #    self.aggregated_metrics_object = RePlayStudyAggregatedMetrics()
        #
        #    if (hasattr(self, "aggregated_metrics")):
        #        if (self.aggregated_metrics is not None) and (len(self.aggregated_metrics) > 0) and (len(self.aggregated_metrics_object.aggregated_metrics) == 0):
        #            self.aggregated_metrics_object.aggregated_metrics = self.aggregated_metrics
        #
        #    self.aggregated_metrics_object.save()
        #    self.save()
        return

    def _load_metrics_dataframe_if_not_already_loaded(self):
        if (not self.is_aggregated_metrics_loaded):
            self._load_metrics_dataframe()

    def _load_metrics_dataframe (self):
        self._assert_aggregated_metrics_object()

        aggregated_metrics_bson = self.aggregated_metrics_object_gridfs.read()
        aggregated_metrics_dict = BSON.decode(aggregated_metrics_bson)
        self.aggregated_metrics_df = pandas.read_json(json.dumps(aggregated_metrics_dict))

        #self.aggregated_metrics_df = pandas.read_json(json.dumps(self.aggregated_metrics_object.aggregated_metrics))
        self._create_aggregated_metrics_if_necessary()

        self.is_aggregated_metrics_loaded = True

    def _save_metrics_dataframe (self):
        self._assert_aggregated_metrics_object()

        aggregated_metrics_dict = json.loads(pandas.DataFrame.to_json(self.aggregated_metrics_df))
        aggregated_metrics_bson = BSON.encode(aggregated_metrics_dict)
        self.aggregated_metrics_object_gridfs.new_file()
        self.aggregated_metrics_object_gridfs.write(aggregated_metrics_bson)
        self.aggregated_metrics_object_gridfs.close()        

        #self.aggregated_metrics_object.aggregated_metrics = json.loads(pandas.DataFrame.to_json(self.aggregated_metrics_df))
        #self.aggregated_metrics_object.save()
        self.save()

        self.is_aggregated_metrics_loaded = True

    def _create_aggregated_metrics_if_necessary (self):
        #Check to see if the dataframe has any existing columns
        if (len(self.aggregated_metrics_df.columns) == 0):
            #Create the set of keys to be used in the dictionary of aggregated metrics
            keys = []
            keys.extend(RePlayStudy._keys_for_filtering)
            keys.extend(RePlayExercises.get_all_variables())

            #Create an empty dataframe
            self.aggregated_metrics_df = pandas.DataFrame([], columns=keys)

            #Save the dataframe
            self._save_metrics_dataframe()

    def GetAggregatedMetricsDataFrame(self):
        self._load_metrics_dataframe_if_not_already_loaded()
        return self.aggregated_metrics_df

    def SaveAggregatedMetricsDataFrame(self):
        self._save_metrics_dataframe()

    def UpdateParticipantInclusionInAggregatedMetrics (self, participant, save_df = True):
        self._load_metrics_dataframe_if_not_already_loaded()

        #Find all rows that match this participant
        indices_that_match = self.aggregated_metrics_df[
            (self.aggregated_metrics_df["Participant ID"] == participant.uid)
        ].index.to_list()

        #Check to see if any rows match
        if (len(indices_that_match) > 0):

            #Iterate over each matching row and update the "Is Participant Excluded" column
            for idx in indices_that_match:
                self.aggregated_metrics_df.loc[idx, "Is Participant Excluded"] = participant.excluded

            #Save the dataframe
            if (save_df):
                self._save_metrics_dataframe()

    def UpdateParticipantGroupInAggregatedMetrics (self, participant, save_df = True):
        self._load_metrics_dataframe_if_not_already_loaded()

        #Find all rows that match this participant
        indices_that_match = self.aggregated_metrics_df[
            (self.aggregated_metrics_df["Participant ID"] == participant.uid)
        ].index.to_list()

        #Check to see if any rows match
        if (len(indices_that_match) > 0):

            #Iterate over each matching row and update the "Is Participant Excluded" column
            for idx in indices_that_match:
                self.aggregated_metrics_df.loc[idx, "Participant Group Name"] = participant.group

            #Save the dataframe
            if (save_df):
                self._save_metrics_dataframe()

    def UpdateVisitInclusionInAggregatedMetrics (self, visit, save_df = True):
        self._load_metrics_dataframe_if_not_already_loaded()

        #Grab the visit date in string format
        visit_date_str = visit.start_time.date().isoformat()
        
        #Make sure we have a valid participant associated with this visit
        participant = visit.parent
        if (participant is None):
            return

        #Find all rows that match this participant and this visit
        indices_that_match = self.aggregated_metrics_df[
            (self.aggregated_metrics_df["Participant ID"] == participant.uid) &
            (self.aggregated_metrics_df["Visit Date"] == visit_date_str)
        ].index.to_list()

        #Check to see if any rows match
        if (len(indices_that_match) > 0):

            #Iterate over each matching row and update the "Is Visit Excluded" column
            for idx in indices_that_match:
                self.aggregated_metrics_df.loc[idx, "Is Visit Excluded"] = visit.excluded
            
            #Save the dataframe
            if (save_df):
                self._save_metrics_dataframe()

    def UpdateActivityInAggregatedMetrics (self, activity, save_df = True):
        self._load_metrics_dataframe_if_not_already_loaded()

        #Make sure the activity contains calculate metrics
        if ("metrics" not in activity.tags):
            return

        #Get some basic information about this activity's participant and visit to which it belongs
        visit = activity.parent
        if (visit is None):
            return

        participant = visit.parent
        if (participant is None):
            return

        #Let's see if this activity already exists in the metrics dataframe
        activity_object_id = str(activity.pk)
        indices_that_match = self.aggregated_metrics_df[
            self.aggregated_metrics_df["Object ID"] == activity_object_id].index.to_list()
        if (len(indices_that_match) > 0):
            #If the activity already exists in the dataframe...

            #Get the index of the activity
            idx = indices_that_match[0]

            #Update the columns that are used for filtering
            self.aggregated_metrics_df.loc[idx, "Participant Group Name"] = participant.group
            self.aggregated_metrics_df.loc[idx, "Start Time"] = activity.start_time.isoformat()
            self.aggregated_metrics_df.loc[idx, "Is Participant Excluded"] = participant.excluded
            self.aggregated_metrics_df.loc[idx, "Is Visit Excluded"] = visit.excluded
            self.aggregated_metrics_df.loc[idx, "Is Activity Excluded"] = activity.excluded
            self.aggregated_metrics_df.loc[idx, "Activity Game Name"] = activity.activity_name
            self.aggregated_metrics_df.loc[idx, "Activity Exercise Name"] = activity.GetExerciseName()
            self.aggregated_metrics_df.loc[idx, "Activity Hand Used"] = activity.GetHandName()

            #Update the columns that contain calculated analysis metrics
            metrics = RePlayExercises.get_all_variables()
            for var in metrics:
                if (var in activity.tags["metrics"]):
                    self.aggregated_metrics_df.loc[idx, var] = activity.tags["metrics"][var]
                else:
                    self.aggregated_metrics_df.loc[idx, var] = float("NaN")
        else:
            #If the activity does not yet exist in the dataframe

            #Create a new row that we will append to the dataframe
            df_newrow = {}

            #Insert keys for each of the variables used for filtering the data
            df_newrow["Object ID"] = activity_object_id
            df_newrow["Participant ID"] = participant.uid
            df_newrow["Participant Group Name"] = participant.group
            df_newrow["Visit Date"] = visit.start_time.date().isoformat()
            df_newrow["Start Time"] = activity.start_time.isoformat()
            df_newrow["Is Participant Excluded"] = participant.excluded
            df_newrow["Is Visit Excluded"] = visit.excluded
            df_newrow["Is Activity Excluded"] = activity.excluded
            df_newrow["Activity Game Name"] = activity.activity_name
            df_newrow["Activity Exercise Name"] = activity.GetExerciseName()
            df_newrow["Activity Hand Used"] = activity.GetHandName()

            #Insert keys for each of the analysis metrics
            metrics = RePlayExercises.get_all_variables()
            for var in metrics:
                if (var in activity.tags["metrics"]):
                    df_newrow[var] = activity.tags["metrics"][var]
                else:
                    df_newrow[var] = float("NaN")

            #Add the row to the dataframe
            self.aggregated_metrics_df = self.aggregated_metrics_df.append(df_newrow, ignore_index=True)
        
        #Save the dataframe to the database
        if (save_df):
            self._save_metrics_dataframe()

    def DoesActivityMetricMatch (self, activity, metric):
        self._load_metrics_dataframe_if_not_already_loaded()

        #Make sure the activity contains calculate metrics
        if ("metrics" not in activity.tags):
            return False        

        #Let's see if this activity already exists in the metrics dataframe
        activity_object_id = str(activity.pk)
        indices_that_match = self.aggregated_metrics_df[
            self.aggregated_metrics_df["Object ID"] == activity_object_id].index.to_list()
        if (len(indices_that_match) > 0):
            #If the activity already exists in the dataframe...

            #Get the index of the activity
            idx = indices_that_match[0]

            #Get the value of the metric we are interested in
            df_metric_value = self.aggregated_metrics_df.loc[idx, metric]
            if (df_metric_value == activity.tags["metrics"][metric]):
                return True
        
        return False

    def OutputCompleteDataFrame (self, output_file_path, is_to_matlab):
        self.OutputDataframe(output_file_path, is_to_matlab, None, None, None, None, None, True)

    def OutputDataframe (self, output_file_path, is_to_matlab, participant_id, game_name, exercise_name, hand_used, variable_list, output_everything = False):
        self._load_metrics_dataframe_if_not_already_loaded()

        #Get the whole data frame for export
        selected_rows = self.aggregated_metrics_df

        #Remove rows of excluded visits or activities
        selected_rows = selected_rows[selected_rows["Is Visit Excluded"] == False]
        selected_rows = selected_rows[selected_rows["Is Activity Excluded"] == False]        

        if (not output_everything):
            if (participant_id != "All"):
                selected_rows = selected_rows[selected_rows["Participant ID"] == participant_id]
            if (game_name != "All"):
                selected_rows = selected_rows[selected_rows["Activity Game Name"] == game_name]
            if (exercise_name != "All"):
                selected_rows = selected_rows[selected_rows["Activity Exercise Name"] == exercise_name]
            if (game_name == "ReCheck") and (hand_used != "Both"):
                selected_rows = selected_rows[selected_rows["Activity Hand Used"] == hand_used]

            if (isinstance(variable_list, str)) and (variable_list == "All"):
                selected_dataset = selected_rows
            else:
                columns_to_export = ["Participant ID", "Visit Date", "Start Time", "Activity Game Name", "Activity Exercise Name", "Activity Hand Used"]
                if (isinstance(variable_list, list)):
                    columns_to_export.extend(variable_list)
                selected_dataset = selected_rows[columns_to_export]
        else:
            selected_dataset = selected_rows

        if (is_to_matlab):
            #For matlab, we want the result to be an "array of structs". To do this, we must take the following steps...

            #Remove any invalid columns that cannot be exported to Matlab
            original_column_headers = list(selected_dataset.columns.values)
            valid_column_headers = []
            for i in range(0, len(original_column_headers)):
                current_modified_column_name = RePlayUtilities.convert_string_to_lower_snake_case(original_column_headers[i])
                if (len(current_modified_column_name) <= 63):
                    valid_column_headers.append(original_column_headers[i])
            selected_dataset = selected_dataset[valid_column_headers]

            for cur_row_idx in range(0, len(selected_dataset)):
                for cur_col in self._keys_for_filtering:
                    if selected_dataset.iloc[cur_row_idx, selected_dataset.columns.get_loc(cur_col)] is None:
                        selected_dataset.iloc[cur_row_idx, selected_dataset.columns.get_loc(cur_col)] = ""

            #First, let's output the dataset using pandas' to_dict function with key/values pairs as key = column name and value = column values
            dataset_items = selected_dataset.to_dict(orient="list")

            #Next, let's maintain a copy of the original key names
            original_keys = list(dataset_items.keys())

            #Now let's create an array of arrays using the column values
            list_of_lists = []
            for k in original_keys:
                list_of_lists.append(dataset_items[k])
            
            #Now let's change the key names to be lower snake case strings
            modified_keys = original_keys.copy()
            for i in range(0, len(modified_keys)):
                modified_keys[i] = RePlayUtilities.convert_string_to_lower_snake_case(modified_keys[i])

            #Now let's use numpy to create a "record array". This array is in the format needed to output a struct array to matlab
            matlab_items = fromarrays(list_of_lists, names=modified_keys)
            matlab_dict = {"data" : matlab_items}

            #Now output the struct array as a matlab file
            savemat(output_file_path, matlab_dict, do_compression=True, long_field_names=True)
        else:
            selected_dataset.to_excel(output_file_path, "Calculated Variables")

    #endregion