# PySweep 2.0 interface and design decisions
## Introduction
PySweep is a framework intended to be used on top of qcodes [QCoDeS](https://github.com/QCoDeS/Qcodes) in order to define measurements flexibly. At the most general level, a measurement has dependent and independant variables with "setup" and "clean up" methods. For different values of the independant variables, the dependant variables will be measured. In our framework we will decouple the sweeping of the independant variables, from the measurement of the dependant variables. At the most general level, a measurement in our framework looks as follows: 

```python
from pysweep import Measurement

my_measurement = Measurement(
 setup_function, 
 cleanup_function, 
 sweep_object, 
 [measurement_function1, measurement_function2, ...]
)

my_measurement.run("some descriptive_name", "some succinct description")
```

Let's go through the arguments of the Measurement class one by one. 

## Measurement setup and cleanup 

The setup brings the hardware in a state making it ready to perform a measurement. This could for example be instructing a lock-in amplifier to respond to triggers when these are send or putting an oscilloscope in the correct measurement ranges. A cleanup ensure that the instruments are left in defined setting after the measurement has concluded. 

These functions accept a single parameter as input. This parameter shall be of the type QCoDeS Station. 

## SweepObject

The measurement class accepts a single "sweep object" as the thrid parameter, which shall be an instance of a SweepObject class. The basic signature of the SweepObject class is as follows: 

```python
from pysweep import SweepObject

SweepObject(qcodes_parameter, iterable)
```
The second argument of SweepObject may also be a generator (or any class which implements "__next__"). 

At first glance this design seems limited in the following senses: 
1) What if we want to sweep multiple parameters? 
2) How do we establish feedback between a measurement and the sweep object? 

We will address these concerns below

### Multiple sweeping parameters

We shall apply a chaining construct to implement sweeping multiple parameters. For instance, the following code shall sweep two parameters in a nested loop: 

```python
from pysweep import SweepObject, SweepProduct

sweep_product = SweepProduct([
 SweepObject(qcodes_parameter1, iterable1),
 SweepObject(qcodes_parameter2, iterable2)
])
```

In pseudo-code, this does approximately: 

```python
for value1 in iterable1: 
 qcodes_parameter1.set(value1)
 for value2 in iterable2: 
  qcodes_parameter2.set(value2)
  ...  # some measuement
```

The returning sweep_product is another instance of SweepObject which can be inserted into the Measurement class. 

Another way to chain is to "co-sweep" two parameters: 

```python
from pysweep import SweepObject, SweepZip

sweep_product = SweepZip([
 SweepObject(qcodes_parameter1, iterable1),
 SweepObject(qcodes_parameter2, iterable2)
])
```

In pseudo-code, this does approximately: 

```python
for value1, value2 in zip(iterable1, iterable2): 
 qcodes_parameter1.set(value1)
 qcodes_parameter2.set(value2)
 ...  # some measuement
```

## Hardware Triggering

Consider a measurement where we sweep a gate voltage over consecutive values and at each voltage we send a trigger signal to a measurement device to measure a source drain current. The measurement device will use an internal buffer to store the measured value. We want to read out the internal buffer in one go when either we are at the end of our measurement, or when the buffer is full. We propose the following schema to define such a measurement: 

```python
class MyMeasurement(pysweep.BaseMeasurement):
    def setup(self):
        some.instrument.set(0)

    def measure(self, namespace):
        measurement_table = {
            "independent_variables": {
                "gate1": {
                    "unit": "V",
                    "set_function": some.instrument.set,
                    "values": iterable_values, 
                    "at_each": {
                        "function": measurement_instrument.trigger
                    }
                },
                "gate2": {
                    "unit": "V",
                    "set_function": other.instrument.set,
                    "values": generator_values, 
                    "at_end": {
                        "function": measurement_instrument.force_read
                        "args": (True,)
                    }
                }
            },
            "dependent_variables": {
                "source_drain": {
                    "unit": "A",
                    "get_function": measurement_instrument.read_buffer
                }
            }
        }

        return measurement_table

    def cleanup(self, namespace):
        some.instrument.set(0)
```
In the inner loop we send a trigger for each voltage we set on gate 1. We then want to aqcuire the dependent variables and call read buffer. This function should return the string "delayed_N" until either a "force_read" flag becomes true, or if the number of triggers recieved is equal to the buffer size. Here N is any positive integer. When a buffer is read out, the values returned will have the following format: 

```python
{
    "delayed_0": 2.3E-4,
    "delayed_1": 2.2E-4
    ...
}
```
The delayed values will retroactively be filled in 
