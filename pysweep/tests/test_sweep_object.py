import os
import time

import pysweep
import pysweep.utils
from pysweep.sweep_object import sweep, nested_sweep, zip_sweep, BaseSweepObject, ParameterSweep

from .testing_utilities import sorted_dict, StdIOMock, ParameterFactory, SweepValuesFactory

param_log_format = ParameterSweep.log_format


def equivalence_test(test_function, compare_function):

    def measure(station, namespace):
        hs = hash(str(stdio_mock))
        if not hasattr(namespace, "measurements"):
            namespace.measurement = [hs]
        else:
            namespace.measurement.append(hs)

        stdio_mock.write("measurement returns {}".format(hs))
        return {"some measurement": hs}

    stdio_mock = StdIOMock()
    args = (ParameterFactory(stdio_mock), SweepValuesFactory(), stdio_mock, measure, pysweep.Namespace())

    test_out = test_function(*args)
    stdio_mock.flush()
    compare_out = compare_function(*args)

    assert test_out == compare_out


def test_sanity():

    # Test that this ...
    def test(params, values, stdio, measure, namespace):
        for i in sweep(params[0], values[0]):
            stdio.write(sorted_dict(i))

        return str(stdio)

    # Is equivalent to this
    def compare(params, values, stdio, measure, namespace):
        for value in values[0]:
            params[0].set(value)
            dct = sorted_dict(param_log_format(params[0], value))
            stdio.write(dct)

        return str(stdio)

    equivalence_test(test, compare)


def test_product():

    def test(params, values, stdio, measure, namespace):

        param1, param2, param3, param4 = params[:4]
        sweep_values1, sweep_values2, sweep_values3, sweep_values4 = values[:4]

        for i in nested_sweep(
            sweep(param1, sweep_values1),
            sweep(param2, sweep_values2),
            sweep(param3, sweep_values3),
            sweep(param4, sweep_values4),
        ):
            stdio.write(sorted_dict(i))

        return str(stdio)

    def compare(params, values, stdio, measure, namespace):

        param1, param2, param3, param4 = params[:4]
        sweep_values1, sweep_values2, sweep_values3, sweep_values4 = values[:4]

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

                        dct = sorted_dict([
                            param_log_format(p, value) for p, value in zip(params, values)])

                        stdio.write(dct)

        return str(stdio)

    equivalence_test(test, compare)


def test_after_each():

    def test(params, values, stdio, measure, namespace):

        param1, param2, param3, param4 = params[:4]
        sweep_values1, sweep_values2, sweep_values3, sweep_values4 = values[:4]

        for i in nested_sweep(
                sweep(param1, sweep_values1),
                sweep(param2, sweep_values2),
                sweep(param3, sweep_values3).after_each(measure).set_namespace(namespace),
                sweep(param4, sweep_values4),
        ):
            stdio.write(sorted_dict(i))

        return str(stdio)

    def compare(params, values, stdio, measure, namespace):

        param1, param2, param3, param4 = params[:4]
        sweep_values1, sweep_values2, sweep_values3, sweep_values4 = values[:4]

        for value4 in sweep_values4:
            param4.set(value4)
            for value3 in sweep_values3:

                param3.set(value3)
                measure_dict = measure(None, namespace)

                for value2 in sweep_values2:
                    param2.set(value2)
                    for value1 in sweep_values1:
                        param1.set(value1)

                        values = [value1, value2, value3, value4]
                        params = [param1, param2, param3, param4]

                        dct = sorted_dict([
                            param_log_format(p, value) for p, value in zip(params, values)])

                        dct.update(measure_dict)
                        stdio.write(dct)

        return str(stdio)

    equivalence_test(test, compare)


def test_before_each():
    """
    Some measurements are less trivial to implement with pysweep, including performing a measurement right before
    setting a parameter
    """

    # Test that this ...
    def test(params, values, stdio, measure, namespace):

        def wrapped(station, nspace, value):
            measure(None, nspace)
            params[0].set(value)
            return {params[0].label: {"unit": params[0].unit, "value": value}}

        for i in sweep(wrapped, values[0]).set_namespace(namespace):
            stdio.write(sorted_dict(i))

        return str(stdio)

    # Is equivalent to this
    def compare(params, values, stdio, measure, namespace):
        for value in values[0]:
            measure(None, namespace)
            params[0].set(value)
            dct = sorted_dict({params[0].label: {"unit": params[0].unit, "value": value}})
            stdio.write(dct)

        return str(stdio)

    equivalence_test(test, compare)


def test_after_end():

    def test(params, values, stdio, measure, namespace):

        param1, param2, param3, param4 = params[:4]
        sweep_values1, sweep_values2, sweep_values3, sweep_values4 = values[:4]

        for i in nested_sweep(
                sweep(param1, sweep_values1),
                sweep(param2, sweep_values2),
                sweep(param3, sweep_values3).after_end(measure).set_namespace(namespace),
                sweep(param4, sweep_values4),
        ):
            stdio.write(sorted_dict(i))

        return str(stdio)

    def compare(params, values, stdio, measure, namespace):

        param1, param2, param3, param4 = params[:4]
        sweep_values1, sweep_values2, sweep_values3, sweep_values4 = values[:4]

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

                        dct = sorted_dict([
                            param_log_format(p, value) for p, value in zip(params, values)])

                        stdio.write(dct)

        measure(None, namespace)  # Notice that we need to run measure at the very end again.

        return str(stdio)

    equivalence_test(test, compare)


def test_after_end_msg():

    def test(params, values, stdio, measure, namespace):

        p1, p2 = params[:2]
        values1, values2 = values[:2]
        so1 = sweep(p1, values1)
        so2 = sweep(p2, values2).after_end(measure).set_namespace(namespace)

        so3 = nested_sweep(so2, so1)

        for i in so3:
            msg = so3.get_end_measurement_message()
            if msg != dict():
                stdio.write(msg)

        stdio.write(so3.get_end_measurement_message())

        return str(stdio)

    def compare(params, values, stdio, measure, namespace):

        p1, p2 = params[:2]
        values1, values2 = values[:2]
        so1 = sweep(p1, values1)
        so2 = sweep(p2, values2).after_end(measure).set_namespace(namespace)

        for i in so1:
            msg = so2.get_end_measurement_message()
            for j in so2:
                if msg != dict():
                    stdio.write(msg)
                    msg = dict()

        stdio.write(so2.get_end_measurement_message())

        return str(stdio)

    equivalence_test(test, compare)


def test_after_end_msg_top_level():

    def test(params, values, stdio, measure, namespace):

        p1, p2 = params[:2]
        values1, values2 = values[:2]
        so1 = sweep(p1, values1)
        so2 = sweep(p2, values2)

        so3 = nested_sweep(so2, so1).after_end(measure).set_namespace(namespace)

        for i in so3:
           pass

        stdio.write(so3.get_end_measurement_message())

        return str(stdio)

    def compare(params, values, stdio, measure, namespace):

        p1, p2 = params[:2]
        values1, values2 = values[:2]
        so1 = sweep(p1, values1).after_end(measure).set_namespace(namespace)
        so2 = sweep(p2, values2)

        for i in so1:
            for j in so2:
                pass

        stdio.write(so1.get_end_measurement_message())

        return str(stdio)

    equivalence_test(test, compare)


def test_after_start():

    def test(params, values, stdio, measure, namespace):

        param1, param2, param3, param4 = params[:4]
        sweep_values1, sweep_values2, sweep_values3, sweep_values4 = values[:4]

        for i in nested_sweep(
                sweep(param1, sweep_values1),
                sweep(param2, sweep_values2),
                sweep(param3, sweep_values3).after_start(measure).set_namespace(namespace),
                sweep(param4, sweep_values4),
        ):
            stdio.write(sorted_dict(i))

        return stdio

    def compare(params, values, stdio, measure, namespace):

        param1, param2, param3, param4 = params[:4]
        sweep_values1, sweep_values2, sweep_values3, sweep_values4 = values[:4]

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

                        dct = sorted_dict([
                            param_log_format(p, value) for p, value in zip(params, values)])
                        stdio.write(dct)

        return stdio

    equivalence_test(test, compare)


def test_zip():

    def test(params, values, stdio, measure, namespace):

        param1, param2, param3, param4 = params[:4]
        sweep_values1, sweep_values2, sweep_values3, sweep_values4 = values[:4]

        for i in zip_sweep(
            sweep(param1, sweep_values1),
            sweep(param2, sweep_values2),
            sweep(param3, sweep_values3),
            sweep(param4, sweep_values4),
        ):
            stdio.write(sorted_dict(i))

        return stdio

    def compare(params, values, stdio, measure, namespace):

        param1, param2, param3, param4 = params[:4]
        sweep_values1, sweep_values2, sweep_values3, sweep_values4 = values[:4]

        for value1, value2, value3, value4 in zip(sweep_values1, sweep_values2, sweep_values3, sweep_values4):
            param1.set(value1)
            param2.set(value2)
            param3.set(value3)
            param4.set(value4)

            values = [value1, value2, value3, value4]
            params = [param1, param2, param3, param4]

            dct = sorted_dict([
                param_log_format(p, value) for p, value in zip(params, values)])
            stdio.write(dct)

        return stdio

    equivalence_test(test, compare)


def test_product_zip():

    def test(params, values, stdio, measure, namespace):

        param1, param2, param3, param4 = params[:4]
        sweep_values1, sweep_values2, sweep_values3, sweep_values4 = values[:4]

        # Test that this ...
        for i in nested_sweep(
            zip_sweep(
                sweep(param1, sweep_values1),
                sweep(param2, sweep_values2)
            ),
            zip_sweep(
                sweep(param3, sweep_values3),
                sweep(param4, sweep_values4)
            )
        ):
            stdio.write(sorted_dict(i))

        return stdio

    def compare(params, values, stdio, measure, namespace):

        param1, param2, param3, param4 = params[:4]
        sweep_values1, sweep_values2, sweep_values3, sweep_values4 = values[:4]

        # Is equivalent to this
        for value3, value4 in zip(sweep_values3, sweep_values4):
            param3.set(value3)
            param4.set(value4)
            for value1, value2 in zip(sweep_values1, sweep_values2):
                param1.set(value1)
                param2.set(value2)

                values = [value1, value2, value3, value4]
                params = [param1, param2, param3, param4]

                dct = sorted_dict([
                    param_log_format(p, value) for p, value in zip(params, values)])
                stdio.write(dct)

        return stdio

    equivalence_test(test, compare)


def test_zip_product():

    def test(params, values, stdio, measure, namespace):

        param1, param2, param3, param4 = params[:4]
        sweep_values1, sweep_values2, sweep_values3, sweep_values4 = values[:4]

        for i in zip_sweep(
            nested_sweep(
                sweep(param1, sweep_values1),
                sweep(param2, sweep_values2)
            ),
            nested_sweep(
                sweep(param3, sweep_values3),
                sweep(param4, sweep_values4)
            )
        ):
            stdio.write(sorted_dict(i))

        return stdio

    def compare(params, values, stdio, measure, namespace):

        param1, param2, param3, param4 = params[:4]
        sweep_values1, sweep_values2, sweep_values3, sweep_values4 = values[:4]

        def gen1():
            for value2 in sweep_values2:
                param2.set(value2)
                for value1 in sweep_values1:
                    param1.set(value1)

                    values = [value1, value2]
                    params = [param1, param2]

                    dct = sorted_dict([
                        param_log_format(p, value) for p, value in zip(params, values)])

                    yield dct

        def gen2():
            for value4 in sweep_values4:
                param4.set(value4)
                for value3 in sweep_values3:
                    param3.set(value3)

                    values = [value3, value4]
                    params = [param3, param4]

                    dct = sorted_dict([
                        param_log_format(p, value) for p, value in zip(params, values)])

                    yield dct

        for d1, d2 in zip(gen1(), gen2()):
            dct = {}
            dct.update(d1)
            dct.update(d2)
            stdio.write(sorted_dict(dct))

        return stdio

    equivalence_test(test, compare)


def test_top_level_after_end():

    def test(params, values, stdio, measure, namespace):

        param1, param2, param3, param4 = params[:4]
        sweep_values1, sweep_values2, sweep_values3, sweep_values4 = values[:4]

        # Test that this ...
        for i in nested_sweep(
            zip_sweep(
                sweep(param1, sweep_values1),
                sweep(param2, sweep_values2)
            ).after_end(measure).set_namespace(namespace),
            zip_sweep(
                sweep(param3, sweep_values3),
                sweep(param4, sweep_values4)
            )
        ):
            stdio.write(sorted_dict(i))

        return stdio

    def compare(params, values, stdio, measure, namespace):

        param1, param2, param3, param4 = params[:4]
        sweep_values1, sweep_values2, sweep_values3, sweep_values4 = values[:4]

        # Is equivalent to this
        for count, (value3, value4) in enumerate(zip(sweep_values3, sweep_values4)):
            param3.set(value3)
            param4.set(value4)

            if count > 0:
                measure(None, namespace)

            for value1, value2 in zip(sweep_values1, sweep_values2):
                param1.set(value1)
                param2.set(value2)

                values = [value1, value2, value3, value4]
                params = [param1, param2, param3, param4]

                dct = sorted_dict([
                    param_log_format(p, value) for p, value in zip(params, values)])

                stdio.write(dct)

        measure(None, namespace)

        return stdio

    equivalence_test(test, compare)


def test_set_namespace_top_level():

    def test(params, values, stdio, measure, namespace):

        param1, param2, param3, param4 = params[:4]
        sweep_values1, sweep_values2, sweep_values3, sweep_values4 = values[:4]

        for i in nested_sweep(
                sweep(param1, sweep_values1),
                sweep(param2, sweep_values2),
                sweep(param3, sweep_values3).after_each(measure),
                sweep(param4, sweep_values4),
        ).set_namespace(namespace):

            stdio.write(sorted_dict(i))

        return str(stdio)

    def compare(params, values, stdio, measure, namespace):

        param1, param2, param3, param4 = params[:4]
        sweep_values1, sweep_values2, sweep_values3, sweep_values4 = values[:4]

        for value4 in sweep_values4:
            param4.set(value4)
            for value3 in sweep_values3:

                param3.set(value3)
                measure_dict = measure(None, namespace)

                for value2 in sweep_values2:
                    param2.set(value2)
                    for value1 in sweep_values1:
                        param1.set(value1)

                        values = [value1, value2, value3, value4]
                        params = [param1, param2, param3, param4]

                        dct = sorted_dict([
                            param_log_format(p, value) for p, value in zip(params, values)])

                        dct.update(measure_dict)
                        stdio.write(dct)

        return str(stdio)

    equivalence_test(test, compare)


def test_alias():

    def log_time():
        tb = time.time()

        def inner(station, namespace):
            return {"time": {"unit": "s", "value": "{:.2}".format(time.time() - tb)}}
        return inner

    BaseSweepObject.add_alias("log_time", lambda so: so.after_each(log_time()))
    BaseSweepObject.add_alias("sleep", lambda so, t: so.after_each(pysweep.utils.sleep(t)))

    def test(params, values, stdio, measure, namespace):
        param1 = params[0]
        sweep_values1 = values[0]

        for i in sweep(param1, sweep_values1).sleep(.1).log_time():
            stdio.write(i)

        return stdio

    def compare(params, values, stdio, measure, namespace):
        param1 = params[0]
        sweep_values1 = values[0]

        time_logger = log_time()
        for value in sweep_values1:
            param1.set(value)
            time.sleep(.1)
            d = param_log_format(param1, value)
            d.update(time_logger(None, None))
            stdio.write(d)

        return stdio

    equivalence_test(test, compare)

