from collections import OrderedDict
import numpy as np

import qcodes


class StdIOMock:
    def __init__(self):
        self._buffer = ""

    def write(self, value):
        self._buffer += "\n" + str(value)

    def __repr__(self):
        return self._buffer

    def flush(self):
        self._buffer = ""


class BaseObjectFactory:
    def __init__(self, ObjectType):
        self._ObjectType = ObjectType
        self._objects = {}

    def _getitem(self, index):
        if index in self._objects.keys():
            obj = self._objects[index]
        else:
            args, kwargs = self._args_function()
            obj = self._ObjectType(*args, **kwargs)
            self._objects[index] = obj

        return obj

    def __getitem__(self, s):
        if isinstance(s, slice):
            if s.start is None:
                start = 0
            else:
                start = s.start

            if s.stop is None:
                raise ValueError("cannot return an infinite number of objects")

            return [self._getitem(i) for i in range(start, s.stop)]
        else:
            return self._getitem(s)

    def _args_function(self):
        raise NotImplementedError("Please base class")


class ParameterFactory(BaseObjectFactory):
    def __init__(self, std_out):
        self._std_out = std_out
        self._counter = 0
        super().__init__(qcodes.StandardParameter)

    def _args_function(self):
        def setter(v):
            self._std_out.write("setting {} to {}".format(label, v))

        def getter():
            return 0

        label = "parameter {}".format(self._counter)
        self._counter += 1
        return (), {"name": label, "set_cmd": setter, "get_cmd": getter, "unit": "V"}


class SweepValuesFactory(BaseObjectFactory):
    def __init__(self):
        super().__init__(list)

    def _args_function(self):
        l = int(np.random.uniform(3, 6))
        return (np.random.normal(0, 1.0, l),), {}


def sorted_dict(dcts):

    if not isinstance(dcts, list):
        dcts = [dcts]

    d = OrderedDict()
    for dct in dcts:
        d.update(OrderedDict(sorted(dct.items(), key=lambda t: t[0])))

    return d
