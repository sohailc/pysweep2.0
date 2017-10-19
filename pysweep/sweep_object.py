"""
A sweep object allows us to quickly express a measurement where we loop over independent experimental parameters and
perform measurements at different phases in the loop: either after the start of a loop, after at the end of it, or after
each of the set points in the sweep.
"""
import time
from collections import OrderedDict

import qcodes


class BaseSweepObject:
    """
    A sweep object is defined as follows:
    1) It is iterable and looping over a sweep object shall result in independent measurement parameters being set
    at each iteration
    2) At each iteration a dictionary is returned containing information about the parameters that have been set
    and the result of the measurement performed at each set point
    3) A sweep object implements the following methods at minimum:

       * after_each
       * after_start
       * after_end
       * set_station
       * set_namespace

       The meaning and signatures of these methods are explained in their respective doc strings.
    """

    @classmethod
    def add_alias(cls, name, func):
        """
        Adding an alias on the class allows the experimenter to define extensions to the base class which (s)he
        finds handy. Examples are provided in the testing module (see "test_alias") and in the documentation.
        """
        setattr(cls, name, lambda so, *args: func(so, *args))

    def __init__(self):
        # The following attributes are determined when we begin iteration...
        self._param_setter = None  # A "param_setter" is an iterator which, when "next" is called a new value of the
        # independent parameter is set.
        self._station = None  # A QCoDeS station which allows us to access measurement instruments
        self._namespace = None  # The namespace allows different measurement functions to share a memory space

        self._measure_functions = {
            "after_each": [],
            "after_start": [],
            "after_end": []
        }

    def _execute_measure_function(self, name):
        msg_all = dict()
        for func in self._measure_functions[name]:
            msg = func(self._station, self._namespace)
            msg_all.update(msg)

        return msg_all

    def _add_measurement_hooks(self, param_setter):
        """
        This function takes the "bare" param_setter iterable and makes sure the correct measurement functions get
        called at the appropriate time.

        Parameters
        ----------
        param_setter: iterable

        Returns
        -------
        iterable
        """
        start = True
        for main_msg in param_setter:
            after_msg = self._execute_measure_function("after_each")
            main_msg.update(after_msg)

            if start:
                self._execute_measure_function("after_start")
                start = False

            yield main_msg

        yield self._execute_measure_function("after_end")

    def _setter_factory(self):
        """
        When called, this method returns the param setter iterable appropriate for this measurement
        """
        raise NotImplementedError("Please subclass BaseSweepObject")

    def __iter__(self):
        self._param_setter = self._add_measurement_hooks(self._setter_factory())
        return self

    def __next__(self):
        return next(self._param_setter)

    def after_each(self, func):
        """
        Perform a measurement at each set point

        Parameters
        ----------
        func: callable
            A callable of two parameters: station, namespace. This callable returns the result of the measurement
            in a JSON compatible dictionary (e.g. {"gate_voltage": {"unit": "V", "value": 2.3}} )

        Returns
        -------
        self
        """
        self._measure_functions["after_each"].append(func)
        return self

    def after_start(self, func):
        """
        Perform a measurement after setting the first set point in a sweep

        Parameters
        ----------
        func: callable
            A callable of two parameters: station, namespace. This callable returns nothing

        Returns
        -------
        self
        """
        self._measure_functions["after_start"].append(func)
        return self

    def after_end(self, func):
        """
        Perform a measurement after finishing a sweep

        Parameters
        ----------
        func: callable
            A callable of two parameters: station, namespace. This callable returns nothing

        Returns
        -------
        self
        """
        self._measure_functions["after_end"].append(func)
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

# --------------Sweep Subclasses ----------------------------------------------------------------------------


class IteratorSweep(BaseSweepObject):
    """
    Sweep independent parameters by unrolling an iterator. This class is useful if we have "bare" parameter set iterator
    and need to create a proper sweep object as defined in the BaseSweepObject docstring. See the "NestedSweep"
    subclass for an example.

    Parameters
    ----------
    iterator_function: callable
        A callable with no parameters, returning an iterator. Unrolling this iterator has the
        effect of setting the independent parameters.
    """
    def __init__(self, iterator_function):
        self._iterator_function = iterator_function
        super().__init__()

    def _setter_factory(self):
        return self._iterator_function()


class ParameterSweep(BaseSweepObject):
    """
    Sweep independent parameters by looping over set point values and setting a QCoDeS parameter to this value at
    each iteration

    Parameters
    ----------
    parameter: qcodes.StandardParameter
    point_function: callable
        A callable of two parameters: station, namespace, returning an iterator. Unrolling this iterator returns to
        us set values of the parameter
    """

    @staticmethod
    def log_format(parameter, set_value):
        return OrderedDict({parameter.label: {
            "unit": parameter.unit,
            "value": set_value,
            "independent_parameter": True
        }})

    def __init__(self, parameter, point_function):
        self._parameter = parameter
        self._point_function = point_function
        super().__init__()

    def _setter_factory(self):
        for set_value in self._point_function(self._station, self._namespace):
            self._parameter.set(set_value)
            yield ParameterSweep.log_format(self._parameter, set_value)


class FunctionSweep(BaseSweepObject):
    """
    Sweep independent parameters by looping over set point values and calling a set function

    Parameters
    ----------
    set_function: callable
        A callable of three parameters: station, namespace, set_value. This returns a dictionary containing arbitrary
        information about the value set and any measurements performed (or it can contain any information that needs to
        be added in the final dataset
    point_function: callable
        A callable of two parameters: station, namespace, returning an iterator. Unrolling this iterator returns to
        us set values of the parameter
    """
    def __init__(self, set_function, point_function):
        self._set_function = set_function
        self._point_function = point_function
        super().__init__()

    def _setter_factory(self):
        for set_value in self._point_function(self._station, self._namespace):
            yield self._set_function(self._station, self._namespace, set_value)


class NestedSweep(BaseSweepObject):
    """
    Nest multiple sweep objects. This is for example very useful when performing two or higher dimensional scans
    (e.g. sweep two gate voltages and measure a current at each coordinate (gate1, gate2).

    Parameters
    ----------
    sweep_objects: list, BaseSweepObject
        The first sweep object in the list represents the inner most loop

    Notes
    -----
    We produce a nested sweep object of arbitrary depth by first defining a function which nests just two sweep objects

        product = two_product(so1, so2)

    A third order nest is then achieved like so:

        product = two_product(so1, two_product(so2, so3))

    A fourth order by

        product = two_product(so1, two_product(so2, two_product(so3, so4)))

    Etc...
    """
    def __init__(self, sweep_objects):
        self._sweep_objects = sweep_objects
        super().__init__()

    @staticmethod
    def _two_product(sweep_object1, sweep_object2):
        """
        Parameters
        ----------
        sweep_object1: BaseSweepObject
        sweep_object2: BaseSweepObject

        Returns
        -------
        BaseSweepObject
        """
        def inner():
            for result2 in sweep_object2:
                for result1 in sweep_object1:
                    result1.update(result2)
                    yield result1

        return IteratorSweep(inner)

    def _setter_factory(self):
        prod = self._sweep_objects[0]
        for so in self._sweep_objects[1:]:
            prod = NestedSweep._two_product(prod, so)

        return prod

    def set_station(self, station):
        """
        We need to pass on the station to the sweep objects in the nest

        Parameter
        ---------
        station: qcodes.Station
        """
        self._station = station
        for so in self._sweep_objects:
            so.set_station(station)
        return self

    def set_namespace(self, namespace):
        """
        We need to pass on the namespace to the sweep objects in the nest

        Parameter
        ---------
        namespace: pysweep.Namespace
        """
        self._namespace = namespace
        for so in self._sweep_objects:
            so.set_namespace(namespace)
        return self


class ZipSweep(BaseSweepObject):
    """
    Zip multiple sweep objects. Unlike a nested sweep, we will produce a 1D sweep

    Parameters
    ----------
    sweep_objects: list, BaseSweepObject
    """
    def __init__(self, sweep_objects):
        self._sweep_objects = sweep_objects
        super().__init__()

    @staticmethod
    def _combine_dictionaries(dictionaries):
        combined = {}
        for d in dictionaries:
            combined.update(d)
        return combined

    def _setter_factory(self):
        for results in zip(*self._sweep_objects):
            yield ZipSweep._combine_dictionaries(results)

    def set_station(self, station):
        """
        We need to pass on the station to the sweep objects in the nest

        Parameter
        ---------
        station: qcodes.Station
        """
        self._station = station
        for so in self._sweep_objects:
            so.set_station(station)
        return self

    def set_namespace(self, namespace):
        """
        We need to pass on the namespace to the sweep objects in the nest

        Parameter
        ---------
        namespace: pysweep.Namespace
        """
        self._namespace = namespace
        for so in self._sweep_objects:
            so.set_namespace(namespace)
        return self


class TimeTrace(BaseSweepObject):
    """
    Make a "time sweep", that is, take a time trace

    Parameter
    ---------
    measure: callable
        callable of arguments  station, namespace, returning a dictionary with measurement results.
    delay: float
        The time in seconds between calling the measure function
    total_time: float
        The total duration of the time trace
    """
    def __init__(self, measure, delay, total_time):
        self._measure = measure
        self._delay = delay
        self._total_time = total_time
        super().__init__()

    def _setter_factory(self):
        t0 = time.time()
        t = t0
        while t - t0 < self._total_time:
            msg = self._measure(self._station, self._namespace)
            time_msg = {"time": {"unit": "s", "value": t, "independent_parameter": True}}
            msg.update(time_msg)
            yield msg
            time.sleep(self._delay)
            t = time.time()

# --------------  Sweep Factories ----------------------------------------------------------------------------


def sweep(obj, sweep_points):
    """
    A convenience function to create a 1D sweep object

    Parameters
    ----------
    obj: qcodes.StandardParameter or callable
        If callable, it shall be a callable of three parameters: station, namespace, set_value and shall return a
        dictionary
    sweep_points: iterable or callable returning a iterable
        If callable, it shall be a callable of two parameters: station, namespace and shall return an iterable

    Returns
    -------
    FunctionSweep or ParameterSweep
    """

    if not callable(sweep_points):
        point_function = lambda station, namespace: sweep_points
    else:
        point_function = sweep_points

    if not isinstance(obj, qcodes.StandardParameter):
        if not callable(obj):
            raise ValueError("The object to sweep over needs to either be a QCoDeS parameter or a function")

        return FunctionSweep(obj, point_function)
    else:
        return ParameterSweep(obj, point_function)


def nested_sweep(*sweep_objects):
    """
    A convenience function to make nested sweeps

    Parameters
    ----------
    sweep_objects: list, BaseSweepObject
    """
    return NestedSweep(sweep_objects)


def zip_sweep(*sweep_objects):
    """
    A convenience function to make a zipped sweep

    Parameters
    ----------
    sweep_objects: list, BaseSweepObject
    """
    return ZipSweep(sweep_objects)


def time_trace(measure, delay, total_time):
    return TimeTrace(measure, delay, total_time)