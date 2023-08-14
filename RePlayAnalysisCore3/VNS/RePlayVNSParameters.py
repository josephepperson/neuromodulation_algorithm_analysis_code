from mongoengine import *
from datetime import timedelta
from enum import Enum

from RePlayAnalysisCore3.CustomFields.CustomFields import TimedeltaField
from RePlayAnalysisCore3.CustomFields.CustomFields import IntEnumField

class SmoothingOptions(Enum):
    NoSmoothing = 0
    AveragingFilter = 1

class Stage1_Operations(Enum):
    NoOperation = 0
    SubtractMean = 1
    Derivative = 2
    Gradient = 3

class Stage2_Operations(Enum):
    RMS = 0
    SignedRMS = 1
    Mean = 2
    Sum = 3
    NoOperation = 4

class BufferExpirationPolicy(Enum):
    TimeLimit = 0
    TimeCapacity = 1
    NumericCapacity = 2

class RePlayVNSParameters(EmbeddedDocument):
    Enabled = BooleanField(default = False)
    Minimum_ISI = TimedeltaField(default = timedelta(seconds = 0))
    Desired_ISI = TimedeltaField(default = timedelta(seconds = 0))
    Selectivity = FloatField(default = float("NaN"))
    CompensatorySelectivity = FloatField(default = float("NaN"))
    TyperSharkLookbackSize = FloatField(default = float("NaN"))
    LookbackWindow = TimedeltaField(default = timedelta(seconds = 0))
    SmoothingWindow = TimedeltaField(default = timedelta(seconds = 0))
    NoiseFloor = FloatField(default = float("NaN"))
    TriggerOnPositive = BooleanField(default = False)
    TriggerOnNegative = BooleanField(default = False)
    SelectivityControlledByDesiredISI = BooleanField(default = False)
    Stage1_Smoothing = IntEnumField(SmoothingOptions, default=SmoothingOptions.NoSmoothing)
    Stage2_Smoothing = IntEnumField(SmoothingOptions, default=SmoothingOptions.NoSmoothing)
    Stage1_Operation = IntEnumField(Stage1_Operations, default=Stage1_Operations.NoOperation)
    Stage2_Operation = IntEnumField(Stage2_Operations, default = Stage2_Operations.NoOperation)
    VNS_AlgorithmParameters_SaveVersion = IntField(default = 0)
    LookbackWindowExpirationPolicy = IntEnumField(BufferExpirationPolicy, default=BufferExpirationPolicy.TimeLimit)
    LookbackWindowCapacity = IntField(0)
    SmoothingKernelSize = TimedeltaField(default = timedelta(seconds = 0))

    def __init__(self, *args, **values):
        super().__init__(*args, **values)
