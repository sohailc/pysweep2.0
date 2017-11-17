from qcodes import Parameter


class BaseMapping:
    def __call__(self, value):
        raise NotImplementedError("Please subclass")

    def inverse(self, value):
        raise NotImplementedError("Please subclass")

    def __repr__(self):
        raise NotImplementedError("Please subclass")


class LinearMapping(BaseMapping):

    def __init__(self, conversion_factor):
        self.conversion_factor = conversion_factor

    def __call__(self, value):
        return value * self.conversion_factor

    def inverse(self, value):
        return value / self.conversion_factor

    def __repr__(self):
        return "Linear map: this = original * {}".format(self.conversion_factor)


class Alias(Parameter):
    def __init__(self, parameter, name, instrument=None, mapping=None, **kwargs):

        self._parameter = parameter
        self.name = name

        parameter_instrument = getattr(parameter, "_instrument", None)
        if not instrument:
            instrument = parameter_instrument

        if parameter_instrument is not None:
            parameter_instrument_name = parameter_instrument.name
        else:
            parameter_instrument_name = "None"

        if mapping is None:
            self._mapping = LinearMapping(1)

        elif isinstance(mapping, float) or isinstance(mapping, int):
            self._mapping = LinearMapping(mapping)
        else:
            self._mapping = mapping

        metadata = {
            "alias_of": ".".join([parameter_instrument_name, parameter.name]),
            "mapping": str(self._mapping)
        }

        if "unit" not in kwargs:
            kwargs["unit"] = parameter.unit

        super().__init__(
            name=self.name,
            instrument=instrument,
            metadata=metadata,
            **kwargs
        )

        if instrument is not None:
            instrument.parameters[name] = self

    def set(self, value):
        self._save_val(value)
        self._parameter(self._mapping.inverse(value))

    def get(self):
        value = self._mapping(self._parameter())
        self._save_val(value)
        return value
