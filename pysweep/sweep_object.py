from inspect import signature

from qcodes import StandardParameter


class SweepObject:
    def __init__(self, parameter, sweep_values):

        if not isinstance(parameter, StandardParameter):
            raise ValueError("The Parameter should be of type QCoDeS StandardParameter")

        self._parameter = parameter

        if not callable(sweep_values):
            self._create_sweep_values = lambda: sweep_values
        else:
            self._create_sweep_values = sweep_values

        self._sweep_values = None
        self._station = None
        self._namespace = None

    def __next__(self):
        value = next(self._sweep_values)
        self._parameter.set(value)

        label = self._parameter.label
        units = self._parameter.units
        return {
            label: {
                "units": units,
                "value": value
            }
        }

    def set_station(self, station):
        self._station = station

    def set_namespace(self, namespace):
        self._namespace = namespace

    def __iter__(self):

        sig = signature(self._create_sweep_values)
        if list(sig.parameters.keys()) == ["station", "namespace"]:

            if None in [self._station, self._namespace]:
                raise IndexError("Cannot iterate over sweep object unless a station and namespace have been given")

            self._sweep_values = iter(self._create_sweep_values(self._station, self._namespace))
        else:
            self._sweep_values = iter(self._create_sweep_values())

        return self

