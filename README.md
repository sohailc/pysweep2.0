# PySweep 2.0 interface and design decisions
## Introduction
PySweep is a framework intended to be used on top of qcodes [QCoDeS](https://github.com/QCoDeS/Qcodes) in order to define measurements flexibly. At the most general level, a measurement has dependent and independant variables with "setup" and "clean up" methods. For different values of the independant variables, the dependant variables will be measured. In our framework we will decouple the sweeping of the independant variables, from the measurement of the dependant variables. At the most general level, a measurement in our framework looks as follows: 

```python
from pysweep import Measurement, SpyViewExporter

Measurement.default_station = station
Measurement.default_exporter = SpyViewExporter

my_measurement = Measurement(
 setup_function, 
 cleanup_function, 
 sweep_object, 
 [measurement_function1, measurement_function2, ...]
)

my_measurement.run(name="some_descriptive_name", description="some succinct description")
```

Let's go through the arguments of the Measurement class one by one.

## Setting defaults

The measurement class has default class attributes which can be set before starting any measurements. Specifically:
1) default station: The QCoDeS station to be used in measurements
2) default exporter: The default export format to use. The API of the exporter shall be described in section TBD. In the first version of pysweep 2.0 we shall have at least the SpyView exporter which will enable users to export to an ascii file compatible with the [Spyview](http://nsweb.tn.tudelft.nl/~gsteele/spyview/) program 

## Measurement setup and cleanup 

The setup brings the hardware in a state making it ready to perform a measurement. This could for example be instructing a lock-in amplifier to respond to triggers when these are send or putting an oscilloscope in the correct measurement ranges. A cleanup ensure that the instruments are left in well-defined settings after the measurement has concluded. 

These functions accept a two parameter as input, the first of type QCoDeS Station and the second shall be an instance of pysweep.NameSpace. The setup and cleanup functions do not return anything. 

## pysweep.NameSpace

The pysweep namespace object is simply defined as 

```python
class NameSpace:
 pass
```
and at first glance seems rather useless. What we can do with the namespace is for example the following: 

```python
>>> namespace = pysweep.NameSpace
>>> namespace.a = 1
>>> namespace.f = lambda x: x**2
>>> print(namespace.a)
1
>>> print(namespace.f(4))
16
```

All setup, cleanup and measurement functions shall accept a namespace as second argument. This will allow communication between these function. 

### The motivation for using namespaces

One might wonder why we are using namespaces for communication between functions. Why not make these function class methods, as the pythonic namespace available will be "self"? However, if the setup, cleanup and measurement functions would be class methods of a single instance then these methods will be coupled to each other. Let us suppose that we have two measurements, each with its own setup, measure and cleanup function: 

```
Measurement 1 = setup1, measure1, cleanup1 
Measurement 2 = setup2, measure2, cleanup2 
```
Now lets suppose that we want to define a third measurement which combines the two pervious onces: 
```
Measurement 3 = setup1, measure2, cleanup3 
```
There is no way to reuse code for the third measurement if the functions involved are class methods. Our design with namespaces allows us to mix and match setup, measure and cleanup functions to our hearts content :-)

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

### More complex sweeping operation with e.g. with adaptive stepping

Consider for example a situation where a measurement function sweeps a gate voltage and measures a source-drain current. There is an unknown gate voltage at which there is a maximum in the source drain current and we would like to sample more closely around this peak in gate-space. A measurement such as this might look as follows: 

```python
my_measurement = Measurement(
 setup_function, 
 cleanup_function, 
 SweepObject(station.gate, gate_values), 
 [measure_source_drain]
)
```

If the second argument of the sweep object is not an iterable or a list, it is assumed that it is a callable with arguments "station", "namespace". In the above example we could define "gate_values" as follows.  

```python
def gate_values(station, namespace):
 start_value = 0.2  #[V]
 end_value = 0.8 #[V]
 current_value = start_value
 while current_value < end_value:
  yield current_value
  current_value += calculate_next(station)  # Use the station to calculate an updated value for the gate
  
def calculate_next(station):
 sd_current = station.source_drain()
 gate_voltage = station.gate()
 
 # Measure dV/dI
 di = 0.1
 station.source_drain(sd_current + di)
 dv = station.gate() - gate_voltage
 
 return 0.01 / (0.1 + abs(dv / di))   # We want the sampling rate to be higher for higher dV/dI. 
```

It is possible that two sweep object which are chained together with SweepProduct or SweepZip can communicate with each other via the namespace. 

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
 SweepObject(powersource.channel[0], np.linspace(0, 1, 100))\
  .at_each(send_trigger)\
  .at_end(instrument.force_buffer_read), 
 [instrument.read_buffer]
)
```
By calling the "force_buffer_read" method we are instructing the instrument to read the buffer even if it is not full. 

# API 

## pysweep module

The pysweep module shall have the following class and function definitions: 

* Measurement: class
    * Description: Responsible for measurements 

* SweepObject: class
    * Description: Responsible for setting the independant variables in a measurement
    
* BasePysweepExporter: class
    * Description: The base class of a exporter which writes an internal measurement dictionary to a file

* SpyViewExporter: class 
    * Description: Exports the internal measurement dictionary to a spyview file 
    
* NameSpace: class
    * Description: Useful for providing a local namesapce 

* SweepProduct: function
    * Description: Chain a list of sweep objects to create a nested loop of arbitrary depth
    * Inputs: list, SweepObject
    * Returns: SweepObject

* SweepZip: function
    * Description: Chain a list of sweep objects to create co-sweeping loops
    * Inputs: list, SweepObject
    * Returns: SweepObject

## Measurement

Signature: 
```
Measurement(setup, cleanup, sweep_object=None, [measurement1, measurement2, ...])
```

### Constructor arguments
* setup: Callable
    * Description: Callable to the station is a state ready for a measurement
    * inputs: 
        * station, qcodes.Station
        * namespace, pysweep.NameSpace
    * returns: None

* cleanup: Callable
    * Description: Callable to put the station in a well defined state after a measurement
    * inputs: 
        * station, qcodes.Station
        * namespace, pysweep.NameSpace
    * returns: None

* sweep_object: pysweep.SweepObject, optional
    * Description: This object is responsible for setting the independant variables during a measurement. If no parameters are swept during a measurement (e.g. all sweeping is done by hardware), this parameter can be None. For a complete description, see the API of this class described elsewhere in this document. 

* measurement_list: list, callable
    * Description: A list of callables 
    * inputs: 
        * station, qcodes.Station
        * namespace, pysweep.NameSpace
    * returns: dictionary

### Public methods
* run
    * Description: run the measurement
    * Inputs: 
        * name, string
        * description, string
    * Returns: None

### Public class attributes
* default_station, qcodes.Station
    * Description: The station instance to be used when creating a measurement instance

* default_exporter, PySweepExporter 
    * Description: The default exporter to be used. 

## SweepObject

Signature: 
```
SweepObject(qcodes_parameter, sweepvalues)
```
### Constructor arguments
* qcodes_parameter, qcodes.instrument.Parameter
    * Description: The parameter that needs to be swept. 

* sweepvalues, list or iterable or generator or callable
    * Description: The values which need to be set at each iteration of the measurement. If 'sweepvalues' is a callable this needs to accept two parameters: a qcodes.Station instance and a pysweep.NameSpace instance. 

### Methods
* \_\_next\_\_
    * Description: A sweep object is an iterable, which means we can loop over a sweep object. Everytime \_\_next\_\_ is called, the sweep object shall return a dictionary in the format {<independant_parameter_name_1>: <value>, <independant_parameter_name_2>: <value>, ...} 

