from itertools import combinations

from qcodes import Parameter

prefix_table = {
    "nano": 1E-9,
    "micro": 1E-6,
    "milli": 1E-3,
    "unit": 1,
    "kilo": 1000,
    "mega": 1E6,
    "giga": 1E9
}


class BaseMapping:
    def __call__(self, value):
        raise NotImplementedError("Please subclass")

    def inverse(self, value):
        raise NotImplementedError("Please subclass")

    def __repr__(self):
        raise NotImplementedError("Please subclass")


class LinearMapping(BaseMapping):

    conversion_table = {
        "{} to {}".format(frm, to): prefix_table[frm] / prefix_table[to] for frm, to in combinations(prefix_table, 2)
    }

    conversion_table.update(
        {"{} to {}".format(to, frm): prefix_table[to] / prefix_table[frm] for frm, to in combinations(prefix_table, 2)}
    )

    def __init__(self, conversion_factor):

        if isinstance(conversion_factor, str):
            self.conversion_factor = LinearMapping.conversion_table[conversion_factor]
        else:
            self.conversion_factor = conversion_factor

    def __call__(self, value):
        return value / self.conversion_factor

    def inverse(self, value):
        return value * self.conversion_factor

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
        self._parameter(self._mapping(value))

    def get(self):
        value = self._mapping.inverse(self._parameter())
        self._save_val(value)
        return value
