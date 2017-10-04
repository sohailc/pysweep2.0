from collections import OrderedDict

import pysweep
from pysweep.sweep_object import sweep_object, sweep_product
import qcodes


class StdIOMock:
    def __init__(self):
        self._buffer = ""

    def print(self, value):
        self._buffer += "\n" + str(value)

    def __repr__(self):
        return self._buffer

    def flush(self):
        self._buffer = ""


def make_parameter(label, std_out):
    def setter(v):
        std_out.print("setting {} to {}".format(label, v))

    return qcodes.StandardParameter(label, set_cmd=setter, units="V")


def merge_dicts(dicts):
    merged_dict = {}
    for d in dicts:
        for k, v in d.items():
            merged_dict[k] = v
    return merged_dict


def sorted_dict(dct):
    return OrderedDict(sorted(dct.items(), key=lambda t: t[0]))


def test_sanity():
    param_label = "param1"
    values = [1, 2]

    std_out = StdIOMock()
    param = make_parameter(param_label, std_out)

    # Test that this ...
    for i in sweep_object(param, values):
        std_out.print(sorted_dict(i))

    test_out = str(std_out)
    std_out.flush()

    # Is equivalent to this
    for value in values:
        param.set(value)
        dct = sorted_dict({param.label: {"unit": param.units, "value": value}})
        std_out.print(dct)

    compare_out = str(std_out)
    assert test_out == compare_out


def test_product():

    std_out = StdIOMock()
    param1 = make_parameter("label1", std_out)
    param2 = make_parameter("label2", std_out)
    param3 = make_parameter("label3", std_out)
    param4 = make_parameter("label4", std_out)

    sweep_values1 = [1, 2]
    sweep_values2 = [1, 2, 3]
    sweep_values3 = [0, 1, 2]
    sweep_values4 = range(100)

    # Test that this ...
    for i in sweep_product(
        sweep_object(param1, sweep_values1),
        sweep_object(param2, sweep_values2),
        sweep_object(param3, sweep_values3),
        sweep_object(param4, sweep_values4),
    ):
        std_out.print(sorted_dict(i))

    test_out = str(std_out)
    std_out.flush()

    # Is equivalent to this
    for value4 in sweep_values4:
        param4.set(value4)
        for value3 in sweep_values3:
            param3.set(value3)
            for value2 in sweep_values2:
                param2.set(value2)
                for value1 in sweep_values1:
                    param1.set(value1)

                    values = [value1, value2, value3, value4]
                    params = [param1, param2, param3, param4]

                    dct = sorted_dict({p.label: {"unit": p.units, "value": value} for p, value in zip(params, values)})
                    std_out.print(dct)

    compare_out = str(std_out)
    assert test_out == compare_out


def test_after_each():

    def measure(station, namespace):
        return {"some measurement": hash(str(std_out))}

    std_out = StdIOMock()
    param1 = make_parameter("label1", std_out)
    param2 = make_parameter("label2", std_out)
    param3 = make_parameter("label3", std_out)
    param4 = make_parameter("label4", std_out)

    sweep_values1 = [1, 2]
    sweep_values2 = [1, 2, 3]
    sweep_values3 = [0, 1, 2]
    sweep_values4 = [0, 1]

    # Test that this ...
    for i in sweep_product(
            sweep_object(param1, sweep_values1),
            sweep_object(param2, sweep_values2),
            sweep_object(param3, sweep_values3).after_each(measure),
            sweep_object(param4, sweep_values4),
    ):
        std_out.print(sorted_dict(i))

    test_out = str(std_out)
    std_out.flush()

    # Is equivalent to this
    for value4 in sweep_values4:
        param4.set(value4)
        for value3 in sweep_values3:

            param3.set(value3)
            measure_dict = measure(None, None)

            for value2 in sweep_values2:
                param2.set(value2)
                for value1 in sweep_values1:
                    param1.set(value1)

                    values = [value1, value2, value3, value4]
                    params = [param1, param2, param3, param4]

                    dct = sorted_dict({p.label: {"unit": p.units, "value": value} for p, value in zip(params, values)})
                    dct.update(measure_dict)
                    std_out.print(dct)

    compare_out = str(std_out)
    assert test_out == compare_out


def test_after_end():

    def measure(station, ns):
        if not hasattr(ns, "measurements"):
            ns.measurement = [hash(str(std_out))]
        else:
            ns.measurement.append(hash(str(std_out)))

        return {}

    std_out = StdIOMock()
    namespace = pysweep.Namespace
    param1 = make_parameter("label1", std_out)
    param2 = make_parameter("label2", std_out)
    param3 = make_parameter("label3", std_out)
    param4 = make_parameter("label4", std_out)

    sweep_values1 = [1, 2]
    sweep_values2 = [1, 2, 3]
    sweep_values3 = [0, 1, 2]
    sweep_values4 = [0, 1]

    # Test that this ...
    for i in sweep_product(
            sweep_object(param1, sweep_values1),
            sweep_object(param2, sweep_values2),
            sweep_object(param3, sweep_values3).after_end(measure).set_namespace(namespace),
            sweep_object(param4, sweep_values4),
    ):
        std_out.print(sorted_dict(i))

    test_out = namespace.measurement
    namespace = pysweep.Namespace  # A fresh namespace
    std_out.flush()

    # Is equivalent to this
    for count, value4 in enumerate(sweep_values4):
        if count > 0:
            measure(None, namespace)

        param4.set(value4)
        for value3 in sweep_values3:
            param3.set(value3)

            for value2 in sweep_values2:
                param2.set(value2)
                for value1 in sweep_values1:
                    param1.set(value1)

                    values = [value1, value2, value3, value4]
                    params = [param1, param2, param3, param4]

                    dct = sorted_dict({p.label: {"unit": p.units, "value": value} for p, value in zip(params, values)})
                    std_out.print(dct)

    measure(None, namespace)  # Notice that we need to run measure at the very end again.
    compare_out = namespace.measurement
    assert all([i == j for i,j in zip(test_out, compare_out)])


def test_after_start():

    def measure(station, ns):
        if not hasattr(ns, "measurements"):
            ns.measurement = [hash(str(std_out))]
        else:
            ns.measurement.append(hash(str(std_out)))

        return {}

    std_out = StdIOMock()
    namespace = pysweep.Namespace
    param1 = make_parameter("label1", std_out)
    param2 = make_parameter("label2", std_out)
    param3 = make_parameter("label3", std_out)
    param4 = make_parameter("label4", std_out)

    sweep_values1 = [1, 2]
    sweep_values2 = [1, 2, 3]
    sweep_values3 = [0, 1, 2]
    sweep_values4 = [0, 1]

    # Test that this ...
    for i in sweep_product(
            sweep_object(param1, sweep_values1),
            sweep_object(param2, sweep_values2),
            sweep_object(param3, sweep_values3).after_start(measure).set_namespace(namespace),
            sweep_object(param4, sweep_values4),
    ):
        std_out.print(sorted_dict(i))

    test_out = namespace.measurement
    namespace = pysweep.Namespace  # A fresh namespace
    std_out.flush()

    # Is equivalent to this
    for value4 in sweep_values4:
        param4.set(value4)
        start = True

        for value3 in sweep_values3:
            param3.set(value3)

            if start:
                measure(None, namespace)
                start = False

            for value2 in sweep_values2:
                param2.set(value2)

                for value1 in sweep_values1:
                    param1.set(value1)

                    values = [value1, value2, value3, value4]
                    params = [param1, param2, param3, param4]

                    dct = sorted_dict({p.label: {"unit": p.units, "value": value} for p, value in zip(params, values)})
                    std_out.print(dct)

    compare_out = namespace.measurement
    assert all([i == j for i,j in zip(test_out, compare_out)])
