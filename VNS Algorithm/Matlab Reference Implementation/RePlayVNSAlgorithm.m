classdef RePlayVNSAlgorithm
    %RePlayVNSAlgorithm - Matlab reference implementation
    %   This is the reference implementation of the RePlay VNS
    %   algorithm in Matlab.

    methods(Static)

        function b = txbdc_diff (a)
            b = RePlayVNSAlgorithm.txbdc_diff2(a, 1, length(a), true);
        end

        function b = txbdc_diff2 (a, start_index, count, same_size)
            if (nargin < 4)
                same_size = true;
            end

            calculated_size = length(a);
            if (~same_size)
                calculated_size = calculated_size - 1;
            end

            b = nan(1, calculated_size);
            for i = 1:length(a)
                if ((i < start_index) || (i > (start_index + count)))
                    b(i) = a(i);
                elseif (i <= (start_index + count))
                    if ((i + 1) <= length(a))
                        b(i) = a(i+1) - a(i);
                    else
                        if same_size
                            b_to_add = 0;
                            if (~isempty(b))
                                last_non_nan_idx = find(~isnan(b), 1, 'last');
                                if (~isempty(last_non_nan_idx))
                                    b_to_add = b(last_non_nan_idx(1));
                                end
                            end
                            b(i) = b_to_add;
                        end
                    end
                end
            end
        end

        function result = txbdc_gradient(signal)
            result = nan(1, length(signal));
            if (length(signal) > 1)
                for i = 1:length(signal)
                    new_value = 0;
                    if i == 1
                        new_value = signal(i+1) - signal(i);
                    elseif i == length(signal)
                        new_value = signal(i) - signal(i - 1);
                    else
                        new_value = 0.5 * (signal(i+1) - signal(i-1));
                    end
                    result(i) = new_value;
                end
            else
                result = 0;
            end
        end

        function result = txbdc_box_smooth (signal, smoothing_factor)
            if (nargin < 2)
                smoothing_factor = 3;
            end

            result = [];
            if (~isempty(signal))
                if (smoothing_factor < 1)
                    smoothing_factor = 1;
                end

                signal_prepend = repelem(signal(1), 1, smoothing_factor);
                signal_append = repelem(signal(end), 1, smoothing_factor);

                ts = [signal_prepend signal signal_append];
                start_idx = length(signal_prepend) + 1;
                end_idx = length(signal_prepend) + length(signal);
                num_elements_each_side = floor(smoothing_factor / 2.0);
                for i = start_idx:end_idx
                    current_start_idx = i - num_elements_each_side;
                    current_end_idx = current_start_idx + smoothing_factor - 1;
                    avg_of_elements = nanmean(ts(current_start_idx:current_end_idx));
                    result = [result avg_of_elements];
                end
            end
        end

        function [vns_stim_times, vns_parameters] = adjust_selectivity_based_upon_desired_isi(sample_ts, should_we_trigger, vns_parameters, vns_stim_times, most_recent_selectivity_adjustment_time, selectivity_adjustment_period, saturation_time)
            arguments
                sample_ts
                should_we_trigger
                vns_parameters RePlayVNSParameters
                vns_stim_times
                most_recent_selectivity_adjustment_time
                selectivity_adjustment_period
                saturation_time
            end

            if (isempty(vns_stim_times))
                vns_stim_times = [vns_stim_times sample_ts];
            elseif (should_we_trigger)
                vns_stim_times = [vns_stim_times sample_ts];
            end

            if (sample_ts >= (most_recent_selectivity_adjustment_time + selectivity_adjustment_period))
                current_isi = 0;

                if (length(vns_stim_times) > 1)
                    intervals = diff(vns_stim_times) * 1000;
                    current_isi = mean(intervals);
                elseif (length(vns_stim_times) == 1)
                    current_isi = (sample_ts - vns_stim_times(1)) * 1000;
                    if (current_isi < (seconds(vns_parameters.Desired_ISI) * 1000))
                        return
                    end
                end

                %Calculate the difference between the current projected ISI
                %and the desired ISI
                isi_diff = (seconds(vns_parameters.Desired_ISI) * 1000) - current_isi;

                %Calculate the learning rate
                learning_rate = 0;
                saturation_time_ms = saturation_time * 1000;
                if (isi_diff < -saturation_time_ms)
                    learning_rate = -1.0;
                elseif (isi_diff > saturation_time_ms)
                    learning_rate = 1.0;
                else
                    learning_rate = isi_diff / saturation_time_ms;
                end

                %Calcualte the new selectivity
                new_selectivity = vns_parameters.Selectivity + (learning_rate / 100.0);

                %Assign the new selectivity to the parameters structure
                vns_parameters.Selectivity = new_selectivity;

            end

        end

        function [result_vns_signal, result_vns_positive_threshold, result_vns_negative_threshold, result_vns_timeout, result_vns_trigger_ts] = ProcessSignal (signal, signal_ts, vns_parameters, buffer_flush_ts)
            arguments
                signal
                signal_ts
                vns_parameters RePlayVNSParameters
                buffer_flush_ts
            end

            % Instantiate an empty array to be used as the result
            result_vns_signal = [];
            result_vns_trigger_ts = [];
            result_vns_timeout = [];
            result_vns_positive_threshold = [];
            result_vns_negative_threshold = [];

            vns_most_recent_stimulation_time = 0;
            vns_most_recent_should_we_trigger = false;
            vns_current_positive_threshold = vns_parameters.NoiseFloor;
            vns_current_negative_threshold = -vns_parameters.NoiseFloor;            

            % The following variables are exclusively for selectivity adjustment based on the desired ISI
            sel_adjust_vns_stim_times = [];
            sel_adjust_most_recent_selectivity_adjustment_time = 0;
            sel_adjust_selectivity_adjustment_period = 1.0;
            sel_adjust_saturation_time = 10.0;
            
            % Copy the buffer flush timestamps in sorted order
            local_buffer_flush_ts = sort(buffer_flush_ts);

            % Requirement to advance: the length of the signal array and
            % the timestamps array must be equal
            if (length(signal) == length(signal_ts))

                % Get the smoothing window size in units of seconds
                smoothing_window_seconds = seconds(vns_parameters.SmoothingWindow);

                % Create the small buffer
                small_buffer = [];
                small_buffer_ts = [];

                vns_lookback_values = [];
                vns_lookback_values_ts = [];

                % Iterate over each element of the signal
                for i = 1:length(signal)
                    %Grab the sample
                    sample = signal(i);
                    sample_ts = signal_ts(i);

                    %Check to see if we should flush the VNS algorithm
                    %buffers before proceeding with this sample
                    if (~isempty(local_buffer_flush_ts))
                        if (sample_ts >= local_buffer_flush_ts(1))
                            %Pop the first element
                            current_flush_time = local_buffer_flush_ts(1);
                            local_buffer_flush_ts(1) = [];

                            %Flush the algorithm buffers
                            vns_most_recent_stimulation_time = current_flush_time;
                            vns_most_recent_should_we_trigger = false;
                            small_buffer = [];
                            small_buffer_ts = [];
                            vns_lookback_values = [];
                            vns_lookback_values_ts = [];
                        end
                    end

                    should_we_trigger = false;
                    if (i == 1)
                        vns_most_recent_stimulation_time = sample_ts;
                    end

                    %Determine whether we can allow triggering based on
                    %timing
                    allow_trigger_based_on_timing = (sample_ts >= (vns_most_recent_stimulation_time + seconds(vns_parameters.Minimum_ISI)));
                    if (allow_trigger_based_on_timing)
                        result_vns_timeout = [result_vns_timeout 1];
                    else
                        result_vns_timeout = [result_vns_timeout 0];
                    end

                    %Add the new sample to the small buffer
                    small_buffer = [small_buffer sample];
                    small_buffer_ts = [small_buffer_ts sample_ts];

                    %Determine the smoothing kernel size for this iteration
                    %of the loop
                    kernel_size = 5;
                    if (length(small_buffer_ts) > 1)
                        isi_seconds = small_buffer_ts(2) - small_buffer_ts(1);
                        if (isi_seconds > 0)
                            kernel_seconds = seconds(vns_parameters.SmoothingKernelSize);
                            kernel_size = round(kernel_seconds / isi_seconds);
                            if (kernel_size < 3)
                                kernel_size = 3;
                            end
                        end
                    end

                    %Remove old values from the small buffer
                    first_idx = 0;
                    for j = 1:length(small_buffer_ts)
                        if (small_buffer_ts(j) >= (sample_ts - smoothing_window_seconds))
                            first_idx = j;
                            small_buffer = small_buffer(first_idx:end);
                            small_buffer_ts = small_buffer_ts(first_idx:end);
                            break;
                        end
                    end

                    %Stage 1 Smoothing
                    s1_buffer = small_buffer;
                    if (vns_parameters.Stage1_Smoothing == SmoothingOptions.AveragingFilter)
                        s1_buffer = RePlayVNSAlgorithm.txbdc_box_smooth(s1_buffer, kernel_size);
                    end

                    %Stage 1 Operation
                    s1_result = s1_buffer;
                    if (vns_parameters.Stage1_Operation == Stage1_Operations.SubtractMean)
                        m = nanmean(s1_buffer);
                        s1_result = s1_buffer - m;
                    elseif (vns_parameters.Stage1_Operation == Stage1_Operations.Derivative)
                        s1_result = RePlayVNSAlgorithm.txbdc_diff(s1_buffer);
                    elseif (vns_parameters.Stage1_Operation == Stage1_Operations.Gradient)
                        s1_result = RePlayVNSAlgorithm.txbdc_gradient(s1_buffer);
                    end

                    %Stage 2 Smoothing
                    s2_buffer = s1_result;
                    if (vns_parameters.Stage2_Smoothing == SmoothingOptions.AveragingFilter)
                        s2_buffer = RePlayVNSAlgorithm.txbdc_box_smooth(s2_buffer, kernel_size);
                    end

                    %Stage 2 Operation
                    s2_result = 0;
                    if (~isempty(s2_buffer))
                        s2_result = s2_buffer(end);
                    end

                    if (vns_parameters.Stage2_Operation == Stage2_Operations.RMS)
                        if (~isempty(s2_buffer))
                            s2_result = sqrt(nansum(s2_buffer .^ 2) / length(s2_buffer));
                        else
                            s2_result = 0;
                        end
                    elseif (vns_parameters.Stage2_Operation == Stage2_Operations.SignedRMS)
                        if (~isempty(s2_buffer))
                            s2_result = sqrt(nansum(s2_buffer .^ 2) / length(s2_buffer));
                            s2_result = s2_result * sign(nanmean(s2_buffer));
                        else
                            s2_result = 0;
                        end
                    elseif (vns_parameters.Stage2_Operation == Stage2_Operations.Mean)
                        if (~isempty(s2_buffer))
                            s2_result = nanmean(s2_buffer);
                        else
                            s2_result = 0;
                        end
                    elseif (vns_parameters.Stage2_Operation == Stage2_Operations.Sum)
                        if (~isempty(s2_buffer))
                            s2_result = nansum(s2_buffer);
                        else
                            s2_result = 0;
                        end
                    end

                    %The stage 2 result is placed into the result of this
                    %function
                    result_vns_signal = [result_vns_signal s2_result];

                    %Check to see if the latest value is above the noise
                    %floor
                    if (abs(s2_result) >= vns_parameters.NoiseFloor)
                        vns_lookback_values = [vns_lookback_values s2_result];
                        vns_lookback_values_ts = [vns_lookback_values_ts sample_ts];

                        %Remove old values from the vns lookback buffer
                        lookback_window_seconds = seconds(vns_parameters.LookbackWindow);
                        if (vns_parameters.LookbackWindowExpirationPolicy == BufferExpirationPolicy.TimeLimit)
                            first_idx = 0;
                            for j = 1:length(vns_lookback_values_ts)
                                if (vns_lookback_values_ts(j) >= (sample_ts - lookback_window_seconds))
                                    first_idx = j;
                                    vns_lookback_values = vns_lookback_values(first_idx:end);
                                    vns_lookback_values_ts = vns_lookback_values_ts(first_idx:end);
                                    break;
                                end
                            end
                        elseif (vns_parameters.LookbackWindowExpirationPolicy == BufferExpirationPolicy.TimeCapacity)
                            if (length(vns_lookback_values) >= 6)
                                latest_timestamps = vns_lookback_values_ts((end-6):end);
                                diff_latest_timestamps = diff(latest_timestamps) * 1000;
                                median_interval_ms = median(diff_latest_timestamps);

                                %Now that we have a measure of the median
                                %ISI, calculate how many samples our buffer
                                %should be
                                buffer_size_limit = round((lookback_window_seconds * 1000) / median_interval_ms);

                                %Now that we know our buffer size, limit
                                %the capacity of the buffer to that size
                                vns_lookback_values = vns_lookback_values((end-buffer_size_limit):end);
                                vns_lookback_values_ts = vns_lookback_values_ts((end-buffer_size_limit):end);
                            end
                        else
                            first_idx = length(vns_lookback_values) - vns_parameters.LookbackWindowCapacity + 1;
                            if (first_idx < 1)
                                first_idx = 1;
                            end
                            vns_lookback_values = vns_lookback_values(first_idx:end);
                            vns_lookback_values_ts = vns_lookback_values_ts(first_idx:end);
                        end

                        %The matlab prctile function expects a number
                        %between 0 and 100, rather than 0 to 1
                        vns_parameters_selectivity = vns_parameters.Selectivity * 100;
                        values_above_pos_noise_floor = vns_lookback_values(vns_lookback_values >= vns_parameters.NoiseFloor);
                        values_below_neg_noise_floor = vns_lookback_values(vns_lookback_values < -vns_parameters.NoiseFloor);

                        if (~isempty(values_above_pos_noise_floor))
                            vns_current_positive_threshold = max([vns_parameters.NoiseFloor, prctile(values_above_pos_noise_floor, vns_parameters_selectivity)]);
                        end

                        if (~isempty(values_below_neg_noise_floor))
                            vns_current_negative_threshold = min([-vns_parameters.NoiseFloor, prctile(values_below_neg_noise_floor, 100 - vns_parameters_selectivity)]);
                        end

                        %Now determine whether to issue a stimulation
                        %trigger
                        trigger_based_on_value = ( ...
                            ((s2_result >= vns_current_positive_threshold) && (vns_parameters.TriggerOnPositive)) || ...
                            ((s2_result <= vns_current_negative_threshold) && (vns_parameters.TriggerOnNegative)) ...
                        );

                        if (trigger_based_on_value && allow_trigger_based_on_timing)
                            vns_most_recent_stimulation_time = sample_ts;
                            should_we_trigger = true;
                            result_vns_trigger_ts = [result_vns_trigger_ts sample_ts];
                        end

                        vns_most_recent_should_we_trigger = should_we_trigger;

                        if (vns_parameters.SelectivityControlledByDesiredISI)
                            [vns_stim_times, vns_parameters] = RePlayVNSAlgorithm.adjust_selectivity_based_upon_desired_isi( ...
                                sample_ts, ...
                                should_we_trigger, ...
                                vns_parameters, ...
                                sel_adjust_vns_stim_times, ...
                                sel_adjust_most_recent_selectivity_adjustment_time, ...
                                sel_adjust_selectivity_adjustment_period, ...
                                sel_adjust_saturation_time); 
                        end

                        result_vns_positive_threshold = [result_vns_positive_threshold vns_current_positive_threshold];
                        result_vns_negative_threshold = [result_vns_negative_threshold vns_current_negative_threshold];

                    end
                end

            end

        end

    end

end




































