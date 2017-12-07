import numpy as np

from pysweep.data_storage.base_storage import BaseStorage


class NpStore(BaseStorage):
    def __init__(self):
        self._buffer = dict()

    @staticmethod
    def get_value_shapes(values):
        shapes = []
        for value in values:
            if hasattr(value, "shape"):
                shape = str(value.shape)
            else:
                shape = ""

            shapes.append(shape)

        return shapes

    def dict_to_array(self, dictionary):

        units = [d["unit"] for d in dictionary.values()]
        field_names = ["{} [{}]".format(*nu) for nu in zip(dictionary.keys(), units)]

        values = [d["value"] for d in dictionary.values()]
        shapes = self.get_value_shapes(values)

        types = [shp + str(np.dtype(type(i))) for shp, i in zip(shapes, values)]
        dtype = list(zip(field_names, types))

        return np.array([tuple(values)], dtype=dtype)

    @staticmethod
    def group_parameters_by_filter(records, filtr):  # filter is a reserved keyword
        in_group = dict()
        out_group = dict()

        for name, parameter in records.items():
            if filtr(parameter):
                in_group.update({name: parameter})
            else:
                out_group.update({name: parameter})

        return in_group, out_group

    def add(self, record):

        independents, dependents = self.group_parameters_by_filter(
            record,
            lambda d: d.get('independent_parameter', False)
        )

        for name, parameter in dependents.items():

            dictionary = dict(independents)
            dictionary.update({name: parameter})

            ary = self.dict_to_array(dictionary)

            if name not in self._buffer:
                self._buffer[name] = ary
            else:
                self._buffer[name] = np.append(self._buffer[name], ary)