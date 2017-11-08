"""
This formatter uses the native QCoDeS, SQL light based data storage class
"""

try:
    from qcodes.dataset.param_spec import ParamSpec
except ImportError:
    raise ImportError("Your QOcDeS installation does not have the data set support. Make sure that your environment "
                      "contains the right QCoDeS branch as data set support has not been merged yet in main")

from pysweep.data_storage.output_formatter import BaseFormatter


class QcodesNativeFormatter(BaseFormatter):
    def __init__(self, experiment):
        self._experiment = experiment
        self._parameters = set()  # Parameter names

    def _add_to_dataset(self, data_set, parameter_name, unit, depends_on):
        ty = "number"  # for now
        param_spec = ParamSpec(parameter_name, ty, depends_on=depends_on, unit=unit)
        data_set.add_parameters([param_spec])
        self._parameters.add(parameter_name)

    def _register_parameters_in_dataline(self, data_set, data_line):
        # Make sure all parameters in a data line are registered in the QCoDeS data set
        # first find all independent parameters in the data line and make sure they are registered
        independent_parameters = []
        dependent_parameters = []

        for parameter_name in data_line.keys():
            if "independent_parameter" in data_line[parameter_name]:
                independent_parameters.append(parameter_name)

                if parameter_name not in self._parameters:
                    unit = data_line[parameter_name]["unit"]
                    self._add_to_dataset(data_set, parameter_name, unit, [])
            else:
                dependent_parameters.append(parameter_name)

        # Then process all dependent parameters
        for parameter_name in dependent_parameters:
            if parameter_name not in self._parameters:
                unit = data_line[parameter_name]["unit"]
                self._add_to_dataset(data_set, parameter_name, unit, independent_parameters)

    def run(self, sweep_object, data_set_name):

        data_set = self._experiment.new_data_set(data_set_name)

        for data_line in sweep_object:
            self._register_parameters_in_dataline(data_set, data_line)
            data_set.add_result({k: data_line[k]["value"] for k in data_line.keys()})

        return data_set