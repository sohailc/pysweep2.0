import pytest
import numpy as np

from qcodes import Parameter

from qsweep.convenience import sweep, measure
from qsweep.decorators import getter, setter

from ._test_tools import Factory


@pytest.fixture()
def parameters():
    def create_param(name):
        return Parameter(name, set_cmd=None, get_cmd=None)

    return Factory(create_param)


@pytest.fixture()
def sweep_functions():
    def create_function(name):

        @setter((name, ""))
        def sweep_function(value):
            pass

        return sweep_function

    return Factory(create_function)


def test_sanity_sweep_parameter(parameters):
    p = parameters["p"]
    values = [0, 1, 2]
    so = sweep(p, values)
    assert list(so) == [{"p": value} for value in values]
    assert 'numeric' == so.parameter_table.param_specs[0].type


def test_label(parameters):
    p = parameters["p"]
    p.label = "my cool label"
    values = [0, 1, 2]
    so = sweep(p, values)
    assert list(so) == [{"p": value} for value in values]
    assert 'numeric' == so.parameter_table.param_specs[0].type
    assert "my cool label" == so.parameter_table.param_specs[0].label


def test_sanity_sweep_parameter_w_step_count(parameters):
    p = parameters["p"]
    start = 1
    stop = 3
    step_count = 10
    values = np.linspace(start, stop, step_count)
    so = sweep(p, start=start, stop=stop, step_count=step_count)
    assert list(so) == [{"p": value} for value in values]
    assert 'numeric' == so.parameter_table.param_specs[0].type


def test_sweep_parameter_with_paramtype(parameters):
    p = parameters["p"]
    values = [0, 1, 2]
    so = sweep(p, values, paramtype='array')
    assert list(so) == [{"p": value} for value in values]
    assert 'array' == so.parameter_table.param_specs[0].type


def test_sanity_measure_parameter(parameters):
    pval = 12
    p = Parameter('p', set_cmd=False, get_cmd=lambda: pval)

    so = measure(p)

    assert list(so) == [{"p": pval}]
    assert 'numeric' == so.parameter_table.param_specs[0].type


def test_measure_parameter_with_paramtype(parameters):
    pval = 12
    p = Parameter('p', set_cmd=False, get_cmd=lambda: pval)

    so = measure(p, paramtype='array')

    assert list(so) == [{"p": pval}]
    assert 'array' == so.parameter_table.param_specs[0].type


def test_sanity_sweep_setter_function(sweep_functions):
    p = sweep_functions["p"]
    values = [0, 1, 2]
    so = sweep(p, values)
    assert list(so) == [{"p": value} for value in values]
    assert 'numeric' == so.parameter_table.param_specs[0].type


def test_sanity_sweep_getter_function(sweep_functions):
    qval = 123

    @getter(('q', ""))
    def measure_function():
        return qval

    p = sweep_functions["p"]
    values = [0, 1, 2]
    so = sweep(p, values)(
        measure(measure_function)
    )
    assert list(so) == [{"p": value, "q": qval} for value in values]
    assert 'numeric' == so.parameter_table.param_specs[0].type
    assert 'numeric' == so.parameter_table.param_specs[1].type


def test_error():
    """
    Setter functions need to be decorated with `setter`
    """

    def no_good_setter(value):
        pass

    with pytest.raises(ValueError):
        sweep(no_good_setter, [0, 1])

