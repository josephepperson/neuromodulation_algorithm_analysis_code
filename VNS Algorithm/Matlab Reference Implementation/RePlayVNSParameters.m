classdef RePlayVNSParameters

    properties
        
        Enabled logical = false
        Minimum_ISI duration = seconds(0)
        Desired_ISI duration = seconds(0)
        Selectivity double = nan
        CompensatorySelectivity double = nan
        TyperSharkLookbackSize double = nan
        LookbackWindow duration = seconds(0)
        SmoothingWindow duration = seconds(0)
        NoiseFloor double = nan
        TriggerOnPositive logical = false
        TriggerOnNegative logical = false
        SelectivityControlledByDesiredISI logical = false
        Stage1_Smoothing SmoothingOptions = SmoothingOptions.NoSmoothing
        Stage2_Smoothing SmoothingOptions = SmoothingOptions.NoSmoothing
        Stage1_Operation Stage1_Operations = Stage1_Operations.NoOperation
        Stage2_Operation Stage2_Operations = Stage2_Operations.NoOperation
        VNS_AlgorithmParameters_SaveVersion int32 = 0
        LookbackWindowExpirationPolicy BufferExpirationPolicy = BufferExpirationPolicy.TimeLimit
        LookbackWindowCapacity int32 = 0
        SmoothingKernelSize duration = seconds(0)

    end

end