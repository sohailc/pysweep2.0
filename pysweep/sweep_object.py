
class BaseSetterObject:
    @staticmethod
    def dummy(station, namespace):
        pass

    def __init__(self):

        self._measure_functions = {
            "before_each": [BaseSetterObject.dummy],
            "after_each": [BaseSetterObject.dummy],
            "after_start": [BaseSetterObject.dummy],
            "after_end": [BaseSetterObject.dummy]
        }

        for name in self._measure_functions.keys():
            setattr(self, name, self._add_measure_function(name))
            setattr(self, "execute_{}".format(name), self._execute_measure_function(name))

    def _add_measure_function(self, name):
        def inner(func):
            if callable(func):
                self._measure_functions[name].append(func)
            else:
                self._measure_functions[name].extend(func)
        return inner

    def _execute_measure_function(self, name):
        def inner(station, namespace):
            for func in self._measure_functions[name]:
                func(station, namespace)
        return inner


class SetterObject(BaseSetterObject):

    def __init__(self, parameter, point_function):
        self._parameter = parameter
        self._point_function = point_function
        super().__init__()

    def unrole(self, station, namespace):
        for value in self._point_function(station, namespace):
            yield {self._parameter.name: {"units": self._parameter.units, "value": value}}

    def __call__(self, station, namespace):
        #setter_generator = (self._parameter.set(value) for value in  self._point_function(station, namespace))
        value_generator = self._point_function(station, namespace)

        start = True
        stop = False
        while not stop:

            try:
                value = next(value_generator)
            except StopIteration:
                stop = True
                self.execute_after_end(station, namespace)
                continue

            self.execute_before_each(station, namespace)
            self._parameter.set(value)
            self.execute_after_each(station, namespace)

            yield {self._parameter.name: {"units": self._parameter.units, "value": value}}

            if start:
                self.execute_after_start(station, namespace)
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
        setter_product = self._setters[-1]
        for setter in self._setters[-2::-1]:
            setter_product = SetterProduct._two_product(setter_product, setter)

        setter_product = self._add_hooks(setter_product)
        return setter_product(station, namespace)

    def _add_hooks(self, generator):

        def hooked_generator(station, namespace):
            self.execute_before_each(station, namespace)
            start = True
            for value in generator(station, namespace):

                if start:
                    self.execute_after_start(station, namespace)
                    start = False

                self.execute_after_each(station, namespace)
                yield value
                self.execute_before_each(station, namespace)

            self.execute_after_end(station, namespace)

        return hooked_generator


class SweepObject:
    def __init__(self, setter):
        self.setter = setter
        self._setter_generator = None
        self._station = None
        self._namespace = None

    def __next__(self):
        return next(self._setter_generator)

    def __iter__(self):
        self._setter_generator = self.setter(self._station, self._namespace)
        return self

    def before_each(self, before_each):
        self.setter.before_each(before_each)
        return self

    def after_each(self, after_each):
        self.setter.after_each(after_each)
        return self

    def after_start(self, after_start):
        self.setter.after_start(after_start)
        return self

    def after_end(self, after_end):
        self.setter.after_end(after_end)
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
