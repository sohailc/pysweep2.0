
class BaseSetterObject:
    def __init__(self):

        self._measure_functions = {
            "before_each": [],
            "after_each": [],
            "after_start": [],
            "after_end": []
        }

        for name in self._measure_functions.keys():
            setattr(self, name, self._add_measure_function(name))
            setattr(self, "execute_{}".format(name), self._execute_measure_function(name))

    def _add_measure_function(self, name):
        def inner(func):
            self._measure_functions[name].append(func)
        return inner

    def _execute_measure_function(self, name):
        def inner(station, namespace):
            msg_all = dict()
            for func in self._measure_functions[name]:
                msg = func(station, namespace)
                msg_all.update(msg)

            return msg_all

        return inner

    def _add_hooks(self, setter_function):
        def hooked(station, namespace):

            start = True
            stop = False
            setter_generator = setter_function(station, namespace)

            while not stop:

                try:
                    before_msg = self.execute_before_each(station, namespace)
                    main_msg = next(setter_generator)
                    after_msg = self.execute_after_each(station, namespace)

                    main_msg.update(before_msg)
                    main_msg.update(after_msg)
                    yield main_msg

                except StopIteration:
                    stop = True
                    self.execute_after_end(station, namespace)
                    continue

                if start:
                    self.execute_after_start(station, namespace)
                    start = False

        return hooked


class SetterObject(BaseSetterObject):

    def __init__(self, parameter, point_function):
        self._parameter = parameter
        self._point_function = point_function
        super().__init__()

    def _unroll(self, station, namespace):
        for value in self._point_function(station, namespace):
            self._parameter.set(value)
            yield {self._parameter.name: {"units": self._parameter.units, "value": value}}

    def __call__(self, station, namespace):
        return self._add_hooks(self._unroll)(station, namespace)


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

        return self._add_hooks(setter_product)(station, namespace)


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
