from pysweep import Namespace
from pysweep.data_storage.json import JSONStorage
from pysweep.data_storage.spyview import SpyviewFormatter
from pysweep.sweep_object import ChainSweep


class Measurement:
    station = None

    @classmethod
    def attach_station(cls, station):
        cls.station = station

    @classmethod
    def set_default_storage_class(cls, storage_class, args, kwargs):
        cls.storage_class = storage_class
        cls.storage_args = args
        cls.storage_kwargs = kwargs

    @classmethod
    def get_default_formatter(cls):
        return cls.storage_class(*cls.storage_args, **cls.storage_kwargs)

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


storage_classes = {
    "spyview": {
        "storage_class": SpyviewFormatter,
        "args": [],
        "kwargs": dict()
    },
    "dict": {
        "storage_class": JSONStorage,
        "args": [],
        "kwargs": dict(unit="replace", value="append", independent_parameter="replace")
    }
}


def set_default_storage_class(cls="spyview"):
    Measurement.set_default_storage_class(**storage_classes[cls])

set_default_storage_class()
