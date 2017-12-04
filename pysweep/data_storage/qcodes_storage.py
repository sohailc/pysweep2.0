import numpy as np

import qcodes
from qcodes.instrument.parameter import ArrayParameter

from pysweep.data_storage.json_storage import JSONStorage


class ParameterFromArray(ArrayParameter):
    def __init__(self, name):
        super().__init__(
            name,
            shape=(1,),
        )

        self.name = name
        self._data_array = None

    def prepare(self, data_array, shape, set_points_arrays, unit):
        self._data_array = np.array(data_array).reshape(shape)
        self.shape = shape
        self.setpoint_units = unit, unit
        self.setpoint_names = ('sample_nr', 'sample_nr')
        self.setpoint_labels = ('Sample number', 'Sample number')

        xs = tuple([i[0] for i in zip(*set_points_arrays)])
        ys = tuple([i[1] for i in zip(*set_points_arrays)])

        #self.setpoints = tuple(range(100)), (tuple(range(100)), tuple(range(100)))

    def get_raw(self):
        return self._data_array


class QcodesStorage(JSONStorage):
    def __init__(self):
        super().__init__(unit="replace", value="append", independent_parameter="replace")

    @staticmethod
    def _find_data_shape(set_points_array):
        return tuple([len(set(arry)) for arry in set_points_array])

    def output(self, name):
        oput = super().output(name)

        data_array = oput[name]["value"]
        unit = oput[name]["unit"]
        set_points_arrays = [arry["value"] for arry in oput.values() if "independent_parameter" in arry]
        shape = QcodesStorage._find_data_shape(set_points_arrays)

        param_array = ParameterFromArray(name)
        param_array.prepare(data_array, shape, set_points_arrays, unit)
        return qcodes.Measure(param_array).run()
