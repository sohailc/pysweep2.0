from pysweep import Namespace
from pysweep.sweep_object import nested_sweep
from pysweep.output_formatter import DictFormatter


class Measurement:
    station = None

    @classmethod
    def attach_station(cls, station):
        cls.station = station

    @classmethod
    def get_default_formatter(cls):
        return DictFormatter({"unit": "replace", "value": "append"})

    def __init__(self, setup, cleanup, sweep_objects, measures=None, output_formatter=None):

        self._setup = setup
        self._cleanup = cleanup

        self._sweep_object = nested_sweep(*sweep_objects) if isinstance(sweep_objects, list) else sweep_objects
        self._measures = [] if measures is None else measures
        self._output_formatter = Measurement.get_default_formatter() if output_formatter is None else output_formatter

        self.name = None

    def run(self, name, description=None):

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
