"""
A sweep object allows us to quickly express a measurement where we loop over independent experimental parameters and
perform measurements at different phases in the loop: either after the start of a loop, after at the end of it, or after
each of the set points in the sweep.
"""
import time
from functools import partial
from collections import OrderedDict

import qcodes


class BaseSweepObject:
    """
    A sweep object is defined as follows:
    1) It is iterable and looping over a sweep object shall result in independent measurement parameters being set
    at each iteration
    2) At each iteration a dictionary is returned containing information about the parameters set and measurements that
    have been performed. Note that in general, the number of iterations is equal to the number of set points, except
    for the case where the "after_end" measurement function returns a non-empty dictionary. In the latter case, the
    number of iterations is equal to the number of set points, plus one. The last iteration returns the result of the
    after_end measurement.
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
        self._after_end_msg = dict()
        self.is_top_level = True  # Note that "top_level" is NOT the same as the outer most sweep object in a nested
        # sweep. When we create a compound sweep object (e.g. a nest or a zip), this compound object becomes the top
        # level object.

        self._measure_functions = {
            "after_each": [],
            "after_start": [],
            "after_end": []
        }

    def _get_end_measurement_message(self):
        """
        This is an interface to access the results of the "after_end" measurement results.

        Returns
        -------
        msg: dict
        """
        msg = OrderedDict(self._after_end_msg)
        self._after_end_msg = OrderedDict()
        return msg

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
            after_each_msg = self._execute_measure_function("after_each")
            main_msg.update(after_each_msg)

            if start:
                self._execute_measure_function("after_start")
                start = False

            if self.is_top_level:
                after_end_msg = self._get_end_measurement_message()
                main_msg.update(after_end_msg)

            yield main_msg

        self._after_end_msg.update(self._execute_measure_function("after_end"))

        # In principle we want the result of the after_end measurement to be yielded at the end. However,
        # we only want to do this if we are at the top level. If this behavior would be displayed in one of the sub
        # sweep object in e.g. a nest, the lower lying nest objects would multiply over this yield, with disastrous
        # consequences.
        if self.is_top_level:
            after_end_msg = self._get_end_measurement_message()
            if after_end_msg != OrderedDict():
                yield after_end_msg

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

    def after_each(self, func, **kwargs):
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
        self._measure_functions["after_each"].append(partial(func, **kwargs))
        return self

    def after_start(self, func, **kwargs):
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
        self._measure_functions["after_start"].append(partial(func, **kwargs))
        return self

    def after_end(self, func, **kwargs):
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
        self._measure_functions["after_end"].append(partial(func, **kwargs))
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


class CompoundSweep(BaseSweepObject):
    """
    A compound sweep object is composed to multiple sweep objects. Examples are a nested sweep or a zipped sweep.
    This is also an abstract class.

    Parameters
    ----------
    sweep_objects: list, BaseSweepObject
    """

    def __init__(self, sweep_objects):
        for so in sweep_objects:
            so.is_top_level = False

        self._sweep_objects = sweep_objects
        super().__init__()

    def _get_end_measurement_message(self):
        """
        Make sure the end measurement results of the sub sweep objects are accessible from the top level interface

        Returns
        -------
        msgs: dict
            A dictionary containing measurement results.
        """
        msgs = dict(self._after_end_msg)
        self._after_end_msg = dict()

        for so in self._sweep_objects:
            msg = so._get_end_measurement_message()
            msgs.update(msg)

        return msgs

    def set_station(self, station):
        """
        We need to pass on the station to the sweep objects in the sub sweep objects

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
        We need to pass on the namespace to the sweep objects in the sub sweep objects

        Parameter
        ---------
        namespace: pysweep.Namespace
        """
        self._namespace = namespace
        for so in self._sweep_objects:
            so.set_namespace(namespace)
        return self

    def _setter_factory(self):
        """
        When called, this method returns the param setter iterable appropriate for this measurement
        """
        raise NotImplementedError("Please subclass BaseSweepObject")

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
        if parameter._instrument is not None:  # TODO: Make a QCoDeS pull request to access this through a public
            # interface
            label = "{}_{}".format(parameter._instrument.name, parameter.label)
        else:
            label = parameter.label

        return OrderedDict({label: {
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


class NestedSweep(CompoundSweep):
    """
    Nest multiple sweep objects. This is for example very useful when performing two or higher dimensional scans
    (e.g. sweep two gate voltages and measure a current at each coordinate (gate1, gate2).

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
            prod = self._two_product(prod, so)

        return prod


class ZipSweep(CompoundSweep):
    """
    Zip multiple sweep objects. Unlike a nested sweep, we will produce a 1D sweep
    """
    @staticmethod
    def _combine_dictionaries(dictionaries):
        combined = {}
        for d in dictionaries:
            combined.update(d)
        return combined

    def _setter_factory(self):
        for results in zip(*self._sweep_objects):
            yield ZipSweep._combine_dictionaries(results)


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
