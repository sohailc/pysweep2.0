from pysweep import Namespace
from pysweep.sweep_object import sweep_product


class Measurement:
    station = None

    @classmethod
    def attach_station(cls, station):
        cls.station = station

    def __init__(self, setup, cleanup, measures, sweep_objects):

        self._setup = setup
        self._cleanup = cleanup
        self._measures = measures

        if hasattr(sweep_objects, "__len__"):
            self._sweep_object = sweep_product(sweep_objects)
        else:
            self._sweep_object = sweep_objects

        self.name = None

    def run(self, name, description=None):

        self.name = name
        namespace = Namespace()
        self._sweep_object.set_station(Measurement.station)
        self._sweep_object.set_namespace(namespace)

        self._setup(Measurement.station, namespace)
        for iteration in self._sweep_object:
            pass   # TODO: Left off here

        self._cleanup(Measurement.station, namespace)
        self._sweep_object.unset_namespace()