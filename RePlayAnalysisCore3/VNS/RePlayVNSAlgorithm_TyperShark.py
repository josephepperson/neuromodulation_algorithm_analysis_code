import numpy as np
from datetime import datetime
from datetime import timedelta
from py_linq import Enumerable

from .RePlayVNSParameters import RePlayVNSParameters
from .RePlayVNSParameters import SmoothingOptions
from .RePlayVNSParameters import Stage1_Operations
from .RePlayVNSParameters import Stage2_Operations
from .RePlayVNSParameters import BufferExpirationPolicy

class RePlayVNSAlgorithm_TyperShark:

    @staticmethod
    def ProcessSignal (signal_ts, vns_parameters):
        #How to use this function:
        #   You must pass in 2 parameters, as follows:
        #   1. signal_ts = an array that holds the timestamps for keypress, in units of seconds
        #   2. vns_parameters = an object that holds the vns parameters used during this session, of type RePlayVNSParameters

        #Instantiate an empty array to be used as the result
        result = []

        vns_parameters_selectivity = vns_parameters.Selectivity * 100
        vns_most_recent_stimulation_time = signal_ts[0]
        vns_most_recent_should_we_trigger = False

        vns_lookback_values = []
        result_vns_timeout = []
        vns_should_we_trigger = []
        vns_stimulation_times = []     
        vns_positive_thresholds = []   

        if (isinstance(vns_parameters, RePlayVNSParameters)):
            #Calculate the interval between each keypres
            keypress_intervals = abs(np.diff(signal_ts))

            #Now take the inverse of the interval
            for i in range(0, len(keypress_intervals)):
                if keypress_intervals[i] > 0:
                    keypress_intervals[i] = 1.0 / keypress_intervals[i]

            #Assign to the result
            result = keypress_intervals

            #Iterate through the signal
            for i in range(0, len(result)):
                vns_lookback_values.append(result[i])
                num_to_remove = len(vns_lookback_values) - vns_parameters.TyperSharkLookbackSize
                if (num_to_remove > 0):
                    vns_lookback_values = vns_lookback_values[num_to_remove:]

                #Determine whether we can allow triggering based on timing
                allow_trigger_based_on_timing = (signal_ts[i] >= (vns_most_recent_stimulation_time + vns_parameters.Minimum_ISI.total_seconds()))  
                if (allow_trigger_based_on_timing):
                    result_vns_timeout.append(1)
                else:
                    result_vns_timeout.append(0)                    

                vns_current_positive_threshold = np.percentile(vns_lookback_values, vns_parameters_selectivity)
                vns_positive_thresholds.append(vns_current_positive_threshold)
                if (result[i] >= vns_current_positive_threshold) and (allow_trigger_based_on_timing):
                    vns_most_recent_stimulation_time = signal_ts[i]
                    vns_most_recent_should_we_trigger = True
                    vns_stimulation_times.append(vns_most_recent_stimulation_time)
                vns_should_we_trigger.append(vns_most_recent_should_we_trigger)

        return (result, vns_positive_thresholds, [], result_vns_timeout, vns_stimulation_times)
            
