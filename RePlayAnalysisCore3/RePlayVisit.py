from mongoengine import *
import numpy
import math
import pandas
from datetime import datetime
from datetime import timedelta
from RePlayAnalysisCore3.RePlayExercises import RePlayExercises
from RePlayAnalysisCore3.Documents.DatabaseAnalysisUnitDocument import DatabaseAnalysisUnitDocument
import RePlayAnalysisCore3.RePlayStudy
from RePlayAnalysisCore3.ReStoreStimulationCollection import *

class RePlayVisit(DatabaseAnalysisUnitDocument):
    meta = {
        'collection':'RePlayVisit'
    }    

    start_time = DateTimeField()
    end_time = DateTimeField()

    def __init__(self, *args, **values):
        super().__init__(*args, **values)

    #region Methods to handle what happens when this visit is included/excluded

    def _handle_exclusion_toggled(self):
        #Update the master dataframe
        RePlayAnalysisCore3.RePlayStudy.RePlayStudy.GetStudy().UpdateVisitInclusionInAggregatedMetrics(self)        

    #endregion

    #region Methods for finding stimulations that occurred during this visit

    def GetReStoreStimulationObjectsDuringVisit(self):
        stims_during_this_visit = []
        current_visit_starttime = self.start_time
        current_visit_endtime = self.end_time
        current_participant = self.parent
        if (current_participant is not None):
            all_stims_for_this_participant = ReStoreStimulation.objects(uid = current_participant.uid)
            stims_during_this_visit = [x for x in all_stims_for_this_participant if ((x.stimulation_datetime >= current_visit_starttime) and (x.stimulation_datetime <= current_visit_endtime))]
        
        return stims_during_this_visit            

    def GetReStoreSuccessfulStimulationsDuringVisit (self):
        return self.__get_filtered_stimulation_data(True)

    def GetReStoreFailedStimulationsDuringVisit (self):
        return self.__get_filtered_stimulation_data(False)

    def __get_filtered_stimulation_data(self, is_successful_stims):
        stims_during_this_visit = []
        current_visit_starttime = self.start_time
        current_visit_endtime = self.end_time
        current_participant = self.parent
        if (current_participant is not None):
            all_stims_for_this_participant = ReStoreStimulation.objects(Q(uid = current_participant.uid) & Q(is_successful = is_successful_stims))
            stims_during_this_visit = [x.stimulation_datetime for x in all_stims_for_this_participant if ((x.stimulation_datetime >= current_visit_starttime) and (x.stimulation_datetime <= current_visit_endtime))]
        
        return stims_during_this_visit            

    #endregion

    #region Methods used for calculating certain analysis metrics

    def CalculateAnalysisMetrics (self):
        #If this activity's tags does not create a Btree for "metrics", let's create it.
        self._assert_metrics_in_tags()

        #Call the base class method to calculate analysis metrics
        super().CalculateAnalysisMetrics()        

        #Now let's do some specific stuff for visits
        for variable_name in RePlayVisit.visit_metrics:
            result = self.CalculateVisitMetric(variable_name)
            visit_variable_name = "(Visit) " + variable_name
            self.tags["metrics"][visit_variable_name] = result

    def CalculateVisitMetric(self, variable_name):
        result = float("NaN")

        if (variable_name in RePlayVisit.visit_metrics):

            if (variable_name == "Total repetitions"):

                intermediate_result = self.FetchAnalysisMetricIndividualData("Total repetitions")
                if (len(intermediate_result) > 0) and (any(~numpy.isnan(intermediate_result))):
                    result = float(numpy.nansum(intermediate_result))

            elif (variable_name == "Total gameplay duration"):

                intermediate_result = self.FetchAnalysisMetricIndividualData("Duration")
                if (len(intermediate_result) > 0) and (any(~numpy.isnan(intermediate_result))):
                    result = float(numpy.nansum(intermediate_result) / 60.0)

            elif ((variable_name == "Total visit duration") or 
                    (variable_name == "Total time not playing games") or
                    (variable_name == "Percent time not playing games") or
                    (variable_name == "Longest gap between playing games")):

                #Get all activities on this date
                activities_on_this_date = self.children

                #Sort the activities that we will be looking at in cronological order
                all_activity_start_times = [x.start_time for x in activities_on_this_date]
                sorted_indices = numpy.argsort(all_activity_start_times)

                total_gap = 0
                visit_start_time = None
                visit_end_time = None
                total_visit_duration = float("NaN")
                max_gap = float("NaN")
                percent_gap = float("NaN")

                previous_activity_stop_time = None
                
                #Iterate over each activity
                for activity_idx in range(0, len(sorted_indices)):

                    #Get the current activity
                    sorted_idx = sorted_indices[activity_idx]
                    current_activity = activities_on_this_date[sorted_idx]

                    #Skip this activity if it has been marked for exclusion
                    if (current_activity.excluded):
                        continue

                    current_activity_duration = current_activity.duration
                    if (current_activity_duration is None) or (math.isnan(current_activity_duration)):
                        current_activity_duration = 0

                    if (previous_activity_stop_time is None) or (visit_start_time is None):
                        visit_start_time = current_activity.start_time
                        previous_activity_stop_time = current_activity.start_time + timedelta(seconds=current_activity_duration)
                    else:
                        current_gap = (current_activity.start_time - previous_activity_stop_time).total_seconds()
                        total_gap += current_gap
                        if (math.isnan(max_gap) or (current_gap >= max_gap)):
                            max_gap = current_gap
                        
                        current_activity_end_time = current_activity.start_time + timedelta(seconds=current_activity_duration)
                        if (visit_end_time is None):
                            visit_end_time = current_activity_end_time
                        else:
                            if (current_activity_end_time > visit_end_time):
                                visit_end_time = current_activity_end_time

                        previous_activity_stop_time = current_activity_end_time

                if (visit_end_time is not None) and (visit_start_time is not None):
                    total_visit_duration = (visit_end_time - visit_start_time).total_seconds()
                    if (not math.isnan(total_visit_duration)) and (total_visit_duration > 0):
                        percent_gap = (total_gap / total_visit_duration) * 100.0                        

                if (variable_name == "Total visit duration"):
                    result = float(total_visit_duration / 60.0)
                elif (variable_name == "Total time not playing games"):
                    #Convert the data to units of minutes
                    result = float(total_gap / 60.0)
                elif(variable_name == "Percent time not playing games"):
                    result = float(percent_gap)
                elif(variable_name == "Longest gap between playing games"):
                    #Convert the data to units of minutes
                    result = float(max_gap / 60.0)

            elif (variable_name == "Total successful VNS trigger events [logged by ReStore]"):

                result = float(len(self.GetReStoreSuccessfulStimulationsDuringVisit()))

            elif (variable_name == "Total failed VNS trigger events [logged by ReStore]"):

                result = float(len(self.GetReStoreFailedStimulationsDuringVisit()))

            elif (variable_name == "Total VNS trigger requests [logged by RePlay]"):

                result = 0
                for activity in self.children:
                    result += float(len(activity.GetStimulationRequestsForActivity()))

            elif (variable_name == "Total successful VNS trigger events [logged by RePlay]"):

                result = 0
                for activity in self.children:
                    result += float(len(activity.GetSuccessfulStimulationsForActivity()))

            elif (variable_name == "Total failed VNS trigger events [logged by RePlay]"):

                result = 0
                for activity in self.children:
                    result += float(len(activity.GetFailedStimulationsForActivity()))

            elif (variable_name == "Ratio of RePlay VNS requests to ReStore VNS successes"):

                replay_requests = 0
                for activity in self.children:
                    replay_requests += float(len(activity.GetStimulationRequestsForActivity()))                
           
                restore_successes = float(len(self.GetReStoreSuccessfulStimulationsDuringVisit()))                    

                try:
                    result = replay_requests / restore_successes
                except:
                    result = float("NaN")
                
        return result

    #endregion

    #region Static stuff used for analysis metrics

    visit_metrics = [
        "Total repetitions",
        "Total gameplay duration",
        "Total visit duration",
        "Total time not playing games",
        "Percent time not playing games",
        "Longest gap between playing games",
        "Total successful VNS trigger events [logged by ReStore]",
        "Total failed VNS trigger events [logged by ReStore]",
        "Total VNS trigger requests [logged by RePlay]",
        "Total successful VNS trigger events [logged by RePlay]",
        "Total failed VNS trigger events [logged by RePlay]",
        "Ratio of RePlay VNS requests to ReStore VNS successes"
    ]

    visit_metrics_units = {
        "Total repetitions" : "",
        "Total gameplay duration" : "minutes",
        "Total visit duration" : "minutes",
        "Total time not playing games" : "minutes",
        "Percent time not playing games" : "",
        "Longest gap between playing games" : "minutes",
        "Total successful VNS trigger events [logged by ReStore]" : "",
        "Total failed VNS trigger events [logged by ReStore]" : "",
        "Total VNS trigger requests [logged by RePlay]" : "",
        "Total successful VNS trigger events [logged by RePlay]" : "",
        "Total failed VNS trigger events [logged by RePlay]" : "",
        "Ratio of RePlay VNS requests to ReStore VNS successes" : ""        
    }

    @staticmethod
    def get_all_visit_metrics (prepend_visit_to_string = True):
        if (prepend_visit_to_string):
            result = [("(Visit) " + x) for x in RePlayVisit.visit_metrics]    
            return result
        else:
            return RePlayVisit.visit_metrics.copy()

    @staticmethod
    def convert_to_qualified_visit_metric_string (string_to_convert):
        return ("(Visit) " + string_to_convert)


    #endregion

