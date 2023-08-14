from mongoengine import *

from RePlayAnalysisCore3.Documents.DatabaseAnalysisUnitDocument import DatabaseAnalysisUnitDocument
from RePlayAnalysisCore3.RePlayStudy import RePlayStudy

class RePlayParticipant(DatabaseAnalysisUnitDocument):
    meta = {
        'collection':'RePlayParticipant'
    }    

    uid = StringField(max_length = 200, default="")
    _group = StringField(max_length = 200, db_field="group", default="Unknown")
    _is_active = BooleanField(default=True, db_field="is_active")

    def __init__(self, *args, **values):
        super().__init__(*args, **values)

    #region Properties

    @property
    def is_active (self):
        return self._is_active

    @is_active.setter
    def is_active(self, value):
        if (self._is_active != value):
            self._is_active = value
            self.save()

    @property
    def group (self):
        return self._group

    @group.setter
    def group (self, value):
        if (self._group != value):
            self._group = value
            self.save()
            RePlayStudy.GetStudy().UpdateParticipantGroupInAggregatedMetrics(self)

    #endregion

    #region Methods to handle what happens when this participant is included/excluded

    def _handle_exclusion_toggled(self):
        #Update the master dataframe
        RePlayStudy.GetStudy().UpdateParticipantInclusionInAggregatedMetrics(self)        

    #endregion        

