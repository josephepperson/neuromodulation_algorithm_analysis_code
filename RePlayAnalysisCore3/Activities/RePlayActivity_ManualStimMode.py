from mongoengine import *
from RePlayAnalysisCore3.Activities.BaseActivity import BaseActivity
from RePlayAnalysisCore3.RePlayExercises import RePlayExercises
from RePlayAnalysisCore3.RePlayStudy import RePlayStudy

class RePlayActivity_ManualStimMode(BaseActivity):

    datafile = GenericReferenceField()

    stim_request_times = ListField(DateTimeField())
    successful_stim_times = ListField(DateTimeField())
    failed_stim_times = ListField(DateTimeField())
    messages_datetimes = ListField(DateTimeField())
    messages = ListField(StringField())
    full_messages_datetimes = ListField(DateTimeField())
    full_messages = ListField(StringField())
    
    def __init__(self, *args, **values):
        super().__init__(*args, **values)

    #region Methods for creating this activity during the db update process

    def populate_activity (self, loaded_datafile):

        self.datafile = loaded_datafile

        self.activity_name = "Manual Stimulation"
        self.uid = self.datafile.subject_id
        self.start_time = self.datafile.start_time
        self.duration = self.datafile.duration
        self.stim_request_times = self.datafile.stim_request_times_sent_to_restore
        self.successful_stim_times = self.datafile.successful_stim_times
        self.failed_stim_times = self.datafile.failed_stim_times
        self.messages_datetimes = self.datafile.messages_datetimes
        self.messages = self.datafile.messages
        self.full_messages_datetimes = self.datafile.full_messages_datetimes
        self.full_messages = self.datafile.full_messages        

    #endregion
    
    #region Methods to fetching and calculating commonly-used analysis metrics for this activity

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
            return float("NaN")

    def __calculate_common_independent_variable(self, selected_variable_str):
        if (selected_variable_str == "Duration"):
            return self.duration
        else:
            return float("NaN")

    def __calculate_common_dependent_variable(self, selected_variable_str):
        if (selected_variable_str == "VNS trigger events [logged by ReStore]"):
            return len(self.GetStimulationsFromReStoreDatalogs())
        if (selected_variable_str == "VNS trigger events [logged by RePlay]"):
            return len(self.successful_stim_times)
        else:
            return float("NaN")

    #endregion        

    #region Methods that return stimulations logged by RePlay/ReTrieve for this activity

    def GetStimulationRequestsForActivity (self):
        return self.stim_request_times

    def GetSuccessfulStimulationsForActivity (self):
        return self.successful_stim_times

    def GetFailedStimulationsForActivity (self):
        return self.failed_stim_times

    #endregion    