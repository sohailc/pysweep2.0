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

my_measurement.run("some_descriptive_name", "some succinct description", export_as="gnu_plot")
```

Let's go through the arguments of the Measurement class one by one. 

## Measurement setup and cleanup 

The setup brings the hardware in a state making it ready to perform a measurement. This could for example be instructing a lock-in amplifier to respond to triggers when these are send or putting an oscilloscope in the correct measurement ranges. A cleanup ensure that the instruments are left in well-defined settings after the measurement has concluded. 

These functions accept a single parameter as input. This parameter shall be of the type QCoDeS Station. These functions do not return anything 

## SweepObject

The measurement class accepts a single "sweep object" as the thrid parameter, which shall be an instance of a SweepObject class. The basic signature of the SweepObject class is as follows: 

```python
from pysweep import SweepObject

SweepObject(qcodes_parameter, iterable)
```
The second argument of SweepObject may also be a generator (or any class which implements "__next__"). 

At first glance this design seems limited in the following senses: 
1) What if we want to sweep multiple parameters? 
2) What if we want to perform more actions at each sweep iteration then simply setting a parameter (e.g. sending a trigger)? 
3) How do we establish feedback between a measurement and the sweep object? 

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
 qcodes_parameter2.set(value2)
 for value2 in iterable2: 
  qcodes_parameter1.set(value1)
  ...  # some measuement
```

Note that the first argument of sweep product represents the inner most loop. The returning sweep_product is another instance of SweepObject which can be inserted into the Measurement class. 

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

Needless to say, we can arbitrarily combine SweepProduct and SweepZip to create complex sweeping schemes. 

### Performing actions before, during and after the sweep

It can be necessary to perform certain actions before, during or after a sweep. For instance, at each iteration in the sweep we might want to send a hardware trigger. Note that it is not always possible to solve this in the measurement functions. We might for instance send a hardware trigger in the measurement function, but suppose we want to perform some action at the start or end of a sweep; there is no way for a measurement function to know if we are starting or ending a sweep. 

Another solution we could propose to put some intelligence in the iterator (e.g. using a class instance which implements __next__) and while for complex cases this can indeed me necessary, for simple cases we will implement "at_start", "at_end" and "at_each" methods on the sweep object. For instance, consider the following code: 

```python
sweep_product = SweepProduct([
 SweepObject(qcodes_parameter1, iterable1).at_each(trigger_function),
 SweepObject(qcodes_parameter2, iterable2)
])
```
The complete signature of the at_start, at_end and at_each: "at_each(callable, args)" where args is an optional tuple. These functions return a SweepObject so that we can do "SweepObject().at_each().at_end()". 

### More complex sweeping operation with e.g. feedback

Consider an alternative solution to the "send a trigger at each iteration" problem: 

```python
class TriggerAtEach:
 def __init__(self, param_values):
  self._param_values = param_values
 def __next__():
  nxt = next(self._param_values)
  trigger_function()
  return nxt
```

And we use this as such

```python
sweep_product = SweepProduct([
 SweepObject(qcodes_parameter1, TriggerAtEach(iterable1)),
 SweepObject(qcodes_parameter2, iterable2)
])
```

This is obviously much less elegant and more complex. However, the basic idea will allow us to perform complex sweeps. Consider for example a situation where a measurement function sweeps a gate voltage and measures a source-drain current. There is an unknown gate voltage at which there is a maximum in the source drain current and we would like to sample more closely around this peak in gate-space. A measurement such as this might look as follows: 

```python

my_measurement = Measurement(
 setup_function, 
 cleanup_function, 
 SweepObject(station.keithley.channel[0], maximum_sampler), 
 [maximum_sampler.measure_source_drain]
)
```

We will not go into implementation details, but it is not hard to program "maximum_sampler" such that the "next" value it returns depends on the measured source drain current: the steps in the gate voltage is proportional to the derivative in the source drain current. 

## Measurement functions

Let's look at the basic signature of the measurement class again: 

```python
from pysweep import Measurement

my_measurement = Measurement(
 setup_function, 
 cleanup_function, 
 sweep_object, 
 [measurement_function1, measurement_function2, ...]
)
```

At each iteration of the sweep object each of the measurement functions will be called. Like the setup and cleanup functions, the measurement function accespts one argument: a QCoDeS Station. These functions return a dictionary, where the keys represent the name of the parameter being measured and value the measured value. The measurement class will aggregate the measured values in an internal dictionary under the same keys. For instance, if in the first iteration the measurement function returns: 

```python
{
 "gate_voltage [V]": 2.3
}
```
and at the second iteration it returns: 
```python
{
 "gate_voltage [V]": 4.5
}
```
The internal dictionary will contain
```python
{
 "gate_voltage [V]": [2.3, 4.5]
}
```

We see that we can define multiple measurement functions. The measurement class will combine the resulting dictionaries.  

### Measurment functions reading hardware buffered values

Let's consider a scenario where the sweep object is sending triggers to a measurement instrument and at each trigger this instrument stores the measured value in an internal buffer. For certain type of measurements this can dramatically increase the measurement speed (as is the case with for example the SR830 lockin amplifier). We read out the buffer when either the buffer is full or when the measurement is done. How do we program this will pysweep? 

The measurement function will be called at each iteration of the sweep object but unless the instrument buffer is full or we are at the end of a sweep we cannot return any measurement value. When we do read the buffer al the previously unread values will be returned at once. To accomodate this, the measurement functions will for instance return at each iteration

```python
{
 "gate_voltage [V]": "delayed_<serial number>"
}
```
where serial number is a number generated by the python module [uuid](https://docs.python.org/2/library/uuid.html). When the buffered values become available these values are returned as follows: 

```python
{
 "gate_voltage [V]": {"delayed_<serial number1>": 2.3, "delayed_<serial number2>": 4.5, ...}
}
```
The delayed values will be retroactively be inserted in the data set. A complete measurement may look something as follows: 

```python
from pysweep import Measurement

my_measurement = Measurement(
 setup_function, 
 cleanup_function, 
 SweepObject(powersource.channel[0], np.linspace(0, 1, 100)).at_each(send_trigger).at_end(instrument.force_buffer_read), 
 [instrument.read_buffer]
)
```
By calling the "force_buffer_read" method we are instructing the instrument to read the buffer even if it is not full. 

# Exporting measurements to files

By default, measurements are saved in the JSON format. However, we can specify another format with the "export_as" keyword argument. For instance, export_as="gnu_plot" will save in a format which is compatible with the [GNU plot](http://www.gnuplot.info/) utility. This is important for users using the [Spyview](http://nsweb.tn.tudelft.nl/~gsteele/spyview/) program. The files will be written concurrently with the measurements, ensuring that if a measurement encounters an exception, data will still be saved. However, values will only be saved to file once every delayed value is known as plotters like GNU plot and Spyview will not know how to interprete strings like "delayed_<number>".  

# TODO

make description optional

it should be able to determine if a measrement is running 

sweeps should be able to influence each other
