from pysweep import Namespace
from pysweep.sweep_object import SweepObject, sweep_product


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
        self._namespace = None

    def run(self, name, description=None):

        self.name = name
        self._namespace = Namespace()

        self._setup(Measurement.station, self._namespace)
        for iteration in self._sweep_object:
            pass   # TODO: Left off here
