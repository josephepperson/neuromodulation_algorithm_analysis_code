from mongoengine import *
import numpy
import math
from RePlayAnalysisCore3.RePlayExercises import RePlayExercises

class DatabaseAnalysisUnitDocument(Document):
    meta = {
        'allow_inheritance': True,
        'abstract': True
    }

    parent = GenericReferenceField()
    children = ListField(GenericReferenceField())
    tags = DictField()

    _excluded = BooleanField(default=False, db_field="excluded")
    _is_dirty = BooleanField(default=True)

    #region Constructor

    def __init__(self, *args, **values):
        super().__init__(*args, **values)

    #endregion

    #region Properties

    @property
    def excluded (self):
        return self._excluded

    @excluded.setter
    def excluded (self, value):
        if (value != self._excluded):
            self._excluded = value
            self.save()
            self._handle_exclusion_toggled()

    @property
    def is_dirty (self):
        return self._is_dirty

    @is_dirty.setter
    def is_dirty (self, value):
        if (value != self._is_dirty):
            self._is_dirty = value
            self.save()
            if ((not (self.parent is None)) and (isinstance(self.parent, DatabaseAnalysisUnitDocument))):
                self.parent.HandleDirtyChild(self)
    
    #endregion

    #region Private methods

    def _handle_exclusion_toggled(self):
        #This method will be overriden and implemented by inheriting classes
        pass

    def _assert_metrics_in_tags(self):
        if (not ("metrics" in self.tags)):
            self.tags["metrics"] = {}

    #endregion

    #region Methods

    def HasNestedDirtyChildren (self):
        new_is_dirty = False
        if (self.children is not None) and (len(self.children) > 0):
            all_children_nested_is_dirty = [x.HasNestedDirtyChildren() for x in self.children]
            new_is_dirty = any(all_children_nested_is_dirty)
        else:
            new_is_dirty = self.is_dirty
        return new_is_dirty

    def HandleDirtyChild (self, child):
        if (self.children is not None) and (len(self.children) > 0):
            all_children_is_dirty = [x.is_dirty for x in self.children]
            new_is_dirty = any(all_children_is_dirty)
            if (new_is_dirty != self.is_dirty):
                self.is_dirty = new_is_dirty

    def VerifyDirtyChildren (self):
        if (self.children is not None) and (len(self.children) > 0):
            for child in self.children:
                child.VerifyDirtyChildren()
            self.HandleDirtyChild(None)

    def HasAnalysisMetric (self, variable_name):
        self._assert_metrics_in_tags()
        return (variable_name in self.tags["metrics"])
            
    def FetchAnalysisMetric (self, variable_name):
        #Make sure that object has "metrics" in its collection of tags.
        self._assert_metrics_in_tags()

        #Grab the value of this metric
        result = float("NaN")
        if (variable_name in self.tags["metrics"]):
            result = self.tags["metrics"][variable_name]
            if (result is None):
                result = float("NaN")

        #Return the result to the user
        return result

    def FetchAnalysisMetricIndividualData (self, variable_name):
        #Grab values from children
        list_of_values = []
        for current_child in self.children:
            if (current_child.HasAnalysisMetric(variable_name)) and (not current_child.excluded):
                current_child_result = current_child.FetchAnalysisMetric(variable_name)
                list_of_values.append(current_child_result)

        return list_of_values

    def CalculateAnalysisMetrics (self):
        #Resolve analysis metrics on children that are currently "dirty"
        for current_child in self.children:
            if (current_child.HasNestedDirtyChildren()):
                try:
                    current_child.CalculateAnalysisMetrics()
                    current_child.is_dirty = False
                    current_child.save()
                except Exception as ex:
                    print(ex)
                    pass

        #Now let's aggregate the data from all children
        
        #First, get the list of all analysis metrics
        all_variable_names = RePlayExercises.get_all_variables()

        #Next, let's iterate through each metric and calculate the result
        for current_metric in all_variable_names:
            self.CalculateIndividualAnalysisMetric(current_metric)

    def CalculateIndividualAnalysisMetric (self, variable_name):
        #This function may be overriden and implemented by inheritors of this class
        pass

        '''
        #Grab values from children
        list_of_values = []
        for current_child in self.children:
            if (current_child.HasAnalysisMetric(variable_name)) and (not current_child.excluded):
                current_child_result = current_child.FetchAnalysisMetric(variable_name)
                if (current_child_result is not None):
                    if (isinstance(current_child_result, list) or isinstance(current_child_result, tuple)):
                        list_of_values.append(current_child_result[0])
                    else:
                        list_of_values.append(current_child_result)
        
        #Calculate the aggregate mean of the collected values
        if (len(list_of_values) > 0) and (any(~numpy.isnan(list_of_values))):
            result_mean = numpy.nanmean(list_of_values)
        else:
            result_mean = float("NaN")

        result_std_err = float("NaN")
        sample_size = numpy.count_nonzero(~numpy.isnan(list_of_values))
        if (sample_size > 0):
            result_std_err = numpy.nanstd(list_of_values) / math.sqrt(sample_size)

        #Make sure the "metrics" tag exists in our dictionary of tags
        self._assert_metrics_in_tags()

        #Store the result in the "metrics" of this visit
        self.tags["metrics"][variable_name] = (result_mean, result_std_err)
        '''

    #endregion
    