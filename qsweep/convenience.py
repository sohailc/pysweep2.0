from typing import Union, Iterator
import logging
import time
import numpy as np

from qcodes import Parameter
from qsweep.base import Sweep, Measure, Zip, Nest, Chain, BaseSweepObject
from qsweep.decorators import (
    parameter_setter, parameter_getter, MeasureFunction, SweepFunction
)

log = logging.getLogger()
log.setLevel(logging.INFO)


def make_setpoints_array(
    start: float,
    stop: float,
    step: float = None,
    step_count: int = None
) -> np.ndarray:
    """
    Given start, stop and step_count or step values, return a numpy array
    with set points values.

    Args:
        start
        stop
        step: The requested size of the steps. If this value
            has not been given, than `step_count` must be given.
            Please note that there need to fit an integer number
            of steps between the start and stop values. If this
            is not the case, we round of to the nearest integer
            number of steps and issue a warning that the step_value
            has changed.
        step_count: The number of steps between start and stop values.
            If this value has not been given, then `step_value` must
            be given.
    """
    def _is_none(*lst):
        return [i is None for i in lst]

    if not any(_is_none(step, step_count)):
        raise ValueError(
            "Either step or step_count need to be given, "
            "but not both"
        )

    if any(_is_none(start, stop)) or all(_is_none(step_count, step)):
        raise ValueError(
            "We need both start and stop and one of step "
            "or step_count"
        )

    if step_count is None:
        step_count = int(np.round((stop - start) / step)) + 1

    set_points, actual_step = np.linspace(
        start, stop, step_count, retstep=True
    )

    if step is not None and not np.isclose(step, actual_step, rtol=0.01):
        log.warning(
            f"Cannot set integer number of steps between "
            f"{start} and {stop} with {step} step sizes. "
            f"Changing the step size from {step} to {actual_step}"
        )

    return set_points


def sweep(
        parameter: Union[Parameter, SweepFunction],
        set_points: Iterator = None,
        start: float = None,
        stop: float = None,
        step: float = None,
        step_count: int = None,
        paramtype: str = None
) -> BaseSweepObject:
    """
    Create a sweep object which sweeps the given parameter.

    Args:
        parameter: The parameter to sweep
        set_points: The set point values to sweep over.
            If the set points are not given, the start,
            stop and step or step_count values are needed.
        start: The start value of the sweep
            This value is required if a set point iterator is not provided
        stop: The stop value of the sweep
            This value is required if a set point iterator is not provided
        step: The step size of the sweep.
            If the set point iterator is not provided, we either need this
            value or a value for `step_count`. Please note that there need
            to fit an integer number of steps between the start and stop values.
            If this is not the case, we round of to the nearest integer number
            of steps and issue a warning that the step_value has changed.
        step_count: the number of step in the sweep.
            If the set point iterator is not provided, we either need this
            value or a value for `step`.
        paramtype: ['array', 'numeric', 'text', 'complex']
            The type of parameter which is being swept. The default value
            is 'numeric'
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
        set_points = make_setpoints_array(
            start, stop, step, step_count
        )

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

