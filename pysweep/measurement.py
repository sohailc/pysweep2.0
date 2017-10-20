from pysweep import Namespace
from pysweep.sweep_object import nested_sweep
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

    def __init__(self, setup, cleanup, sweep_objects, measures=None, output_formatter=None):

        self._setup = setup
        self._cleanup = cleanup

        self._sweep_object = nested_sweep(*sweep_objects) if isinstance(sweep_objects, list) else sweep_objects
        self._measures = measures or []
        self._output_formatter = output_formatter or Measurement.get_default_formatter()

        self.name = None

    def run(self, name):

        self.name = name
        namespace = Namespace()
        self._sweep_object.set_station(Measurement.station)
        self._sweep_object.set_namespace(namespace)

        for measure in self._measures:
            self._sweep_object.after_each(measure)

        self._setup(Measurement.station, namespace)
        for log_line in self._sweep_object:
            self._output_formatter.add(log_line)

        self._output_formatter.finalize()
        self._cleanup(Measurement.station, namespace)
        self._sweep_object.set_namespace(None)

        return self

    def output(self):
        return self._output_formatter.output()


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
