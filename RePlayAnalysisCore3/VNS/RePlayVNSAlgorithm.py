import math
import numpy as np
from datetime import datetime
from datetime import timedelta
from py_linq import Enumerable

from .RePlayVNSParameters import RePlayVNSParameters
from .RePlayVNSParameters import SmoothingOptions
from .RePlayVNSParameters import Stage1_Operations
from .RePlayVNSParameters import Stage2_Operations
from .RePlayVNSParameters import BufferExpirationPolicy

class RePlayVNSAlgorithm:

    @staticmethod
    def __diff (a):
        return RePlayVNSAlgorithm.__diff2(a, 0, len(a), False)

    @staticmethod
    def __diff2 (a, start_index, count, same_size = True):
        b = []
        for i in range(0, len(a)):
            if ((i < start_index) or (i > (start_index + count))):
                b.append(a[i])
            elif (i <= (start_index + count)):
                if ((i + 1) < len(a)):
                    b.append(a[i+1] - a[i])
                else:
                    if same_size:
                        b_to_add = 0
                        if (len(b) > 0):
                            b_to_add = b[-1]
                        b.append(b_to_add)
        return b

    @staticmethod
    def __gradient (signal):
        result = []
        if (signal is not None) and (len(signal) > 1):
            for i in range(0, len(signal)):
                if i == 0:
                    result.append(signal[i+1] - signal[i])
                elif i == (len(signal) - 1):
                    result.append(signal[i] - signal[i - 1])
                else:
                    result.append(0.5 * (signal[i + 1] - signal[i - 1]))
        else:
            result.append(0)
        return result

    @staticmethod
    def __box_smooth (signal, smoothing_factor = 3):
        result = []
        if (signal is not None) and (len(signal) > 0):
            if (smoothing_factor < 1):
                smoothing_factor = 1
            
            signal_prepend = Enumerable.repeat(signal[0], smoothing_factor).to_list()
            signal_append = Enumerable.repeat(signal[-1], smoothing_factor).to_list()

            
            ts = []
            ts.extend(signal_prepend)
            ts.extend(signal)
            ts.extend(signal_append)

            start_idx = len(signal_prepend)
            end_idx = len(signal_prepend) + len(signal)
            num_elements_each_side = int(math.floor(smoothing_factor / 2.0))
            for i in range(start_idx, end_idx):
                current_start_idx = i - num_elements_each_side
                current_end_idx = current_start_idx + smoothing_factor
                avg_of_elements = np.nanmean(ts[current_start_idx:current_end_idx])
                result.append(avg_of_elements)
        return result

    @staticmethod
    def __adjust_selectivity_based_upon_desired_isi(sample_ts, should_we_trigger, vns_parameters, vns_stim_times, most_recent_selectivity_adjustment_time, selectivity_adjustment_period, saturation_time):
        if (len(vns_stim_times) == 0):
            vns_stim_times.append(sample_ts)
        elif (should_we_trigger):
            vns_stim_times.append(sample_ts)
        
        if (sample_ts >= (most_recent_selectivity_adjustment_time + selectivity_adjustment_period)):
            current_isi = 0

            if (len(vns_stim_times) > 1):
                intervals = np.diff(vns_stim_times) * 1000
                current_isi = np.average(intervals)
            elif (len(vns_stim_times) == 1):
                current_isi = (sample_ts - vns_stim_times[0]) * 1000
                if (current_isi < (vns_parameters.Desired_ISI.total_seconds() * 1000)):
                    return

            #Calculate the difference between the current projected ISI and the desired ISI
            isi_diff = (vns_parameters.Desired_ISI.total_seconds() * 1000) - current_isi

            #Calculate the learning rate
            learning_rate = 0
            saturation_time_ms = saturation_time * 1000
            if (isi_diff < -saturation_time_ms):
                learning_rate = -1.0
            elif (isi_diff > saturation_time_ms):
                learning_rate = 1.0
            else:
                learning_rate = isi_diff / saturation_time_ms

            #Calculate the new selectivity
            new_selectivity = vns_parameters.Selectivity + (learning_rate / 100.0)

            #Assign the new selectivity to the parameters structure
            vns_parameters.Selectivity = new_selectivity

    @staticmethod
    def ProcessSignal (signal, signal_ts, vns_parameters, buffer_flush_ts):
        #How to use this function:
        #   You must pass in 3 parameters, as follows:
        #   1. signal = the "transformed game signal"
        #   2. signal_ts = an array that holds the timestamps for each sample in signal, in units of seconds
        #   3. vns_parameters = an object that holds the vns parameters used during this session, of type RePlayVNSParameters
        #   4. buffer_flush_ts = an array that holds timestamps for when the VNS buffer was flushed during the session, in units of seconds

        #Instantiate an empty array to be used as the result
        result_vns_signal = []
        result_vns_trigger_ts = []
        result_vns_timeout = []
        result_vns_positive_threshold = []
        result_vns_negative_threshold = []

        vns_most_recent_stimulation_time = 0
        vns_most_recent_should_we_trigger = False
        vns_current_positive_threshold = vns_parameters.NoiseFloor
        vns_current_negative_threshold = -vns_parameters.NoiseFloor

        #The following variables are exclusively for selectivity adjustment based on the desired ISI
        sel_adjust_vns_stim_times = []
        sel_adjust_most_recent_selectivity_adjustment_time = 0
        sel_adjust_selectivity_adjustment_period = 1.0
        sel_adjust_saturation_time = 10.0

        #Copy the buffer flush timestamps
        local_buffer_flush_ts = sorted(list(buffer_flush_ts))

        #Requirement to advance: the length of the signal array and the timestamps array must be equal
        if (len(signal) == len(signal_ts)) and isinstance(vns_parameters, RePlayVNSParameters):

            #Get the smoothing window size in units of seconds
            smoothing_window_seconds = vns_parameters.SmoothingWindow.total_seconds()

            #Create the small buffer
            small_buffer = []
            small_buffer_ts = []

            vns_lookback_values = []
            vns_lookback_values_ts = []

            #Iterate over each element of the signal
            for i in range(0, len(signal)):
                #Grab the sample
                sample = signal[i]
                sample_ts = signal_ts[i]

                #Check to see if we should flush the VNS algorithm buffers before proceeding with this sample
                if (len(local_buffer_flush_ts) > 0):
                    if (sample_ts >= local_buffer_flush_ts[0]):
                        #Pop the first element
                        current_flush_time = local_buffer_flush_ts[0]
                        local_buffer_flush_ts = local_buffer_flush_ts[1:]

                        #Flush the algorithm buffers
                        vns_most_recent_stimulation_time = current_flush_time
                        vns_most_recent_should_we_trigger = False
                        small_buffer.clear()
                        small_buffer_ts.clear()
                        vns_lookback_values.clear()
                        vns_lookback_values_ts.clear()

                should_we_trigger = False
                if (i == 0):
                    vns_most_recent_stimulation_time = sample_ts                

                #Determine whether we can allow triggering based on timing
                allow_trigger_based_on_timing = (sample_ts >= (vns_most_recent_stimulation_time + vns_parameters.Minimum_ISI.total_seconds()))  
                if (allow_trigger_based_on_timing):
                    result_vns_timeout.append(1)
                else:
                    result_vns_timeout.append(0)

                #Add the new sample to the small buffer
                small_buffer.append(sample)
                small_buffer_ts.append(sample_ts)

                #Determine the smoothing kernel size for this iteration of the loop
                kernel_size = 5
                if (len(small_buffer_ts) > 1):
                    isi_seconds = small_buffer_ts[1] - small_buffer_ts[0]
                    if (isi_seconds > 0):
                        kernel_seconds = vns_parameters.SmoothingKernelSize.total_seconds()
                        kernel_size = int(round(kernel_seconds / isi_seconds))
                        if (kernel_size < 3):
                            kernel_size = 3

                #Remove old values from the small buffer
                first_idx = -1
                for j in range(0, len(small_buffer_ts)):
                    if (small_buffer_ts[j] >= (sample_ts - smoothing_window_seconds)):
                        first_idx = j
                        small_buffer = small_buffer[first_idx:]
                        small_buffer_ts = small_buffer_ts[first_idx:]
                        break
                
                #Stage 1 Smoothing
                s1_buffer = small_buffer
                if (vns_parameters.Stage1_Smoothing == SmoothingOptions.AveragingFilter):
                    s1_buffer = RePlayVNSAlgorithm.__box_smooth(s1_buffer, kernel_size)

                #Stage 1 Operation
                s1_result = s1_buffer
                if (vns_parameters.Stage1_Operation == Stage1_Operations.SubtractMean):
                    m = np.nanmean(s1_buffer)
                    s1_result = Enumerable(s1_buffer).select(lambda x: x - m).to_list()
                elif (vns_parameters.Stage1_Operation == Stage1_Operations.Derivative):
                    s1_result = RePlayVNSAlgorithm.__diff(s1_buffer)
                elif (vns_parameters.Stage1_Operation == Stage1_Operations.Gradient):
                    s1_result = RePlayVNSAlgorithm.__gradient(s1_buffer)
                
                #Stage 2 Smoothing
                s2_buffer = s1_result
                if (vns_parameters.Stage2_Smoothing == SmoothingOptions.AveragingFilter):
                    s2_buffer = RePlayVNSAlgorithm.__box_smooth(s2_buffer, kernel_size)

                #Stage 2 Operation
                s2_result = 0
                if (len(s2_buffer) > 0):
                    s2_result = s2_buffer[-1]

                if (vns_parameters.Stage2_Operation == Stage2_Operations.RMS):
                    if len(s2_buffer) > 0:
                        s2_result = np.sqrt(
                            np.nansum(Enumerable(s2_buffer).select(lambda x: pow(x, 2)).to_list()) / len(s2_buffer)
                        )
                    else:
                        s2_result = 0
                elif (vns_parameters.Stage2_Operation == Stage2_Operations.SignedRMS):
                    if len(s2_buffer) > 0:
                        s2_result = np.sqrt(
                            np.nansum(Enumerable(s2_buffer).select(lambda x: pow(x, 2)).to_list()) / len(s2_buffer)
                        )
                        s2_result = s2_result * np.sign(np.nanmean(s2_buffer))
                    else:
                        s2_result = 0
                elif (vns_parameters.Stage2_Operation == Stage2_Operations.Mean):
                    if len(s2_buffer) > 0:
                        s2_result = np.nanmean(s2_buffer)
                    else:
                        s2_result = 0
                elif (vns_parameters.Stage2_Operation == Stage2_Operations.Sum):
                    if len(s2_buffer) > 0:
                        s2_result = np.nansum(s2_buffer)
                    else:
                        s2_result = 0

                #The stage 2 result is placed into the result of this function
                result_vns_signal.append(s2_result)

                #Check to see if the latest value is above the noise floor
                if (abs(s2_result) >= vns_parameters.NoiseFloor):
                    vns_lookback_values.append(s2_result)
                    vns_lookback_values_ts.append(sample_ts)

                    #Remove old values from the vns lookback buffer
                    lookback_window_seconds = vns_parameters.LookbackWindow.total_seconds()
                    if (vns_parameters.LookbackWindowExpirationPolicy == BufferExpirationPolicy.TimeLimit):
                        first_idx = -1
                        for j in range(0, len(vns_lookback_values_ts)):
                            if (vns_lookback_values_ts[j] >= (sample_ts - lookback_window_seconds)):
                                first_idx = j
                                vns_lookback_values = vns_lookback_values[first_idx:]
                                vns_lookback_values_ts = vns_lookback_values_ts[first_idx:]
                                break
                    elif (vns_parameters.LookbackWindowExpirationPolicy == BufferExpirationPolicy.TimeCapacity):
                        if (len(vns_lookback_values) >= 6):
                            latest_timestamps = vns_lookback_values_ts[-6:]
                            diff_latest_timestamps = np.diff(latest_timestamps) * 1000 #Multiply by 1000 to get in units of ms
                            median_interval_ms = np.median(diff_latest_timestamps)

                            #Now that we have a measure of the median ISI, calculate how many samples our buffer should be
                            buffer_size_limit = round((lookback_window_seconds * 1000) / median_interval_ms)

                            #Now that we know our buffer size, limit the capacity of the buffer to that size
                            vns_lookback_values = vns_lookback_values[-buffer_size_limit:]
                            vns_lookback_values_ts = vns_lookback_values_ts[-buffer_size_limit:]
                    else:
                        vns_lookback_values = vns_lookback_values[-vns_parameters.LookbackWindowCapacity:]
                        vns_lookback_values_ts = vns_lookback_values_ts[-vns_parameters.LookbackWindowCapacity:]

                    #The numpy percentile function expects a number between 0 and 100, rather than 0 to 1
                    vns_parameters_selectivity = vns_parameters.Selectivity * 100
                    values_above_pos_noise_floor = [x for x in vns_lookback_values if x >= vns_parameters.NoiseFloor]
                    values_below_neg_noise_floor = [x for x in vns_lookback_values if x < -vns_parameters.NoiseFloor]

                    if (len(values_above_pos_noise_floor) > 0):
                        vns_current_positive_threshold = max(vns_parameters.NoiseFloor, np.percentile(values_above_pos_noise_floor, vns_parameters_selectivity))
                    
                    if (len(values_below_neg_noise_floor) > 0):
                        vns_current_negative_threshold = min(-vns_parameters.NoiseFloor, np.percentile(values_below_neg_noise_floor, 100 - vns_parameters_selectivity))

                    #Now determine whether to issue a stimulation trigger
                    trigger_based_on_value = (
                        ((s2_result >= vns_current_positive_threshold) and (vns_parameters.TriggerOnPositive)) or
                        ((s2_result <= vns_current_negative_threshold) and (vns_parameters.TriggerOnNegative))
                    )
                    if (trigger_based_on_value and allow_trigger_based_on_timing):
                        vns_most_recent_stimulation_time = sample_ts
                        should_we_trigger = True
                        result_vns_trigger_ts.append(sample_ts)
                    
                    vns_most_recent_should_we_trigger = should_we_trigger

                    if (vns_parameters.SelectivityControlledByDesiredISI):
                        RePlayVNSAlgorithm.__adjust_selectivity_based_upon_desired_isi(
                            sample_ts,
                            should_we_trigger,
                            vns_parameters,
                            sel_adjust_vns_stim_times,
                            sel_adjust_most_recent_selectivity_adjustment_time,
                            sel_adjust_selectivity_adjustment_period,
                            sel_adjust_saturation_time)

                result_vns_positive_threshold.append(vns_current_positive_threshold)
                result_vns_negative_threshold.append(vns_current_negative_threshold)
        
        return (result_vns_signal, result_vns_positive_threshold, result_vns_negative_threshold, result_vns_timeout, result_vns_trigger_ts)
            
