from mongoengine import *

class PostHocVNSObject(Document):

    meta = {
        'allow_inheritance': True, 
        'collection':'VNS_Calculated_Signal_Data',
        'strict':False
    }    

    post_hoc_vns_algorithm_data_has_been_calculated = BooleanField(default=False)
    post_hoc_vns_algorithm_signal_value = ListField(FloatField())
    post_hoc_vns_algorithm_positive_threshold = ListField(FloatField())
    post_hoc_vns_algorithm_negative_threshold = ListField(FloatField())
    post_hoc_vns_algorithm_timing_allows_trigger = ListField(FloatField())
    post_hoc_vns_algorithm_trigger_timestamps = ListField(FloatField())

    def __init__(self, *args, **values):
        super().__init__(*args, **values)

    def SetData (self, has_been_calculated, signal_value, pos_thresh, neg_thresh, allows_trigger, ts):
        #Set all the properties
        self.post_hoc_vns_algorithm_data_has_been_calculated = has_been_calculated
        self.post_hoc_vns_algorithm_signal_value = signal_value
        self.post_hoc_vns_algorithm_positive_threshold = pos_thresh
        self.post_hoc_vns_algorithm_negative_threshold = neg_thresh
        self.post_hoc_vns_algorithm_timing_allows_trigger = allows_trigger
        self.post_hoc_vns_algorithm_trigger_timestamps = ts

        #Save this object
        self.save()
