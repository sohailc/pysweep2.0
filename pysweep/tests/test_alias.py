import qcodes

from pysweep.utils import alias


class Powersource(qcodes.Instrument):
    def __init__(self, name):
        super().__init__(name)
        self._voltage = 0

        self.add_parameter(
            name="voltage",
            set_cmd=self._set_voltage,
            get_cmd=self._get_voltage,
            unit="mV"  # Stupid thing works in mV instead of Volt
        )

    def _set_voltage(self, value):
        self._voltage = value

    def _get_voltage(self):
        return self._voltage


def test():
    pwr = Powersource("pwr")

    gate = alias(pwr.voltage, new_label="gate voltage", new_name="gate", new_unit="V", conversion_factor=1E3)
    gate(3)  # Set at 3 V
    print(gate())
