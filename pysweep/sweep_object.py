from qcodes import StandardParameter

from .chain_operators import pass_operator, product_operator


class ParameterWrapper:

    @staticmethod
    def dummy_each(station, namespace):
        pass

    def __init__(self, param, before_each=None, after_each=None):
        self._param = param
        if before_each is None:
            self._before_each = ParameterWrapper.dummy_each
        else:
            self._before_each = before_each

        if after_each is None:
            self._after_each = ParameterWrapper.dummy_each
        else:
            self._after_each = after_each

    def add_before_each(self, before_each):
        self._before_each = before_each

    def add_after_each(self, after_each):
        self._after_each = after_each

    def set(self, value, station, namespace):
        self._before_each(station, namespace)
        self._param.set(value)
        self._after_each(station, namespace)

    @property
    def label(self):
        return self._param.label

    @property
    def units(self):
        return self._param.units


class BaseSweepObject:
    def __init__(self, parameters, point_functions, chain_operator, before_each=None, after_each=None):
        """
        Parameters
        ----------
        parameters: list, qcodes.StandardParameter
        point_functions: list, generator_function, n_parameters
            A list of equal length as the number of parameters. Each generator function accepts two parameters; a
             QCoDeS Station and a pysweep Namespace. Each "next" operation on the generators gives the next value to be
             set on the parameters
        chain_operator: callable
            Callable which accepts a list of generator functions as input and returns a single generator function. This
            function accepts two parameters: a QCoDeS Station and a pysweep Namespace
        """

        self._parameters = [{False: ParameterWrapper(p, before_each, after_each), True: p}
                            [isinstance(p, ParameterWrapper)] for p in parameters]

        self._point_functions = point_functions
        self._chain_operator = chain_operator

        self._point_generator = None
        self._station = None
        self._namespace = None
        self._after_each = after_each
        self._before_each = before_each

    def __next__(self):
        values, modify = next(self._point_generator)

        for parameter, value, mdy in zip(self._parameters, values, modify):
            if mdy:
                parameter.set(value, self._station, self._namespace)

        return {p.label: {"unit": p.units, "value": v} for p, v in zip(self._parameters, values)}

    def __iter__(self):
        self._point_generator = self._chain_operator(self._point_functions)(self._station, self._namespace)
        return self

    def set_station(self, station):
        self._station = station

    def set_namespace(self, namespace):
        self._namespace = namespace

    def unset_namespace(self):
        self._namespace = None

    def after_each(self, after_each_function):
        self._parameters[0].add_after_each(after_each_function)
        return self

    def before_each(self, before_each_function):
        self._parameters[-1].add_before_each(before_each_function)
        return self


class SweepObject(BaseSweepObject):
    def __init__(self, parameter, point_function):
        """
        Parameters
        ----------
        parameter: list, qcodes.StandardParameter
        point_function: iterable or a function returning an iterable
        """
        if not isinstance(parameter, StandardParameter):
            raise ValueError("The Parameter should be of type QCoDeS StandardParameter")

        if not callable(point_function):
            _point_function = lambda station, namespace: (i for i in point_function)
        else:
            _point_function = point_function

        super().__init__([parameter], [_point_function], chain_operator=pass_operator)


def sweep_product(sweep_objects):
    """
    Parameters
    ----------
    sweep_objects: list, SweepObject
    """

    params = []
    point_functions = []
    for p in sweep_objects:
        params.extend(p._parameters)
        point_functions.extend(p._point_functions)

    return BaseSweepObject(params, point_functions, chain_operator=product_operator)


