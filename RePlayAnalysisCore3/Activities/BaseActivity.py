from mongoengine import *
import math
from datetime import timedelta
from datetime import datetime, time
from py_linq import Enumerable

from RePlayAnalysisCore3.Documents.DatabaseAnalysisUnitDocument import DatabaseAnalysisUnitDocument
from RePlayAnalysisCore3.RePlayStudy import RePlayStudy
from RePlayAnalysisCore3.ReStoreStimulationCollection import *

class BaseActivity(DatabaseAnalysisUnitDocument):
    
    meta = {
        'allow_inheritance': True, 
        'collection':'Activities',
        'strict':False
    }

    uid = StringField(max_length=200)
    activity_name = StringField(max_length=200)
    start_time = DateTimeField()
    duration = FloatField()

    def __init__(self, *args, **values):
        super().__init__(*args, **values)

    #region Methods to handle what happens when this activity is included/excluded

    def _handle_exclusion_toggled(self):
        #Update the master dataframe
        RePlayStudy.GetStudy().UpdateActivityInAggregatedMetrics(self)        

    #endregion

    #region Methods to get basic information about this activity

    def GetGameName(self):
        return self.activity_name        

    def GetHandedness(self):
        return (False, False)        

    def GetHandName(self):
        (is_hand_known, is_left_hand) = self.GetHandedness()
        if (is_hand_known):
            if (is_left_hand):
                return "Left"
            else:
                return "Right"
        else:
            return "Unknown"

    def GetExerciseName(self):
        return ""

    def GetDifficulty(self):
        return 1

    def GetNormalizedDifficulty(self):
        return float("NaN")

    def GetGain(self):
        return float("NaN")    

    def GetGameSignal (self, use_real_world_units = True, apply_trim = True):        
        return ([], [], "", 0, 0, None)

    #endregion

    #region Methods that handle usage of the game signal and calculating repetitions

    def GetRepetitionData(self):
        return (0, [])

    def CalculateRepetitionData(self):        
        pass

    #endregion

    #region Methods that return ReStore stimulation information for this activity

    def GetStimulationsFromReStoreDatalogs(self):
        #ReStoreStimulation.objects(Q(uid = ))
        return self.__get_filtered_stimulation_data(True)
    
    def GetStimulationsPerDayFromReStoreDatalogs(self):
        #ReStoreStimulation.objects(Q(uid = ))
        return self.__get_filtered_perday_stimulation_data(True)
    
    def GetShiftedStimulationsFromReStoreDatalogs(self, shift):
        #ReStoreStimulation.objects(Q(uid = ))
        return self.__get_filtered_shifted_stimulation_data(True, shift)

    def GetFailedStimulationsFromReStoreDatalogs (self):
        return self.__get_filtered_stimulation_data(False)

    def __get_filtered_stimulation_data(self, is_successful_stims):
        stims_during_this_activity = []
        if (not math.isnan(self.duration)):
            current_activity_starttime = self.start_time
            current_activity_endtime = current_activity_starttime + timedelta(seconds = self.duration)
            current_visit = self.parent
            if (current_visit is not None):
                current_participant = current_visit.parent
                if (current_participant is not None):
                    all_stims_for_this_participant = ReStoreStimulation.objects(Q(uid = current_participant.uid) & Q(is_successful = is_successful_stims))
                    stims_during_this_activity = [x.stimulation_datetime for x in all_stims_for_this_participant if ((x.stimulation_datetime >= current_activity_starttime) and (x.stimulation_datetime <= current_activity_endtime))]
        
        return sorted(stims_during_this_activity)
    
    def __get_filtered_perday_stimulation_data(self, is_successful_stims):
        stims_during_this_activity = []
        if (not math.isnan(self.duration)):
            current_activity_starttime = self.start_time
            day_start = datetime.combine(current_activity_starttime, time.min)
            day_end = datetime.combine(current_activity_starttime, time.max)
            current_visit = self.parent
            if (current_visit is not None):
                current_participant = current_visit.parent
                if (current_participant is not None):
                    all_stims_for_this_participant = ReStoreStimulation.objects(Q(uid = current_participant.uid) & Q(is_successful = is_successful_stims))
                    stims_during_this_day = [x.stimulation_datetime for x in all_stims_for_this_participant if ((x.stimulation_datetime >= day_start) and (x.stimulation_datetime <= day_end))]
        
        return sorted(stims_during_this_day)
    
    def __get_filtered_shifted_stimulation_data(self, is_successful_stims, shift):
        stims_during_this_activity = []
        if (not math.isnan(self.duration)):
            current_activity_starttime = self.start_time
            current_activity_endtime = current_activity_starttime + timedelta(seconds = self.duration)
            current_visit = self.parent
            if (current_visit is not None):
                current_participant = current_visit.parent
                if (current_participant is not None):
                    all_stims_for_this_participant = ReStoreStimulation.objects(Q(uid = current_participant.uid) & Q(is_successful = is_successful_stims))
                    stims_during_this_activity = [x.stimulation_datetime for x in all_stims_for_this_participant if (((x.stimulation_datetime - timedelta(seconds=shift)) >= current_activity_starttime) and ((x.stimulation_datetime - timedelta(seconds=shift)) <= current_activity_endtime))]
        
        return sorted(stims_during_this_activity)

    #endregion        

    #region Methods that return stimulations logged by RePlay/ReTrieve for this activity

    def GetStimulationRequestsForActivity (self):
        #This method should be overriden and implemented by child classes
        return []

    def GetSuccessfulStimulationsForActivity (self):
        #This method should be overriden and implemented by child classes
        return []

    def GetFailedStimulationsForActivity (self):
        #This method should be overriden and implemented by child classes
        return []

    #endregion