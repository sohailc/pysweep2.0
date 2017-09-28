from pysweep import Namespace
from pysweep.sweep_object import SweepObject


class Measurement:
    station = None
    namespace = None

    @classmethod
    def attach_station(cls, station):
        cls.station = station

    @classmethod
    def sweep_object(cls, parameter, point_function):

        if cls.namespace is None:
            cls.namespace = Namespace()

        return SweepObject(parameter, point_function, cls.station, cls.namespace)

    def __init__(self, swo):
        self._sweep_object = swo


sweep_object = Measurement.sweep_object
