class BaseSweepObject:
    def __init__(self):

        self._point_generator = None
        self._station = None
        self._namespace = None

        self._measure_functions = {
            "before_each": [],
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

    def _add_hooks(self, setter_function):
        def hooked():

            start = True
            stop = False
            setter_generator = setter_function()

            while not stop:

                try:
                    before_msg = self._execute_measure_function("before_each")
                    main_msg = next(setter_generator)
                    after_msg = self._execute_measure_function("after_each")

                    main_msg.update(before_msg)
                    main_msg.update(after_msg)
                    yield main_msg

                except StopIteration:
                    stop = True
                    self._execute_measure_function("after_end")
                    continue

                if start:
                    self._execute_measure_function("after_start")
                    start = False

        return hooked

    def _setter_function(self):
        raise NotImplementedError("Please subclass BaseSweepObject")

    def __iter__(self):
        self._point_generator = self._add_hooks(self._setter_function)()
        return self

    def __next__(self):
        return next(self._point_generator)


class SweepObject(BaseSweepObject):
    def __init__(self, parameter, point_function):
        self._parameter = parameter

        if not callable(point_function):
            _point_function = lambda station, namespace: iter(point_function)
        else:
            _point_function = point_function

        self._point_function = _point_function
        super().__init__()

    def _setter_function(self):
        for value in self._point_function(self._station, self._namespace):
            self._parameter.set(value)
            yield {self._parameter.label: {"unit": self._parameter.units, "value": value}}


class SweepProduct(BaseSweepObject):
    def __init__(self, sweep_objects):
        self._sweep_object = sweep_objects
        super().__init__()

    @staticmethod
    def _two_product(sweep_object1, sweep_object2):
        def inner():
            for result1 in sweep_object1:
                for result2 in sweep_object2:
                    result2.update(result1)
                    yield result2
        return inner()

    def _setter_function(self):
        prod = self._sweep_object[-1]
        for sweep_object in self._sweep_object[-2::-1]:
            prod = SweepProduct._two_product(prod, sweep_object)
        return prod

