import numpy as np
import qcodes
from pysweep.sweep_object import sweep

from pysweep.measurement import Measurement
Measurement.use_storage("qcodes")

gate_voltages = 10 * [0]


class PowerSource(qcodes.Instrument):
    serial_number = 0

    def __init__(self, name):
        super().__init__(name)

        self.add_parameter(
            name="voltage",
            set_cmd=self._set_voltage,
            get_cmd=self._get_voltage,
            unit="V"
        )

        self._serial_numer = PowerSource.serial_number
        PowerSource.serial_number += 1
        self.connect_message()

    def _set_voltage(self, voltage):
        gate_voltages[self._serial_numer] = voltage

    def _get_voltage(self):
        return gate_voltages[self._serial_numer]

    def connect_message(self, idn_param='IDN', begin_time=None):
        con_msg = ('Connected to: power source {}'.format(PowerSource.serial_number))
        print(con_msg)
        return {}


class MultiMeter(qcodes.Instrument):
    def __init__(self, name):
        super().__init__(name)

        self.add_parameter(
            name="current",
            get_cmd=self._get_current,
            unit="A"
        )

        self.connect_message()

    def _get_current(self):
        v1 = gate_voltages[0]
        v2 = gate_voltages[1]
        r_sqr = v1 ** 2 + v2 ** 2
        return r_sqr

    def connect_message(self, idn_param='IDN', begin_time=None):
        con_msg = ('Connected to: multimeter'.format(PowerSource.serial_number))
        print(con_msg)
        return {}


def some_measurement_function(station, namespace):
    value = station.power_source1.voltage() + station.power_source3.voltage()
    return {"some_measurement": {"unit": "V", "value": value}}


def setup(station, namespace):
    global gate_voltages
    gate_voltages = 10 * [0]
    print("setting up")
    return {}


def cleanup(station, namespace):
    print("cleaning up")
    return {}


def main():
    power_source1 = PowerSource("power_source1")
    power_source2 = PowerSource("power_source2")
    power_source3 = PowerSource("power_source3")
    multi_meter = MultiMeter("multi_meter")

    station = qcodes.Station(power_source1, power_source2, power_source3, multi_meter)
    Measurement.station = station

    measurement = Measurement(
        setup,
        cleanup,
        sweep(power_source1.voltage, np.linspace(-1, 1, 100))(
            sweep(power_source2.voltage, np.linspace(-1, 1, 100))(
                station.multi_meter.current
            )
        )
    )

    data = measurement.run()

    o = data.output("power_source1_voltage")

if __name__ == "__main__":
    main()