from mongoengine import *
import numpy
import math
from scipy import stats

from RePlayAnalysisCore3.Activities.BaseActivity import BaseActivity
from RePlayAnalysisCore3.RePlayExercises import RePlayExercises
from RePlayAnalysisCore3.DataFiles.RePlayDataFile import RePlayDataFile

from RePlayAnalysisCore3.ControllerData.RePlayControllerData import RePlayControllerData
from RePlayAnalysisCore3.GameData.RePlayGameData import RePlayGameData
from RePlayAnalysisCore3.GameData.RePlayGameDataBreakout import RePlayGameDataBreakout
from RePlayAnalysisCore3.GameData.RePlayGameDataFruitArchery import RePlayGameDataFruitArchery
from RePlayAnalysisCore3.GameData.RePlayGameDataFruitNinja import RePlayGameDataFruitNinja
from RePlayAnalysisCore3.GameData.RePlayGameDataRepetitionsMode import RePlayGameDataRepetitionsMode
from RePlayAnalysisCore3.GameData.RePlayGameDataSpaceRunner import RePlayGameDataSpaceRunner
from RePlayAnalysisCore3.GameData.RePlayGameDataTrafficRacer import RePlayGameDataTrafficRacer
from RePlayAnalysisCore3.GameData.RePlayGameDataTyperShark import RePlayGameDataTyperShark

from RePlayAnalysisCore3.VNS.RePlayVNSAlgorithm import RePlayVNSAlgorithm
from RePlayAnalysisCore3.VNS.RePlayVNSAlgorithm_TyperShark import RePlayVNSAlgorithm_TyperShark
from RePlayAnalysisCore3.VNS.RePlayVNSParameters import RePlayVNSParameters
from RePlayAnalysisCore3.RePlayStudy import RePlayStudy

from RePlayAnalysisCore3.PostHocVNSObject import PostHocVNSObject

class RePlayActivity(BaseActivity):
    controller_data = GenericReferenceField()
    game_data = GenericReferenceField()
    post_hoc_vns_algorithm_data = GenericReferenceField()

    def __init__(self, *args, **values):
        super().__init__(*args, **values)

    #region Methods to set controller and game data objects

    def SetControllerData(self, ctl_data):
        #This method sets the controller data object on the activity.
        self.controller_data = ctl_data
        self.is_dirty = True

    def SetGameData(self, g_data):
        #This method set the game data object on the activity.
        self.game_data = g_data
        self.is_dirty = True

    #endregion        

    #region Methods to handle changing the trim string

    def SetGameSignalTrimString (self, trim_points_string):
        #If trim does not exist in the tags, create it
        if not ("trim" in self.tags):
            self.tags["trim"] = ""
        
        #Set the trim if it has changed
        if (self.tags["trim"] != trim_points_string):
            self.tags["trim"] = trim_points_string
            self.is_dirty = True

    def GetGameSignalTrimString(self):
        if ("trim" in self.tags):
            return self.tags["trim"]
        else:
            return ""

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
            idx_of_final_parantheses = selected_variable_str.rfind(")")
            if (idx_of_final_parantheses >= 0):
                altered_variable_str = selected_variable_str[(idx_of_final_parantheses+1):].strip()

                #Now let's see which game variable we should analyze and return
                return float(self.__calculate_game_variable(altered_variable_str))
            else:
                return float("NaN")

    def __calculate_common_independent_variable(self, selected_variable_str):
        if (selected_variable_str == "Difficulty"):
            return self.GetDifficulty()
        elif (selected_variable_str == "Duration"):
            return self.duration
        elif (selected_variable_str == "Gain"):
            return self.GetGain()
        else:
            return float("NaN")    

    def __calculate_common_dependent_variable(self, selected_variable_str):
        #These variables are common to both RePlay and ReTrieve activities
        if (selected_variable_str == "VNS trigger events [logged by ReStore]"):
            return len(self.GetStimulationsFromReStoreDatalogs())

        #These variables are specific to RePlay activities
        if (selected_variable_str == "VNS trigger events [logged by RePlay]"):
            return len(self.GetRePlayStimulationRecords())
        elif (selected_variable_str == "VNS trigger requests [logged by RePlay]"):
            return len(self.GetRePlayStimulationRequests())    
        elif (selected_variable_str == "Total repetitions"):
            (total_reps, _) = self.GetRepetitionData()
            return total_reps
        elif (selected_variable_str == "Max real-world units"):
            (s, _, _, s_min_x, s_max_x, _) = self.GetGameSignal(True)
            s = s[s_min_x:s_max_x]
            return (numpy.nanmax([abs(n) for n in s]))
        elif (selected_variable_str == "Mean real-world units"):
            (s, _, _, s_min_x, s_max_x, _) = self.GetGameSignal(True)
            s = s[s_min_x:s_max_x]
            return (numpy.nanmean([abs(n) for n in s]))
        elif (selected_variable_str == "Mean peak real-world units"):
            (s, _, _, s_min_x, s_max_x, _) = self.GetGameSignal(True)
            s = s[s_min_x:s_max_x]
            (_, r_idx) = self.GetRepetitionData()
            r_idx = [(x - s_min_x) for x in r_idx]

            peaks = []
            for i in range(0, len(r_idx)):
                r_sig = []
                r_start = r_idx[i]
                if (i >= (len(r_idx) - 1)):
                    r_sig = s[r_start:]
                else:
                    r_end = r_idx[i+1]
                    r_sig = s[r_start:r_end]

                try:
                    r_peak = numpy.nanmax([abs(n) for n in r_sig])
                    peaks.append(r_peak)
                except:
                    pass
            
            return (numpy.nanmean(peaks))
        elif (selected_variable_str == "Median peak real-world units"):
            (s, _, _, s_min_x, s_max_x, _) = self.GetGameSignal(True)
            s = s[s_min_x:s_max_x]
            (_, r_idx) = self.GetRepetitionData()
            r_idx = [(x - s_min_x) for x in r_idx]

            peaks = []
            for i in range(0, len(r_idx)):
                r_sig = []
                r_start = r_idx[i]
                if (i >= (len(r_idx) - 1)):
                    r_sig = s[r_start:]
                else:
                    r_end = r_idx[i+1]
                    r_sig = s[r_start:r_end]

                try:
                    r_peak = numpy.nanmax([abs(n) for n in r_sig])
                    peaks.append(r_peak)
                except:
                    pass
            
            return (numpy.nanmedian(peaks))
        elif (selected_variable_str == "Interdecile range of signal in real-world units"):
            (s, _, _, s_min_x, s_max_x, _) = self.GetGameSignal(True)
            s = s[s_min_x:s_max_x]
            idr = numpy.percentile(s, 90) - numpy.percentile(s, 10)
            return (idr)

    def __calculate_game_variable (self, selected_variable_str):
        result = float("NaN")
        if (self.game_data is not None) and (isinstance(self.game_data, RePlayDataFile)):
            game_session = self.game_data.AccessData()
            if (game_session is not None):
                if (self.activity_name == "RepetitionsMode") and (isinstance(game_session, RePlayGameDataRepetitionsMode)):
                    if (selected_variable_str == "Mean peak-to-peak"):
                        temp_result = self.CalculatePeakToPeakAnalysis()
                        if (len(temp_result) > 0):
                            result = numpy.nanmean(temp_result)
                    elif (selected_variable_str == "Median peak-to-peak"):
                        temp_result = self.CalculatePeakToPeakAnalysis()
                        if (len(temp_result) > 0):
                            result = numpy.nanmedian(temp_result)                    

                elif (self.activity_name == "ReCheck") and (isinstance(game_session, RePlayGameDataRepetitionsMode)):
                    if (selected_variable_str == "Mean peak-to-peak"):
                        temp_result = self.CalculatePeakToPeakAnalysis()
                        if (len(temp_result) > 0):
                            result = numpy.nanmean(temp_result)
                    elif (selected_variable_str == "Median peak-to-peak"):
                        temp_result = self.CalculatePeakToPeakAnalysis()
                        if (len(temp_result) > 0):
                            result = numpy.nanmedian(temp_result)                            

                elif (self.activity_name == "Breakout") and (isinstance(game_session, RePlayGameDataBreakout)):
                    breakout_metrics = game_session.CalculateBreakoutGameMetrics()

                    if (selected_variable_str == "Number of balls lost"):
                        result = breakout_metrics[0]
                    elif (selected_variable_str == "Balls lost per minute"):
                        result = breakout_metrics[1]
                    elif (selected_variable_str == "Longest ball duration"):
                        result = breakout_metrics[2]
                    elif (selected_variable_str == "Average ball interval"):
                        result = breakout_metrics[3]
                    elif (selected_variable_str == "Time to first ball lost"):
                        result = breakout_metrics[4]        
                    elif (selected_variable_str == "Score"):
                        pass
                    elif (selected_variable_str == "Score - points per minute"):
                        pass
                                    
                elif (self.activity_name == "TrafficRacer") and (isinstance(game_session, RePlayGameDataTrafficRacer)):

                    if (selected_variable_str == "Percent time in target lane"):
                        result = game_session.CalculatePercentTimeInTargetLane()
                    elif (selected_variable_str == "Score per attempt - best"):
                        result = game_session.GetHighScore()
                    elif (selected_variable_str == "Score per attempt - average"):
                        result = game_session.GetAverageAttemptScore()
                    elif (selected_variable_str == "Score - points per minute"):
                        result = game_session.GetScorePerMinute()
                    elif (selected_variable_str == "Total crashes"):
                        result = len(game_session.crash_events)
                    elif (selected_variable_str == "Crashes per minute"):
                        result = (len(game_session.crash_events) / game_session.session_duration) * 60
                    elif (selected_variable_str == "Total coins"):
                        result = len(game_session.coin_capture_events)
                    elif (selected_variable_str == "Coins per minute"):
                        result = (len(game_session.coin_capture_events) / game_session.session_duration) * 60
                    elif (selected_variable_str == "Coins missed"):
                        total_coins_collected = len(game_session.coin_capture_guids)
                        total_coins = len(game_session.coin_guids)
                        result = total_coins - total_coins_collected
                    elif (selected_variable_str == "Coins missed per minute"):
                        total_coins_collected = len(game_session.coin_capture_guids)
                        total_coins = len(game_session.coin_guids)
                        result = ((total_coins - total_coins_collected) / game_session.session_duration) * 60
                    elif (selected_variable_str == "Percent coins collected"):
                        total_coins_collected = len(game_session.coin_capture_guids)
                        total_coins = len(game_session.coin_guids)
                        if (total_coins > 0):
                            result = (total_coins_collected / total_coins) * 100
                        else:
                            result = float("NaN")
                
                elif (self.activity_name == "SpaceRunner") and (isinstance(game_session, RePlayGameDataSpaceRunner)):
                    space_runner_metrics = game_session.CalculateSpaceRunnerMetrics()

                    if (selected_variable_str == "Number of attempts"):
                        result = float(space_runner_metrics[0])
                    elif (selected_variable_str == "Attempts per minute"):
                        try:
                            result = 60.0 * (float(space_runner_metrics[0]) / self.duration)
                        except:
                            result = float("NaN")
                    elif (selected_variable_str == "Mean score per attempt"):
                        result = float(numpy.nanmean(space_runner_metrics[1]))
                    elif (selected_variable_str == "Best attempt score"):
                        result = float(numpy.nanmax(space_runner_metrics[1]))
                    elif (selected_variable_str == "Mean duration per attempt"):
                        result = float(numpy.nanmean(space_runner_metrics[2]))
                    elif (selected_variable_str == "Best attempt duration"):
                        result = float(numpy.nanmax(space_runner_metrics[2]))
                    elif (selected_variable_str == "Mean coins per attempt"):
                        result = float(numpy.nanmean(space_runner_metrics[3]))
                    elif (selected_variable_str == "Best coins of attempt"):
                        result = float(numpy.nanmax(space_runner_metrics[3]))
                    elif (selected_variable_str == "Score - points per minute"):
                        result = float(game_session.GetScorePerMinute())

                elif (self.activity_name == "FruitArchery") and (isinstance(game_session, RePlayGameDataFruitArchery)):

                    if (selected_variable_str == "Fruit hit per minute"):
                        result = game_session.CalculateFruitHitPerMinute()
                    elif (selected_variable_str == "Score"):
                        result = game_session.CalculateTotalFruitHit()
                    elif (selected_variable_str == "Score - points per minute"):
                        result = game_session.CalculateFruitHitPerMinute()
                    elif (selected_variable_str == "Shots missed per minute"):
                        result = game_session.CalculateShotsMissedPerMinute()

                elif (self.activity_name == "FruitNinja") and (isinstance(game_session, RePlayGameDataFruitNinja)):

                    if (selected_variable_str == "Total fruit hit"):
                        result = game_session.CalculateTotalFruitHit()
                    elif (selected_variable_str == "Swipe accuracy"):
                        result = game_session.CalculateSwipeAccuracy()
                    elif (selected_variable_str == "Score"):
                        result = game_session.final_score
                    elif (selected_variable_str == "Score - points per minute"):
                        minutes = self.duration / 60.0
                        if (minutes > 0):
                            result = game_session.final_score / minutes
                        else:
                            result = 0
                    elif (selected_variable_str == "Fruit missed per minute"):
                        fruit_missed = game_session.CalculateTotalFruitMissed()
                        minutes = self.duration / 60.0
                        if (minutes > 0):
                            result = fruit_missed / minutes
                        else:
                            result = float("NaN")
                    elif (selected_variable_str == "Bombs hit per minute"):
                        bombs_hit = game_session.CalculateTotalBombsHit()
                        minutes = self.duration / 60.0
                        if (minutes > 0):
                            result = bombs_hit / minutes
                        else:
                            result= float("NaN")

                elif (self.activity_name == "TyperShark") and (isinstance(game_session, RePlayGameDataTyperShark)):
                    typershark_metrics = game_session.CalculateTyperSharkMetrics()

                    if (selected_variable_str == "Total sharks killed"):
                        result = float(typershark_metrics[0])
                    elif (selected_variable_str == "Percent sharks killed"):
                        result = float(typershark_metrics[1])
                    elif (selected_variable_str == "Total words completed"):
                        result = float(typershark_metrics[2])                   
                    elif (selected_variable_str == "Percent words completed"):
                        result = float(typershark_metrics[3])
                    elif (selected_variable_str == "Total keypresses"):
                        result = float(typershark_metrics[4])
                    elif (selected_variable_str == "Percent accurate keypresses"):
                        result = float(typershark_metrics[5])
                    elif (selected_variable_str == "Words per minute"):
                        result = float(typershark_metrics[6])
                    elif (selected_variable_str == "Keys per minute"):
                        result = float(typershark_metrics[7])
                    elif (selected_variable_str == "Correct keys per minute"):
                        result = float(typershark_metrics[8])
                    elif (selected_variable_str == "Mistakes per minute"):
                        result = float(typershark_metrics[9])    

                elif (self.activity_name == "ReTrieve"):
                    pass

        return float(result)

    #endregion

    #region Methods to get basic information about the activity

    def GetExerciseName(self):
        exercise_name = ""
        if (self.game_data is not None):
            exercise_name = self.game_data.exercise_id     
        return exercise_name

    def GetDifficulty(self):
        result = 1
        if (self.game_data is not None):
            game_data = self.game_data.AccessData()
            if (game_data is not None):
                result = game_data.GetDifficulty()

        return result

    def GetGain (self):
        result = 1
        if (self.game_data is not None):
            if (hasattr(self.game_data, "gain")):
                result = self.game_data.gain
        elif (self.controller_data is not None):
            if (hasattr(self.controller_data, "gain")):
                result = self.controller_data.gain

        return result

    def GetHandedness(self):
        if (self.game_data is not None) and (isinstance(self.game_data, RePlayDataFile)):
            game_data = self.game_data.AccessData()
            if (game_data is not None):
                return game_data.GetHandedness()
        return (False, False)

    def GetVNSParameters (self):
        #If the game data file has a "vns_algorithm_parameters" object, return that object
        if (self.game_data is not None) and (isinstance(self.game_data, RePlayDataFile)) and (hasattr(self.game_data, "vns_algorithm_parameters")):
            return self.game_data.vns_algorithm_parameters

        #Otherwise, if the controller data file has a "vns_algorithm_parameters" object, return that object
        if (self.controller_data is not None) and isinstance(self.controller_data, RePlayDataFile) and (hasattr(self.controller_data, "vns_algorithm_parameters")):
            return self.controller_data.vns_algorithm_parameters
        
        #Otherwise, just return null
        return None

    #endregion

    #region Methods for obtaining the game signal or VNS-algorithm signal from the session

    def GetGameSignal (self, use_real_world_units = True, apply_trim = True):
        #Get the game signal from the game data class
        if (self.game_data is not None) and (isinstance(self.game_data, RePlayDataFile)):
            game_data = self.game_data.AccessData()
            if (game_data is not None):
                (s, t, u, bt) = game_data.GetGameSignal(use_real_world_units)
                min_x = 0
                max_x = len(t)

                if ((apply_trim) and ("trim" in self.tags)):
                    (min_x, max_x) = self._get_trim_points(t, self.tags["trim"])
                
                if (not isinstance(s, list)):
                    s = []
                if (not isinstance(t, list)):
                    t = []

                return (s.copy(), t.copy(), u, min_x, max_x, bt)
        
        #In the case that the above doesn't work, return some empty arrays
        return ([], [], "", 0, 0, None)

    def GetSignalStartOffset(self):
        result = float("NaN")
        session_start_time = self.start_time

        if (self.game_data is not None) and (isinstance(self.game_data, RePlayDataFile)):
            game_data = self.game_data.AccessData()
            if (game_data is not None):
                alternate_start_time = game_data.signal_timenum[0]
                result = (alternate_start_time - session_start_time).total_seconds()

        return result

    def GetSignalStartTime(self):
        result = None

        if (self.game_data is not None) and (isinstance(self.game_data, RePlayDataFile)):
            game_data = self.game_data.AccessData()
            if (game_data is not None):
                result = game_data.signal_timenum[0]

        return result        

    def GetGameDataSavedVNSSignal(self, apply_trim = True):
        (game_signal, game_signal_timestamps, _, min_x, max_x, _) = self.GetGameSignal(False, apply_trim)

        vns_algorithm_is_frame_data_present = False
        vns_algorithm_timenum = []
        vns_algorithm_should_trigger = []
        vns_algorithm_signal_value = []
        vns_algorithm_positive_threshold = []
        vns_algorithm_negative_threshold = []
        vns_algorithm_timing_allows_trigger = []


        if (len(game_signal_timestamps) > 0):
            min_t = game_signal_timestamps[min_x]
            max_t = game_signal_timestamps[max_x - 1]

            session_start_time = self.start_time

            if (self.game_data is not None) and (isinstance(self.game_data, RePlayDataFile)):
                game_data = self.game_data.AccessData() #Returns a RePlayGameData object
                if (game_data is not None):
                    vns_algorithm_is_frame_data_present = game_data.vns_algorithm_is_frame_data_present
                    vns_algorithm_timenum = game_data.vns_algorithm_timenum.copy()       
                    vns_algorithm_should_trigger = game_data.vns_algorithm_should_trigger.copy()
                    vns_algorithm_signal_value = game_data.vns_algorithm_signal_value.copy()
                    vns_algorithm_positive_threshold = game_data.vns_algorithm_positive_threshold.copy()
                    vns_algorithm_negative_threshold = game_data.vns_algorithm_negative_threshold.copy()
                    vns_algorithm_timing_allows_trigger = game_data.vns_algorithm_timing_allows_trigger.copy()
                    alternate_start_time = game_data.signal_timenum[0]
                    session_start_time = alternate_start_time

            #Transform the vns algorithm time to have a reference frame using the start time of the activity
            vns_algorithm_transformed_time = []
            for i in range(0, len(vns_algorithm_timenum)):
                t = (vns_algorithm_timenum[i] - session_start_time).total_seconds()
                vns_algorithm_transformed_time.append(t)

            #Figure out which elements to keep from the arrays
            if (len(vns_algorithm_transformed_time) > 0):
                nearest_to_min_t = min(vns_algorithm_transformed_time, key=lambda x: abs(x - min_t))
                nearest_to_max_t = min(vns_algorithm_transformed_time, key=lambda x: abs(x - max_t))
                min_x = vns_algorithm_transformed_time.index(nearest_to_min_t)
                max_x = vns_algorithm_transformed_time.index(nearest_to_max_t)

                vns_algorithm_transformed_time = vns_algorithm_transformed_time[min_x:max_x]
                vns_algorithm_should_trigger = vns_algorithm_should_trigger[min_x:max_x]
                vns_algorithm_signal_value = vns_algorithm_signal_value[min_x:max_x]
                vns_algorithm_positive_threshold = vns_algorithm_positive_threshold[min_x:max_x]
                vns_algorithm_negative_threshold = vns_algorithm_negative_threshold[min_x:max_x]
                vns_algorithm_timing_allows_trigger = vns_algorithm_timing_allows_trigger[min_x:max_x]

        return (vns_algorithm_is_frame_data_present, 
                vns_algorithm_transformed_time,
                vns_algorithm_should_trigger,
                vns_algorithm_signal_value,
                vns_algorithm_positive_threshold,
                vns_algorithm_negative_threshold,
                vns_algorithm_timing_allows_trigger)

    def CalculateVNSSignal (self, custom_parameters = None):
        (game_signal, game_signal_timestamps, _, _, _, basis_time) = self.GetGameSignal(False, False)
        recentering_timestamps = self.GetRecenteringEvents()
        recentering_ts = []
        if (basis_time is not None):
            for t_idx in range(0, len(recentering_timestamps)):
                recentering_ts.append((recentering_timestamps[t_idx] - basis_time).total_seconds())

        vns_parameters = custom_parameters
        if (custom_parameters is None):
            vns_parameters = self.GetVNSParameters()

        vns_signal = []
        vns_positive_threshold = []
        vns_negative_threshold = []
        vns_timeout = []
        vns_trigger_ts = []

        if (vns_parameters is not None):
            if (self.activity_name == "TyperShark"):
                result = []
                for i in range(0, len(game_signal)):
                    if (game_signal[i] > 0):
                        result.append(game_signal_timestamps[i])
                vns_signal = RePlayVNSAlgorithm_TyperShark.ProcessSignal(result, vns_parameters)
                if (isinstance(vns_signal, numpy.ndarray)):
                    vns_signal = vns_signal.tolist()
            else:
                (vns_signal, vns_positive_threshold, vns_negative_threshold, vns_timeout, vns_trigger_ts) = RePlayVNSAlgorithm.ProcessSignal(
                    game_signal, game_signal_timestamps, vns_parameters, recentering_ts)
                
                if (isinstance(vns_signal, numpy.ndarray)):
                    vns_signal = vns_signal.tolist()
                if (isinstance(vns_positive_threshold, numpy.ndarray)):
                    vns_positive_threshold = vns_positive_threshold.tolist()
                if (isinstance(vns_negative_threshold, numpy.ndarray)):
                    vns_negative_threshold = vns_negative_threshold.tolist()
                if (isinstance(vns_timeout, numpy.ndarray)):
                    vns_timeout = vns_timeout.tolist()
                if (isinstance(vns_trigger_ts, numpy.ndarray)):
                    vns_trigger_ts = vns_trigger_ts.tolist()                    

        #If no VNS signal was adequately calculated, then let's create a NaN signal of equal length
        #with the game signal
        if (len(vns_signal) == 0):
            vns_signal = [float("NaN")] * len(game_signal_timestamps)
            vns_positive_threshold = [float("NaN")] * len(game_signal_timestamps)
            vns_negative_threshold = [float("NaN")] * len(game_signal_timestamps)
            vns_timeout = [float("NaN")] * len(game_signal_timestamps)
            vns_trigger_ts = []

        return (vns_signal, vns_positive_threshold, vns_negative_threshold, vns_timeout, vns_trigger_ts)        

    def GetVNSSignal (self, force_calculate_new = False):
        
        #Check to see if the post-hoc VNS data has previously been calculated
        has_been_calculated = False
        if (self.post_hoc_vns_algorithm_data is not None):
            has_been_calculated = self.post_hoc_vns_algorithm_data.post_hoc_vns_algorithm_data_has_been_calculated

        if (force_calculate_new or not has_been_calculated):
            #If the user wants to calculate the VNS signal anew, or if the VNS signal has not yet been pre-calculated and stored
            #in the database, then let's go ahead and calculate it...
            (vns_signal, vns_positive_threshold, vns_negative_threshold, vns_timeout, vns_trigger_ts) = self.CalculateVNSSignal()

            #Assign the calculated VNS signal values to the appropriate variables
            self.post_hoc_vns_algorithm_data = PostHocVNSObject()
            try:
                self.post_hoc_vns_algorithm_data.SetData(True, vns_signal, vns_positive_threshold, vns_negative_threshold, vns_timeout, vns_trigger_ts)
            except:
                #If an exception occurred above, then it means the data is too large to fit in a single MongoDB document. So, for the time being,
                #until we get this fixed, we will just return the results of the CalculateVNSSignal function, without saving the sub-document
                return (vns_signal, vns_positive_threshold, vns_negative_threshold, vns_timeout, vns_trigger_ts)

            #Save this activity
            self.save()

        #Return the VNS signal values to the caller
        return (

            self.post_hoc_vns_algorithm_data.post_hoc_vns_algorithm_signal_value,
            self.post_hoc_vns_algorithm_data.post_hoc_vns_algorithm_positive_threshold,
            self.post_hoc_vns_algorithm_data.post_hoc_vns_algorithm_negative_threshold,
            self.post_hoc_vns_algorithm_data.post_hoc_vns_algorithm_timing_allows_trigger,
            self.post_hoc_vns_algorithm_data.post_hoc_vns_algorithm_trigger_timestamps
        )
        
        #return self.CalculateVNSSignal()
        
    #endregion

    #region Methods for obtaining or modifying repetition data for the session

    def _assert_replay_activity_metadata_exists (self):
        did_change_occur = False

        if ("replay_activity_metadata" not in self.tags):
            self.tags["replay_activity_metadata"] = {}
            did_change_occur = True

        if ("rep_count" not in self.tags["replay_activity_metadata"]):
            self.tags["replay_activity_metadata"]["rep_count"] = 0
            did_change_occur = True
        
        if ("rep_list" not in self.tags["replay_activity_metadata"]):
            self.tags["replay_activity_metadata"]["rep_list"] = []
            did_change_occur = True

        if (did_change_occur):
            self.is_dirty = True

        return did_change_occur

    def GetRepetitionData(self):
        was_metadata_created = self._assert_replay_activity_metadata_exists()

        #If the rep list was just created, then we obviously haven't yet calculated
        #the repetitions themselves. Let's go ahead and calculate those now.
        if (was_metadata_created):
            self.CalculateRepetitionData()

        #Get the data to return to the caller
        rep_list = self.tags["replay_activity_metadata"]["rep_list"]
        rep_count = self.tags["replay_activity_metadata"]["rep_count"]
        
        #Return the repetition data to the caller
        return (rep_count, rep_list)             

    def CalculateRepetitionData(self):
        self._assert_replay_activity_metadata_exists()

        #Initialize variables that will be used to store the result
        rep_list = []
        rep_count = 0

        if (self.game_data is not None) and (isinstance(self.game_data, RePlayDataFile)):
            game_data = self.game_data.AccessData()
            if (game_data is not None):
                (rep_count, rep_list) = game_data.CalculateRepetitionData(self.GetExerciseName())

                #Save the calculated data into the metadata for this activity
                self.tags["replay_activity_metadata"]["rep_count"] = rep_count
                self.tags["replay_activity_metadata"]["rep_list"] = rep_list
                self.is_dirty = True
                self.save()

    def RecalculateRepetitionMarkersAsRepetitionsMode(self, apply_trim = True):
        self._assert_replay_activity_metadata_exists()

        #Make sure we meet all the correct criteria to call the function
        if(self.game_data is not None) and (isinstance(self.game_data, RePlayDataFile)):
            game_data = self.game_data.AccessData()
            if (game_data is not None) and (isinstance(game_data, RePlayGameDataRepetitionsMode)):
                #Get the trim parameter to pass into the repetition analysis function
                trim_parameter = None
                if((apply_trim) and ("trim" in self.tags)):
                    (_, t, _, _) = game_data.GetGameSignal(True)
                    min_x = 0
                    max_x = len(t)
                    (min_x, max_x) = self._get_trim_points(t, self.tags["trim"])
                    trim_parameter = {"start":min_x, "end":max_x}

                #Get the parameters that we will pass into the analysis function
                game_id = self.game_data.game_id
                exercise_id = self.game_data.exercise_id
                gain = self.game_data.gain
                standard_range = self.game_data.standard_range

                #Call the repetition analysis function
                rep_list = game_data.RecalculateRepetitionMarkersUsingGameSignal(game_id, exercise_id, gain, standard_range, trim_parameter)              
                rep_count = len(rep_list)

                #Save the calculated data into the metadata for this activity
                self.tags["replay_activity_metadata"]["rep_count"] = rep_count
                self.tags["replay_activity_metadata"]["rep_list"] = rep_list

                self.is_dirty = True
                self.save()

    def AddRepetitionMarker(self, xdata):
        self._assert_replay_activity_metadata_exists()

        #Make sure we meet all the correct criteria to call the function
        if(self.game_data is not None) and (isinstance(self.game_data, RePlayDataFile)):
            game_data = self.game_data.AccessData()
            if (game_data is not None):
                idx = game_data.GetCorrespondingSignalIndexFromSecondsElapsed(xdata)

                self.tags["replay_activity_metadata"]["rep_list"].append(idx)
                self.tags["replay_activity_metadata"]["rep_list"].sort()
                self.tags["replay_activity_metadata"]["rep_count"] = len(self.tags["replay_activity_metadata"]["rep_list"])

                self.is_dirty = True
                self.save()

    def RemoveNearestRepetitionMarker(self, xdata):
        self._assert_replay_activity_metadata_exists()

        #Make sure we meet all the correct criteria to call the function
        if(self.game_data is not None) and (isinstance(self.game_data, RePlayDataFile)):
            game_data = self.game_data.AccessData()
            if (game_data is not None):
                idx = game_data.GetCorrespondingSignalIndexFromSecondsElapsed(xdata)

                rep_list = self.tags["replay_activity_metadata"]["rep_list"]
                nearest_idx = min(rep_list, key=lambda d: abs(d - idx))
                self.tags["replay_activity_metadata"]["rep_list"].remove(nearest_idx)
                self.tags["replay_activity_metadata"]["rep_count"] = len(self.tags["replay_activity_metadata"]["rep_list"])

                self.is_dirty = True
                self.save()

    def ClearRepetitionMarkers(self):
        self._assert_replay_activity_metadata_exists()

        #Make sure we meet all the correct criteria to call the function
        if(self.game_data is not None) and (isinstance(self.game_data, RePlayDataFile)):
            game_data = self.game_data.AccessData()
            if (game_data is not None):
                
                self.tags["replay_activity_metadata"]["rep_list"].clear()
                self.tags["replay_activity_metadata"]["rep_count"] = 0

                self.is_dirty = True
                self.save()

    #endregion

    #region Methods for obtaining information about certain events that occurred during the session

    def GetRecenteringEvents (self):
        result = []
        if (self.game_data is not None):
            game_data = self.game_data.AccessData()
            if (isinstance(game_data, RePlayGameData)):
                result = game_data.rebaseline_time[:]

        return result

    def GetPauseEvents (self):
        pass

    def GetGameInactiveEvents (self):
        pass

    #endregion

    #region Overriden methods that return stimulations logged by RePlay/ReTrieve for this activity

    def GetStimulationRequestsForActivity (self):
        return self.GetRePlayStimulationRequests()

    def GetSuccessfulStimulationsForActivity (self):
        return self.GetRePlayStimulationRecords()

    def GetFailedStimulationsForActivity (self):
        return self.GetRePlayFailedStimulationRecords()

    #endregion

    #region Methods for obtaining information about VNS stimulations that occurred during the session

    def GetRePlayStimulationRequests (self):
        result = []
        try:
            is_typershark = False
            if (self.game_data is not None):
                game_data = self.game_data.AccessData()
                if (isinstance(game_data, RePlayGameDataTyperShark)):
                    is_typershark = True
                    for i in range(0, len(game_data.stimulation_occur)):
                        if (game_data.stimulation_occur[i] > 0):
                            result.append(game_data.signal_timenum[i])
            if (not is_typershark):
                if (self.controller_data is not None) and (isinstance(self.controller_data, RePlayDataFile)):

                    #There was a bug in recording RePlay stim requests for Breakout sessions before RePlay version 1.14 (version code 34).
                    #So we should throw out all stim requests prior to that version for Breakout sessions
                    if (self.controller_data.game_id == "Breakout") and (int(self.controller_data.replay_version_code) < 34):
                        #In this condition, do nothing
                        pass
                    else:
                        #If all the conditions are right, then go ahead and get the stim request times
                        controller_data = self.controller_data.AccessData()
                        if (controller_data is not None):
                            result = controller_data.stim_times
        except:
            pass

        return result

    def GetRePlayStimulationRecords (self):
        result = []
        try:
            is_typershark = False
            if (self.game_data is not None):
                game_data = self.game_data.AccessData()
                if (isinstance(game_data, RePlayGameDataTyperShark)):
                    is_typershark = True
                    if (hasattr(game_data, "stim_times_successful")):
                        result = game_data.stim_times_successful
            if (not is_typershark):
                if (self.controller_data is not None) and (isinstance(self.controller_data, RePlayDataFile)):
                    controller_data = self.controller_data.AccessData()
                    if (controller_data is not None):                    
                        result = controller_data.stim_times_successful
        except:
            pass

        return result
        
    def GetRePlayFailedStimulationRecords (self):
        result = []

        try:
            is_typershark = False
            if (self.game_data is not None):
                game_data = self.game_data.AccessData()
                if (isinstance(game_data, RePlayGameDataTyperShark)):
                    is_typershark = True
                    if (hasattr(game_data, "restore_messages")):
                        result = self._get_failed_stims_from_restore_messages(game_data.restore_messages)
            if (not is_typershark):
                if (self.controller_data is not None) and (isinstance(self.controller_data, RePlayDataFile)):
                    controller_data = self.controller_data.AccessData()
                    if (controller_data is not None):
                        result = self._get_failed_stims_from_restore_messages(controller_data.restore_messages)
        except:
            pass

        return result

    #endregion

    #region Private methods

    def _get_failed_stims_from_restore_messages(self, restore_messages):
        result = []

        for idx in range(0, len(restore_messages)):
            restore_msg = restore_messages[idx]
            if (("secondary" in restore_msg) and ("time" in restore_msg)):
                time = restore_msg["time"]
                secondary = restore_msg["secondary"]
                if ("COMMAND_STATUS" in secondary):
                    is_stim_failure = secondary["COMMAND_STATUS"]
                    if (is_stim_failure == "STIM_FAILURE"):
                        result.append(time)        

        return result

    def _get_trim_points (self, game_signal_timestamps, trim_string):
        #Determine how much of the signal to plot based on the "trim" the user has specified
        min_x = 0
        max_x = len(game_signal_timestamps)
        xlim_string = trim_string
        if (":" in xlim_string):
            string_parts = xlim_string.split(":")
            try:
                potential_min = float(string_parts[0])
                if(potential_min < 0):
                    potential_min = 0
                
                idx = next(x[0] for x in enumerate(game_signal_timestamps) if x[1] >= potential_min)
                min_x = idx
            except:
                pass

            try:
                potential_max = float(string_parts[1])
                if(potential_max > max(game_signal_timestamps)):
                    potential_max = max(game_signal_timestamps)
                
                idx = next(x[0] for x in enumerate(game_signal_timestamps) if x[1] >= potential_max)
                max_x = idx
            except:
                pass      

        return (min_x, max_x)      

    #endregion

    #region These methods are specific to performing the peak-to-peak analysis, i.e. discovering the distances betweens sets of peaks in repetitions

    #This method calculates the peak-to-peak distance between each set of repetitions during the session. It returns these distances
    #as a list of floating point numbers.
    def CalculatePeakToPeakAnalysis(self, use_real_world_units = True):
        p2p_result = []
        (game_signal_actual, game_signal_timestamps, game_signal_units_str, min_x, max_x, _) = self.GetGameSignal(use_real_world_units, True)
        (_, rep_markers) = self.GetRepetitionData()

        if (len(game_signal_timestamps) > 0) and (min_x >= 0) and (max_x <= len(game_signal_timestamps)):
            #Prepare some variables we will need for plotting stimulation markers
            min_t = game_signal_timestamps[min_x]
            max_t = game_signal_timestamps[max_x - 1]        

            rep_peaks = RePlayActivity.CalculateRepetitionPeaks(game_signal_timestamps, game_signal_actual, rep_markers)
            peaks_in_range = [x for x in rep_peaks if ((x[1] >= min_t) and (x[1] <= max_t))]
            p2p_result = RePlayActivity.CalculatePeakToPeakRanges(peaks_in_range)

        return p2p_result

    #Given a timestamp signal and a game signal, as well as a set of repetition markers, this method determines where the
    #"peak" value of each repetition is.
    @staticmethod
    def CalculateRepetitionPeaks(game_signal_ts, game_signal, rep_start_markers):
        result = []
        if (rep_start_markers is not None) and (len(rep_start_markers) > 0):
            current_rep_is_positive = True
            for rep_idx in range(0, len(rep_start_markers)):
                current_rep_start_marker = rep_start_markers[rep_idx]
                current_rep_end_marker = len(game_signal)
                if (rep_idx < (len(rep_start_markers)-1)):
                    current_rep_end_marker = rep_start_markers[rep_idx+1]
                current_rep_data = game_signal[current_rep_start_marker:current_rep_end_marker]
                if (len(current_rep_data) > 0):
                    current_rep_ts = game_signal_ts[current_rep_start_marker:current_rep_end_marker]
                    current_rep_result_idx = float("NaN")
                    current_rep_result_value = float("NaN")
                    current_rep_result_ts = float("NaN")
                    if (current_rep_is_positive):
                        current_rep_result_idx = numpy.argmax(current_rep_data)
                    else:
                        current_rep_result_idx = numpy.argmin(current_rep_data)
                    if not (math.isnan(current_rep_result_idx)):
                        current_rep_result_value = current_rep_data[current_rep_result_idx]
                        current_rep_result_ts = current_rep_ts[current_rep_result_idx]
                    
                    current_rep_result = (current_rep_is_positive, current_rep_result_ts, current_rep_result_value)
                    current_rep_is_positive = not current_rep_is_positive
                    result.append(current_rep_result)
        return result

    #Given a list of values that represent the peaks of each repetition, this method calculates the distance/range between each set of peaks.
    #It returns the result as a list of floating point numbers.
    @staticmethod
    def CalculatePeakToPeakRanges(repetition_peaks_result):
        peak_to_peak_data = []
        if (repetition_peaks_result is not None) and (len(repetition_peaks_result) >= 2):
            for p_idx in range(0, len(repetition_peaks_result)-1, 2):
                cur_peak = repetition_peaks_result[p_idx]
                next_peak = repetition_peaks_result[p_idx+1]
                p2p = abs(cur_peak[2] - next_peak[2])
                peak_to_peak_data.append(p2p)
        return peak_to_peak_data

    #endregion
