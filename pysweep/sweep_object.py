import qcodes


class BaseSweepObject:

    @classmethod
    def add_alias(cls, name, func):
        setattr(cls, name, lambda so, *args: func(so, *args))

    def __init__(self):

        self._point_generator = None
        self._station = None
        self._namespace = None

        self._measure_functions = {
            "after_each": [],
            "after_start": [],
            "after_end": []
        }

        for name in self._measure_functions.keys():
            setattr(self, name, self._add_measure_function(name))

    def _add_measure_function(self, name):
        def inner(func):
            self._measure_functions[name].append(func)
            return self

        return inner

    def _execute_measure_function(self, name):
        msg_all = dict()
        for func in self._measure_functions[name]:
            msg = func(self._station, self._namespace)
            msg_all.update(msg)

        return msg_all

    def _add_hooks(self, setter_iterable):
        def hooked():

            start = True
            for main_msg in setter_iterable:
                after_msg = self._execute_measure_function("after_each")
                main_msg.update(after_msg)

                if start:
                    self._execute_measure_function("after_start")
                    start = False

                yield main_msg

            self._execute_measure_function("after_end")

        return hooked()

    def _setter_factory(self):
        raise NotImplementedError("Please subclass BaseSweepObject")

    def __iter__(self):
        self._point_generator = self._add_hooks(self._setter_factory())
        return self

    def __next__(self):
        return next(self._point_generator)

    def set_station(self, station):
        self._station = station
        return self

    def set_namespace(self, namespace):
        self._namespace = namespace
        return self

# --------------Sweep Subclasses ----------------------------------------------------------------------------


class SweepGenerator(BaseSweepObject):
    def __init__(self, generator_function):
        self._generator_function = generator_function
        super().__init__()

    def _setter_factory(self):
        return self._generator_function()


class SweepParameter(BaseSweepObject):
    def __init__(self, parameter, point_function):
        self._parameter = parameter
        self._point_function = point_function
        super().__init__()

    def _setter_factory(self):
        for value in self._point_function(self._station, self._namespace):
            self._parameter.set(value)
            yield {self._parameter.label: {"unit": self._parameter.units, "value": value}}


class SweepFunction(BaseSweepObject):
    def __init__(self, set_function, point_function):
        self._set_function = set_function
        self._point_function = point_function
        super().__init__()

    def _setter_factory(self):
        for value in self._point_function(self._station, self._namespace):
            yield self._set_function(self._station, self._namespace, value)


class SweepProduct(BaseSweepObject):
    def __init__(self, sweep_objects):
        self._sweep_objects = sweep_objects
        super().__init__()

    @staticmethod
    def _two_product(sweep_object1, sweep_object2):
        def inner():
            for result2 in sweep_object2:
                for result1 in sweep_object1:
                    result1.update(result2)
                    yield result1

        return SweepGenerator(inner)

    def _setter_factory(self):
        prod = self._sweep_objects[0]
        for so in self._sweep_objects[1:]:
            prod = SweepProduct._two_product(prod, so)

        return prod

    def __iter__(self):
        namespace = self._namespace
        station = self._station
        for so in self._sweep_objects:
            if namespace is not None:
                so.set_namespace(namespace)
            if station is not None:
                so.set_station(station)
        return super().__iter__()


class SweepZip(BaseSweepObject):
    def __init__(self, sweep_objects):
        self._sweep_objects = sweep_objects
        super().__init__()

    @staticmethod
    def _combine_dictionaries(dictionaries):
        combined = {}
        for d in dictionaries:
            combined.update(d)
        return combined

    def _setter_factory(self):
        for results in zip(*self._sweep_objects):
            yield SweepZip._combine_dictionaries(results)

    def __iter__(self):
        namespace = self._namespace
        station = self._station
        for so in self._sweep_objects:
            if namespace is not None:
                so.set_namespace(namespace)
            if station is not None:
                so.set_station(station)
        return super().__iter__()

# --------------  Sweep Factories ----------------------------------------------------------------------------


def sweep_object(obj, sweep_points):

    if not callable(sweep_points):
        point_function = lambda station, namespace: sweep_points
    else:
        point_function = sweep_points

    if not isinstance(obj, qcodes.StandardParameter):
        if not callable(obj):
            raise ValueError("The object to sweep over needs to either be a QCoDeS parameter or a function")

        return SweepFunction(obj, point_function)
    else:
        return SweepParameter(obj, point_function)


def sweep_product(*sweep_objects):
    return SweepProduct(sweep_objects)


def sweep_zip(*sweep_objects):
    return SweepZip(sweep_objects)
