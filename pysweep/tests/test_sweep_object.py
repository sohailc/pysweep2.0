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


def test_sanity():
    param_label = "param1"
    values = [1, 2]

    # Test that this ...
    std_out = StdIOMock()
    param = make_parameter(param_label, std_out)
    for i in SweepObject(param, values):
        std_out.print(i)

    test_out = str(std_out)
    std_out.flush()

    # Is equivalent to this
    for value in values:
        param.set(value)
        std_out.print({param.label: {"unit": param.units, "value": value}})

    compare_out = str(std_out)
    assert test_out == compare_out


def test_product():

    param_labels = ["param1", "param2"]
    param_values = [[1, 2], [9, 10, 2]]

    # Test that this ...
    std_out = StdIOMock()
    params = [make_parameter(param_label, std_out) for param_label in param_labels]
    sweep_objects = [SweepObject(test_param, values) for test_param, values in zip(params, param_values)]

    for i in SweepProduct(sweep_objects):
        std_out.print(i)

    test_out = str(std_out)
    std_out.flush()

    # Is equivalent to this
    for value2 in param_values[1]:
        params[1].set(value2)
        for value1 in param_values[0]:
            params[0].set(value1)

            values = [value1, value2]

            std_out.print(
                {p.label: {"unit": p.units, "value": value} for p, value in zip(params, values)})

    compare_out = str(std_out)
    assert test_out == compare_out


def test_product_larger():

    param_labels = ["param1", "param2", "param3"]
    param_values = [[1, 2], [9, 10, 2], range(100)]

    # Test that this ...
    std_out = StdIOMock()
    params = [make_parameter(param_label, std_out) for param_label in param_labels]
    sweep_objects = [SweepObject(test_param, values) for test_param, values in zip(params, param_values)]

    for i in SweepProduct(sweep_objects):
        std_out.print(i)

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

                std_out.print(
                    {p.label: {"unit": p.units, "value": value} for p, value in zip(params, values)})

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

    # Test that this ...
    for i in SweepProduct([
        SweepObject(param1, range1),
        SweepObject(param2, range2).after_each(measure),
        SweepObject(param3, range3)
    ]):
        std_out.print(i)

    test_out = str(std_out)
    std_out.flush()

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

                out_dict = {}
                out_dict.update(out_dict1)
                out_dict.update(out_dict2)
                out_dict.update(measure_dict)
                out_dict.update(out_dict3)
                std_out.print(out_dict)

    compare_out = str(std_out)
    assert test_out == compare_out


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

    # Test that this ...
    for i in SweepProduct([
        SweepObject(param1, range1),
        SweepObject(param2, range2).before_each(measure),
        SweepObject(param3, range3)
    ]):
        std_out.print(i)

    test_out = str(std_out)
    std_out.flush()

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

                out_dict = {}
                out_dict.update(out_dict1)
                out_dict.update(out_dict2)
                out_dict.update(measure_dict)
                out_dict.update(out_dict3)
                std_out.print(out_dict)

    compare_out = str(std_out)
    assert test_out == compare_out
