% Example of how to use the Matlab reference implementation of the RePlay 
% VNS algorithm

% To run this example: first load in the example exported data file that 
% is stored in the same folder as this script. The data file should be
% named:
%   001-002-01012_SpaceRunner_20220928_085441_export.mat
% 
% You must also make sure that the Matlab reference implementation of the 
% RePlay VNS algorithm is in your Matlab path. There are 6 files in the
% Matlab implementation, and they must all be in your path. They are:
%   BufferExpirationPolicy.m
%   RePlayVNSAlgorithm.m
%   RePlayVNSParameters.m
%   SmoothingOptions.m
%   Stage1_Operations.m
%   Stage2_Operations.m
%
% Let me know if you have any questions or feedback.
%
%   - David

p = RePlayVNSParameters;
p.Enabled = true;
p.Minimum_ISI = seconds(5);
p.Desired_ISI = seconds(15);
p.SelectivityControlledByDesiredISI = false;
p.Selectivity = 0.9;
p.CompensatorySelectivity = 0;
p.SmoothingWindow = seconds(0.3);
p.LookbackWindowExpirationPolicy = BufferExpirationPolicy.NumericCapacity;
p.LookbackWindowCapacity = 300;
p.LookbackWindow = seconds(5);
p.TyperSharkLookbackSize = 5;
p.NoiseFloor = 0.0258;
p.TriggerOnPositive = true;
p.TriggerOnNegative = true;
p.Stage1_Smoothing = SmoothingOptions.AveragingFilter;
p.Stage2_Smoothing = SmoothingOptions.AveragingFilter;
p.Stage1_Operation = Stage1_Operations.Gradient;
p.Stage2_Operation = Stage2_Operations.Sum;
p.VNS_AlgorithmParameters_SaveVersion = 4;

gain = 1.72;

temp_signal = (data.signal_game * gain) / 100;
[result_vns_signal, result_vns_positive_threshold, result_vns_negative_threshold, result_vns_timeout, result_vns_trigger_ts] = ...
    RePlayVNSAlgorithm.ProcessSignal(temp_signal, data.signal_timestamps, p, []);

figure;
subplot(2, 1, 1);
hold on;
plot(data.signal_timestamps, data.signal_vns);
title('VNS signal calculated by Python code');
ylim([-0.3 0.3]);

subplot(2, 1, 2);
hold on;
plot(data.signal_timestamps, result_vns_signal);
title('VNS signal calculated by Matlab code');
ylim([-0.3 0.3]);



























