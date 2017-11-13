from .testing_utilities import equivalence_test

from pysweep.measurement import Measurement
from pysweep import sweep

Measurement.use_storage("spyview")


def test_sanity():

    def test(params, values, stdio, measure, namespace):

        p = params[0]
        setup, cleanup = measure[:2]
        sweep_values = values[0]

        measurement = Measurement(
            setup,
            cleanup,
            sweep(p, sweep_values)
        ).run(debug=True, max_buffer_size=10)

        #out = measurement.output(p.label)
        #assert out == {p.label: {"unit": p.unit, "value": list(sweep_values), "independent_parameter": True}}

        return str(stdio)

    def compare(params, values, stdio, measure, namespace):

        p = params[0]
        setup, cleanup = measure[:2]
        sweep_values = values[0]

        setup(None, namespace)
        for value in sweep_values:
            p(value)
        cleanup(None, namespace)

        return str(stdio)

    equivalence_test(test, compare)


