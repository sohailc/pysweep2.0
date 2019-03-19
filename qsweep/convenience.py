from typing import Union, Iterator

import time
import numpy as np

from qcodes import Parameter
from qsweep.base import Sweep, Measure, Zip, Nest, Chain, BaseSweepObject
from qsweep.decorators import (
    parameter_setter, parameter_getter, MeasureFunction, SweepFunction
)


def sweep(
        parameter: Union[Parameter, SweepFunction],
        set_points: Iterator=None,
        start: float=None,
        step: float=None,
        stop: float=None,
        paramtype: str = None
) -> BaseSweepObject:
    """
    Sweep a parameters or function over a set of points (given by the `set_points`
    iterator) or from a `start_value` to a `stop_value` with steps of `step_value`.
    """

    if isinstance(parameter, Parameter):
        fun = parameter_setter(parameter, paramtype=paramtype)
    elif isinstance(parameter, SweepFunction):
        fun = parameter
    else:
        raise ValueError(
            "Can only sweep a QCoDeS parameter or a function "
            "decorated with qsweep.setter"
        )

    if set_points is None:

        if any([i is None for i in [start, stop, step]]):
            raise ValueError(
                "If the set points iterator is None then start, stop and "
                "step values are mandatory"
            )

        set_points = np.arange(start, stop + step, step)

    if not callable(set_points):
        sweep_object = Sweep(fun, fun.parameter_table, lambda: set_points)
    else:
        sweep_object = Sweep(fun, fun.parameter_table, set_points)

    return sweep_object


def measure(fun_or_param, paramtype: str = None):

    if isinstance(fun_or_param, Parameter):
        fun = parameter_getter(fun_or_param, paramtype=paramtype)
    elif isinstance(fun_or_param, MeasureFunction):
        fun = fun_or_param
    else:
        raise ValueError("Can only measure a QCoDeS parameter or a function "
                         "decorated with pytopo.getter")

    return Measure(fun, fun.parameter_table)


def time_trace(interval_time, total_time=None, stop_condition=None):

    start_time = None   # Set when we call "generator_function"

    if total_time is None:
        if stop_condition is None:
            raise ValueError("Either specify the total time or the stop "
                             "condition")

    else:
        def stop_condition():
            global start_time
            return time.time() - start_time > total_time

    def generator_function():
        global start_time
        start_time = time.time()
        while not stop_condition():
            yield time.time() - start_time
            time.sleep(interval_time)

    time_parameter = Parameter(
        name="time", unit="s", set_cmd=None, get_cmd=None)

    return sweep(time_parameter, generator_function)


def szip(*sweep_objects):
    return Zip(*sweep_objects)


def nest(*sweep_objects):
    return Nest(*sweep_objects)


def chain(*sweep_objects):
    return Chain(*sweep_objects)

