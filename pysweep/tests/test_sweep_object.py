from collections import OrderedDict

from pysweep import Namespace
from pysweep.sweep_object import SweepObject, SweepProduct
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

    # Test that this ...
    std_out = StdIOMock()
    param = make_parameter(param_label, std_out)
    for i in SweepObject(param, values):
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

    param_labels = ["param1", "param2", "param3"]
    param_values = [[1, 2], [9, 10, 2], range(100)]

    # Test that this ...
    std_out = StdIOMock()
    params = [make_parameter(param_label, std_out) for param_label in param_labels]
    sweep_objects = [SweepObject(test_param, values) for test_param, values in zip(params, param_values)]

    for i in SweepProduct(sweep_objects):
        std_out.print(sorted_dict(i))

    test_out = str(std_out)
    std_out.flush()

    # Is equivalent to this
    for value3 in param_values[2]:
        params[2].set(value3)
        for value2 in param_values[1]:
            params[1].set(value2)
            for value1 in param_values[0]:
                params[0].set(value1)
                values = [value1, value2, value3]

                dct = sorted_dict({p.label: {"unit": p.units, "value": value} for p, value in zip(params, values)})
                std_out.print(dct)

    compare_out = str(std_out)
    assert test_out == compare_out


def test_after_each():

    def measure(station, namespace):
        return {"some measurement": hash(str(std_out))}

    std_out = StdIOMock()
    param1 = make_parameter("param1", std_out)
    param2 = make_parameter("param2", std_out)
    param3 = make_parameter("param3", std_out)

    range1 = [3, 1]
    range2 = [1, 2]
    range3 = [7, 10]
    test_out = []

    # Test that this ...
    for i in SweepProduct([
        SweepObject(param1, range1),
        SweepObject(param2, range2).after_each(measure),
        SweepObject(param3, range3)
    ]):
        test_out.append(i)

    std_out.flush()
    compare_out = []

    # Is equivalent to this
    for value3 in range3:
        param3.set(value3)
        out_dict3 = {param3.label: {"unit": param3.units, "value": value3}}
        for value2 in range2:

            param2.set(value2)
            out_dict2 = {param2.label: {"unit": param2.units, "value": value2}}
            measure_dict = measure(None, None)  # Notice that the measurement is called after setting param2

            for value1 in range1:
                param1.set(value1)
                out_dict1 = {param1.label: {"unit": param1.units, "value": value1}}
                compare_out.append(merge_dicts([out_dict1, out_dict2, out_dict3, measure_dict]))

    assert all([test == compare for test, compare in zip(test_out, compare_out)])


def test_before_each():

    def measure(station, namespace):
        return {"some measurement": hash(str(std_out))}

    std_out = StdIOMock()
    param1 = make_parameter("param1", std_out)
    param2 = make_parameter("param2", std_out)
    param3 = make_parameter("param3", std_out)

    range1 = [3, 1]
    range2 = [1, 2]
    range3 = [7, 10]
    test_out = []

    # Test that this ...
    for i in SweepProduct([
        SweepObject(param1, range1),
        SweepObject(param2, range2).before_each(measure),
        SweepObject(param3, range3)
    ]):
        test_out.append(i)

    std_out.flush()
    compare_out = []

    # Is equivalent to this
    for value3 in range3:
        param3.set(value3)
        out_dict3 = {param3.label: {"unit": param3.units, "value": value3}}
        for value2 in range2:

            measure_dict = measure(None, None)  # Notice that the measurement is called before setting param2
            param2.set(value2)
            out_dict2 = {param2.label: {"unit": param2.units, "value": value2}}

            for value1 in range1:
                param1.set(value1)
                out_dict1 = {param1.label: {"unit": param1.units, "value": value1}}
                compare_out.append(merge_dicts([out_dict1, out_dict2, out_dict3, measure_dict]))

    assert all([test == compare for test, compare in zip(test_out, compare_out)])


def test_after_end():

    def measure(station, namespace):
        std_out_hash = hash(str(std_out))
        if not hasattr(namespace, "std_out_hash"):
            namespace.std_out_hash = [std_out_hash]
        else:
            namespace.std_out_hash.append(std_out_hash)

        return {}

    std_out = StdIOMock()
    param1 = make_parameter("param1", std_out)
    param2 = make_parameter("param2", std_out)
    param3 = make_parameter("param3", std_out)

    range1 = [3, 1]
    range2 = [1, 2]
    range3 = [7, 10]
    sweep_objects = []
    namespace = Namespace()

    for param, range in zip([param1, param2, param3], [range1, range2, range3]):
        sweep_object = SweepObject(param, range)
        sweep_object.set_namespace(namespace)
        sweep_objects.append(sweep_object)

    sweep_objects[1] = sweep_objects[1].after_end(measure)

    # Test that this ...
    for _ in SweepProduct(sweep_objects):
        pass

    std_out.flush()
    hashes_test = namespace.std_out_hash
    namespace = Namespace()  # A fresh namespace

    # Is equivalent to this
    for count, value3 in enumerate(range3):
        if count != 0:
            measure(None, namespace)  # After the end of the sweep of parameter 2, we will begin the sweep of
            # parameter 3, except at the start of our measurement.

        param3.set(value3)

        for value2 in range2:
            param2.set(value2)

            for value1 in range1:
                param1.set(value1)

    measure(None, namespace)  # At the end of the measurement (that is, after the end of the sweep of parameter 3)
    # the measure function will be called again.

    hashes_compare = namespace.std_out_hash
    assert all([i == j for i, j in zip(hashes_test, hashes_compare)])


def test_after_start():

    def measure(station, namespace):
        std_out_hash = hash(str(std_out))
        if not hasattr(namespace, "std_out_hash"):
            namespace.std_out_hash = [std_out_hash]
        else:
            namespace.std_out_hash.append(std_out_hash)

        return {}

    std_out = StdIOMock()
    param1 = make_parameter("param1", std_out)
    param2 = make_parameter("param2", std_out)
    param3 = make_parameter("param3", std_out)

    range1 = [3, 1]
    range2 = [1, 2]
    range3 = [7, 10]
    sweep_objects = []
    namespace = Namespace()

    for param, range in zip([param1, param2, param3], [range1, range2, range3]):
        sweep_object = SweepObject(param, range)
        sweep_object.set_namespace(namespace)
        sweep_objects.append(sweep_object)

    sweep_objects[1] = sweep_objects[1].after_start(measure)

    # Test that this ...
    for _ in SweepProduct(sweep_objects):
        pass

    std_out.flush()
    hashes_test = namespace.std_out_hash
    namespace = Namespace()  # A fresh namespace

    # Is equivalent to this
    for value3 in range3:
        param3.set(value3)

        for count, value2 in enumerate(range2):

            if count != 0:
                measure(None, namespace)

            param2.set(value2)

            for value1 in range1:
                param1.set(value1)

    hashes_compare = namespace.std_out_hash
    assert all([i == j for i, j in zip(hashes_test, hashes_compare)])
