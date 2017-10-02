
class BaseSetterObject:
    @staticmethod
    def dummy(station, namespace):
        pass

    def __init__(self):
        self._before_each = BaseSetterObject.dummy
        self._after_each = BaseSetterObject.dummy
        self._after_start = BaseSetterObject.dummy
        self._after_end = BaseSetterObject.dummy

    def add_before_each(self, before_each):
        self._before_each = before_each

    def add_after_each(self, after_each):
        self._after_each = after_each

    def add_after_start(self, after_start):
        self._after_start = after_start

    def add_after_end(self, after_end):
        self._after_end = after_end


class SetterObject(BaseSetterObject):

    def __init__(self, parameter, point_function):
        self._parameter = parameter
        self._point_function = point_function
        super().__init__()

    def __call__(self, station, namespace):
        value_generator = self._point_function(station, namespace)

        start = True
        stop = False
        while not stop:

            try:
                value = next(value_generator)
            except StopIteration:
                stop = True
                self._after_end(station, namespace)
                continue

            self._before_each(station, namespace)
            self._parameter.set(value)
            self._after_each(station, namespace)

            yield {self._parameter.name: {"units": self._parameter.units, "value": value}}

            if start:
                self._after_start(station, namespace)
                start = False


class SetterProduct(BaseSetterObject):
    def __init__(self, setters):
        self._setters = setters
        super().__init__()

    @staticmethod
    def _two_product(setter_object1, setter_object2):
        def inner(station, namespace):
            for result1 in setter_object1(station, namespace):
                for result2 in setter_object2(station, namespace):
                    result2.update(result1)
                    yield result2

        return inner

    def __call__(self, station, namespace):
        self._setters[0].add_before_each(self._before_each)
        self._setters[0].add_after_each(self._after_each)
        self._setters[0].add_after_start(self._after_start)
        self._setters[-1].add_after_end(self._after_end)

        setter_product = self._setters[-1]
        for setter in self._setters[-2::-1]:
            setter_product = SetterProduct._two_product(setter_product, setter)

        return setter_product(station, namespace)


class SweepObject:
    def __init__(self, setter):
        self.setter = setter
        self._setter_generator = None
        self._station = None
        self._namespace = None

        self.add_before_each = self.setter.add_before_each
        self.add_after_each = self.setter.add_after_each
        self.add_after_start = self.setter.add_after_start
        self.add_after_end = self.setter.add_after_end

    def __next__(self):
        return next(self._setter_generator)

    def __iter__(self):
        self._setter_generator = self.setter(self._station, self._namespace)
        return self


def sweep_object(parameter, point_function):

    if not callable(point_function):
        _point_function = lambda station, namespace: iter(point_function)
    else:
        _point_function = point_function

    setter = SetterObject(parameter, _point_function)
    return SweepObject(setter)


def sweep_product(sweep_objects):
    setters = [s.setter for s in sweep_objects]
    return SweepObject(SetterProduct(setters))
