from typing import Union, Optional

from qcodes import Parameter, Instrument


class BaseMapping:
    """
    One-to-one mapper. A forward call will convert the new value from an old value while the inverse will do the
    opposite.
    """
    def __call__(self, value: float) ->float:
        # As a convenience, calling the mapper is the same as calling forward
        return self.forward(value)

    def forward(self, value: float) ->float:
        """
        Calculate new from old

        Args:
            value (float)

        Return:
            float
        """
        raise NotImplementedError("Please subclass")

    def inverse(self, value: float) ->float:
        """
        Calculate old from new

        Args:
            value (float)

        Return:
            float
        """
        raise NotImplementedError("Please subclass")

    def __repr__(self) -> str:
        """
        The string representation of the mapping. This is needed for correct logging in the meta data

        Returns:
            str
        """
        raise NotImplementedError("Please subclass")


class LinearMapping(BaseMapping):
    """
    Apply a linear mapping
    """

    def __init__(self, conversion_factor: float):
        """
        New = old * conversion_factor

        Args:
            conversion_factor (float)
        """
        self.conversion_factor = conversion_factor

    def forward(self, value: float) -> float:
        return value * self.conversion_factor

    def inverse(self, value: float) -> float:
        return value / self.conversion_factor

    def __repr__(self) -> str:
        return "Linear map: this = original * {}".format(self.conversion_factor)


class Alias(Parameter):
    """
    Alias a parameter. This is useful if the original instrument parameter is not descriptive of the the experiment
    we need to do.

    Args:
        parameter (qcodes.Parameter): The parameter to alias
        name (str): The name of the new parameter
        instrument (qcodes.Instrument): The instrument to which this new parameter will be attached. If None, then the
                                        parameter is attached to the instrument of the original parameter. If the
                                        original parameter is a free-floating parameter then the result will be likewise
        mapping (BaseMapping or float): Describes how the parameter value of the old parameter should be mapped to
                                         the new one. If this value is a floating point value, then new = old * mapping.
                                         If this value is None, then the value of the old and new parameters shall be
                                         the same.
        kwargs (dict): Kwargs to pass on to the parameter creation (e.g. the unit of the new parameter)
    """

    def __init__(
            self,
            parameter: Parameter,
            name: str,
            instrument: Optional[Instrument]=None,
            mapping: Optional[Union[float, int, BaseMapping]]=None,
            **kwargs: dict
    ):
        self._parameter = parameter
        self.name = name

        # Note, I think this is a sneaky way of accessing a private variable. We need to make a public interface
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

    def set(self, value: float) ->None:
        """
        Set the new parameter value
        """
        self._save_val(value)
        self._parameter(self._mapping.inverse(value))  # Set the old value from the new value -> inverse mapping

    def get(self) ->float:
        """
        Get the new parameter value
        """
        value = self._mapping(self._parameter())
        self._save_val(value)
        return value
