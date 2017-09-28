from inspect import signature, isgeneratorfunction

from qcodes import StandardParameter


class BaseSweepObject:
    def __init__(self, parameters, point_function):
        """
        Parameters
        ----------
        parameters: list, qcodes.StandardParameter
        point_function: list, ndarray or callable
            list, ndarray or callable returning a list or ndarray of tuples. The length of the tuple is equal to the
            number of parameters
        """

        self._parameters = parameters
        self._point_function = point_function
        self._point_generator = None
        self._station = None
        self._namespace = None

    def __next__(self):

        values = next(self._point_generator)
        return {p.label: {"unit": p.units, "value": v} for p, v in zip(self._parameters, values)}

    def __iter__(self):
        self._point_generator = self._point_function()
        return self


class SweepObject(BaseSweepObject):
    def __init__(self, parameter, point_function, station, namespace):
        """
        Parameters
        ----------
        parameter: list, qcodes.StandardParameter
        point_function: callable
        station: qcodes.Station
        namespace: pysweep.Namespace
        """
        def pf():
            return point_function

        if not isinstance(parameter, StandardParameter):
            raise ValueError("The Parameter should be of type QCoDeS StandardParameter")

        self.parameter = parameter
        self._station = station
        self._namespace = namespace

        if not callable(point_function):
            point_function_callable = pf
        else:
            point_function_callable = point_function

        sig = signature(point_function_callable)
        if list(sig.parameters.keys()) == ["station", "namespace"]:
            args = (self._station, self._namespace)
        else:
            args = ()

        self.point_function = lambda: ((i,) for i in point_function_callable(*args))

        super().__init__([self.parameter], self.point_function)


def _two_product(sweep_object1, sweep_object2):
    """
    Parameters
    ----------
    sweep_object1: SweepObject
    sweep_object2: SweepObject
    """

    parameters = [sweep_object1.parameter, sweep_object2.parameter]

    point_function1 = sweep_object1.point_function
    point_function2 = sweep_object2.point_function

    if any([isgeneratorfunction(i) for i in [point_function1, point_function2]]):
        pass
