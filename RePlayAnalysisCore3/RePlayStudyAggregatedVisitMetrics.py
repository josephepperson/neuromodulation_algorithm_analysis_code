from mongoengine import *

class RePlayStudyAggregatedVisitMetrics (Document):
    #Defining some metadata telling the db what collection to use for this class
    meta = {
        'collection':'RePlayStudyAggregatedVisitMetrics',
    }    

    #region Fields that are saved to the database

    aggregated_visit_metrics = DictField()

    #endregion

    #region Constructor

    def __init__(self, *args, **values):
        super().__init__(*args, **values)

    #endregion


