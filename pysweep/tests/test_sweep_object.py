from collections import OrderedDict
import time

import pysweep
import pysweep.utils
from pysweep.sweep_object import for_each

from .testing_utilities import sorted_dict, StdIOMock, ParameterFactory, SweepValuesFactory


def equivalence_test(test_function, compare_function):

    def measure(station, namespace):
        hs = hash(str(stdio_mock))
        if not hasattr(namespace, "measurements"):
            namespace.measurement = [hs]
        else:
            namespace.measurement.append(hs)

        stdio_mock.write("measurement returns {}".format(hs))
        return {}
        #return OrderedDict({"some measurement": hs})

    stdio_mock = StdIOMock()
    args = (ParameterFactory(stdio_mock), SweepValuesFactory(), stdio_mock, measure, pysweep.Namespace())

    test_out = test_function(*args)
    stdio_mock.flush()
    compare_out = compare_function(*args)

    assert test_out == compare_out


def test_sanity():

    def test(params, values, stdio, measure, namespace):
        for _ in for_each(params[0], values[0]):
            pass

        return str(stdio)

    def compare(params, values, stdio, measure, namespace):
        for value in values[0]:
            params[0](value)

        return str(stdio)

    equivalence_test(test, compare)


def test_nest():

    def test(params, values, stdio, measure, namespace):
        p0, p1, p2 = params[:3]
        v0, v1, v2 = [[0, 1, 2], [0, 1, 2], [0, 1, 2]]

        for _ in for_each(p0, v0)(
                for_each(p1, v1)(
                    for_each(p2, v2)
                )
        ):
            pass

        return str(stdio)

    def compare(params, values, stdio, measure, namespace):
        p0, p1, p2 = params[:3]
        v0, v1, v2 = [[0, 1, 2], [0, 1, 2], [0, 1, 2]]

        for value0 in v0:
            p0(value0)
            for value1 in v1:
                p1(value1)
                for value2 in v2:
                    p2(value2)

        return str(stdio)

    equivalence_test(test, compare)


def test_nest_function():

    def test(params, values, stdio, measure, namespace):
        p0, p1, p2 = params[:3]
        v0, v1, v2 = [[0, 1, 2], [0, 1, 2], [0, 1, 2]]

        for _ in for_each(p0, v0).set_namespace(namespace)(
                for_each(p1, v1)(
                    for_each(p2, v2),
                    measure
                )
        ):
            pass

        return str(stdio)

    def compare(params, values, stdio, measure, namespace):
        p0, p1, p2 = params[:3]
        v0, v1, v2 = [[0, 1, 2], [0, 1, 2], [0, 1, 2]]

        for value0 in v0:
            p0(value0)
            for value1 in v1:
                p1(value1)
                for value2 in v2:
                    p2(value2)
                    measure(None, namespace)

        return str(stdio)

    equivalence_test(test, compare)
