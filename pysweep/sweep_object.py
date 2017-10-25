from qcodes import StandardParameter

from pysweep.utils import DictMerge


class BaseForEach:
    def __init__(self, set_function):
        self._set_function = set_function

        self._values = None
        self._result_merger = DictMerge(unit="replace", value="append", independent_parameter="replace")
        self._callable_list = []
        self._before_each_list = []
        self._namespace = None
        self._station = None

    def _values_factory(self):
        raise NotImplementedError("please sub class")

    def __iter__(self):
        self._values = self._values_factory()
        return self

    def _exec_before_each(self):
        result = {}
        for before_each_function in self._before_each_list:
            r = before_each_function(self._station, self._namespace)
            result = self._result_merger.merge([r, result])

        return result

    def __next__(self):
        nxt_value = next(self._values)
        result = self._exec_before_each()
        result = self._result_merger.merge([self._set_function(nxt_value), result])

        for clbl in self._callable_list:
            r = clbl(station=self._station, namespace=self._namespace)
            if isinstance(clbl, BaseForEach):
                for ir in r:
                    result = self._result_merger.merge([ir, result])
            else:
                result = self._result_merger.merge([r, result])

        return result

    def __call__(self, *callables, station=None, namespace=None):
        self._station = station or self._station
        self._namespace = namespace or self._namespace
        self._callable_list.extend(callables)
        return self

    def before_each(self, func):
        self._before_each_list.append(func)
        return self

    def set_station(self, station):
        """
        Make a station available to measurements being performed

        Parameters
        ----------
        station: qcodes.station

        Returns
        -------
        self
        """
        if station is not None:
            self._station = station
        return self

    def set_namespace(self, namespace):
        """
        Make a namespace available to measurements being performed

        Parameters
        ---------
        namespace: pysweep.Namespace

        Returns
        -------
        self
        """
        if namespace is not None:
            self._namespace = namespace
        return self


class ForEachFunction(BaseForEach):
    def __init__(self, set_function, value_list):
        super().__init__(set_function)
        self._value_list = value_list

    def _values_factory(self):
        return iter(self._value_list)


class ForEachParameter(BaseForEach):
    def __init__(self, param, value_list):
        self._param = param
        super().__init__(self._setter)
        self._value_list = value_list

    def _setter(self, value):
        self._param(value)
        if self._param._instrument is not None:
            label = "{}_{}".format(self._param._instrument.name, self._param.label)
        else:
            label = self._param.label

        return {label: {"unit": self._param.unit, "value": value}}

    def _values_factory(self):
        return iter(self._value_list)


def for_each(obj, values):
    if isinstance(obj, StandardParameter):
        return ForEachParameter(obj, values)
    else:
        return ForEachFunction(obj, values)
