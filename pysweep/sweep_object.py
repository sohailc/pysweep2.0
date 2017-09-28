class SweepObject:
    def __init__(self, parameter, sweep_values):
        self._parameter = parameter
        self._sweep_values = sweep_values

    def __next__(self):
       pass

    def __iter__(self):
        return self

