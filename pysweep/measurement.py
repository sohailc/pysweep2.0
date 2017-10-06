from pysweep import Namespace
from pysweep.sweep_object import sweep_product
from pysweep.utils import DictMerge


class Measurement:
    station = None

    @classmethod
    def attach_station(cls, station):
        cls.station = station

    def __init__(self, setup, cleanup, measures, sweep_objects):

        self._setup = setup
        self._cleanup = cleanup
        self._measures = measures
        self._log_lines = []

        if isinstance(sweep_objects, list):
            self._sweep_object = sweep_product(*sweep_objects)
        else:
            self._sweep_object = sweep_objects

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
            self._log_lines.append(log_line)

        self._cleanup(Measurement.station, namespace)
        self._sweep_object.set_namespace(None)

        return self

    def get_output(self):
        return DictMerge(
            {"unit": "replace", "value": "append"}
        ).merge(self._log_lines)
