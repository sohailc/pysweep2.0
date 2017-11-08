from pysweep import Namespace
from pysweep.sweep_object import ChainSweep
from pysweep.output_formatter import DictFormatter
from pysweep.spyview import SpyviewFormatter


class Measurement:
    station = None

    @classmethod
    def attach_station(cls, station):
        cls.station = station

    @classmethod
    def set_default_formatter(cls, formatter_class, args, kwargs):
        cls.formatter_class = formatter_class
        cls.formatter_args = args
        cls.formatter_kwargs = kwargs

    @classmethod
    def get_default_formatter(cls):
        return cls.formatter_class(*cls.formatter_args, **cls.formatter_kwargs)

    @staticmethod
    def _make_list(value):
        if not isinstance(value, list):
            return [value]
        return value

    def __init__(self, setup, cleanup, sweep_objects, output_formatter=None):

        self._setup = Measurement._make_list(setup)
        self._cleanup = Measurement._make_list(cleanup)
        self._sweep_object = ChainSweep([sweep_objects])
        self._output_formatter = output_formatter or Measurement.get_default_formatter()

        self.name = None
        self._has_run = False

    def run(self):

        if self._has_run:
            raise RuntimeError("This measurement has already run. Running twice is disallowed")
        self._has_run = True

        namespace = Namespace()
        self._sweep_object.set_station(Measurement.station)
        self._sweep_object.set_namespace(namespace)

        for setup_function in self._setup:
            setup_function(Measurement.station, namespace)

        for measurement_output in self._sweep_object:
            self._output_formatter.add(measurement_output)

        self._output_formatter.finalize()

        for cleanup_function in self._cleanup:
            cleanup_function(Measurement.station, namespace)

        self._sweep_object.set_namespace(None)

        return self

    def output(self, *args):
        return self._output_formatter.output(*args)


formatters = {
    "spyview": {
        "formatter_class": SpyviewFormatter,
        "args": [],
        "kwargs": dict()
    },
    "dict": {
        "formatter_class": DictFormatter,
        "args": [],
        "kwargs": dict(unit="replace", value="append", independent_parameter="replace")
    }
}


def set_default_formatter(cls="spyview"):
    Measurement.set_default_formatter(**formatters[cls])

set_default_formatter()
