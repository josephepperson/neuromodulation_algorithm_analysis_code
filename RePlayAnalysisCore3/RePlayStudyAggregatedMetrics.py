import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)

from mongoengine import *
from numpy.core.records import fromarrays
from scipy.io import savemat
import pandas
import json

from RePlayAnalysisCore3.RePlayExercises import RePlayExercises
from RePlayAnalysisCore3.LoadedFilesCollection import *
from RePlayAnalysisCore3.RePlayUtilities import RePlayUtilities

class RePlayStudyAggregatedMetrics (Document):
    #Defining some metadata telling the db what collection to use for this class
    meta = {
        'collection':'RePlayStudyAggregatedMetrics',
    }    

    #region Fields that are saved to the database

    aggregated_metrics = DictField()

    #endregion

    #region Constructor

    def __init__(self, *args, **values):
        super().__init__(*args, **values)

    #endregion


