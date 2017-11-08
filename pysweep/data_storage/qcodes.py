"""
This formatter uses the native QCoDeS, SQL light based data storage class. We require the correct QCoDeS branch
for this to work currently
"""

try:
    from qcodes.dataset.param_spec import ParamSpec
except ImportError:
    raise ImportError("Your QOcDeS installation does not have the data set support. Make sure that your environment "
                      "contains the right QCoDeS branch as data set support has not been merged yet in main")

from pysweep.data_storage.base_storage import BaseStorage


class QcodesStorage(BaseStorage):
    def __init__(self, data_set):

        self._data_set = data_set
        self._parameters = set()  # Parameter names

    def _add_to_dataset(self, data_set, parameter_name, unit, depends_on):
        ty = "number"  # for now
        param_spec = ParamSpec(parameter_name, ty, depends_on=depends_on, unit=unit)
        data_set.add_parameters([param_spec])
        self._parameters.add(parameter_name)

    def _register_parameters_in_dataline(self, data_line):
        # Make sure all parameters in a data line are registered in the QCoDeS data set
        # first find all independent parameters in the data line and make sure they are registered
        independent_parameters = []
        dependent_parameters = []

        for parameter_name in data_line.keys():
            if "independent_parameter" in data_line[parameter_name]:
                independent_parameters.append(parameter_name)

                if parameter_name not in self._parameters:
                    unit = data_line[parameter_name]["unit"]
                    self._add_to_dataset(self._data_set, parameter_name, unit, [])
            else:
                dependent_parameters.append(parameter_name)

        # Then process all dependent parameters
        for parameter_name in dependent_parameters:
            if parameter_name not in self._parameters:
                unit = data_line[parameter_name]["unit"]
                self._add_to_dataset(self._data_set, parameter_name, unit, independent_parameters)

    def add(self, dictionary):
        self._register_parameters_in_dataline(dictionary)
        self._data_set.add_result({k: dictionary[k]["value"] for k in dictionary.keys()})

    def output(self):
        return self._data_set

    def finalize(self):
        pass