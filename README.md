# PySweep 2.0 interface and design decisions
## Introduction
PySweep is a framework intended to be used on top of qcodes [QCoDeS](https://github.com/QCoDeS/Qcodes) in order to define measurements flexibly. At the most general level, a measurement has dependent and independent variables with "setup" and "clean up" methods. For different values of the independent variables, the dependant variables will be measured. In our framework we will decouple the sweeping of the independent variables, from the measurement of the dependant variables. At the most general level, a measurement in our framework looks as follows: 

```python
from pysweep import Measurement, SpyViewExporter

Measurement.default_station = station
Measurement.default_exporter = SpyViewExporter

my_measurement = Measurement(
    [setup_function1, setup_function2, ...], 
    [cleanup_function1, cleanup_function2, ...], 
    [measurement_function1, measurement_function2, ...],
    [sweep_object1, sweep_object2, ...], 
)

my_measurement.run(name="some_descriptive_name", description="some succinct description")
```

Let's go through the arguments of the Measurement class one by one.

## Setting defaults

The measurement class has default class attributes which can be set before starting any measurements. Specifically:
1) default station: The QCoDeS station to be used in measurements
2) default exporter: The default export format to use. The API of the exporter shall be described in section TBD. In the first version of pysweep 2.0 we shall have at least the SpyView exporter which will enable users to export to an ascii file compatible with the [Spyview](http://nsweb.tn.tudelft.nl/~gsteele/spyview/) program 

## Measurement setup and cleanup 

A setup function brings the hardware in a state making it ready to perform a measurement. This could for example be instructing a lock-in amplifier to respond to triggers when these are send or putting an oscilloscope in the correct measurement ranges. A cleanup ensure that the instruments are left in well-defined settings after the measurement has concluded. 

The measurement class accepts a list of setup and clean up function. This enhances modularity as not all measurements will have the same hardware; If a measurement does not have an oscilloscope, there is no need to include a "setup_scope" function. 

These functions accept a two parameter as input, the first of type QCoDeS Station and the second shall be an instance of pysweep.NameSpace. The setup and cleanup functions return a dictionary with arbitary contents. We can for example log the start and end times of the measurement.  

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

One might wonder why these function class methods, as then the pythonic namespace "self" will be available. However, if the setup, cleanup and measurement functions would be class methods of a single instance then these methods will be coupled to each other. Let us suppose that we have two measurements, each with its own setup, measure and cleanup function: 

```
Measurement 1 = setup1, measure1, cleanup1 
Measurement 2 = setup2, measure2, cleanup2 
```
Now lets suppose that we want to define a third measurement which combines the two pervious onces: 
```
Measurement 3 = setup1, measure2, cleanup3 
```
There is no way to reuse code for the third measurement if the functions involved are class methods. Our design with namespaces allows us to mix and match setup, measure and cleanup functions to our hearts content.

## SweepObject

The measurement class accepts a list of sweep_object's as the thrid parameter, which shall be an instances of a SweepObject class. The basic signature of the SweepObject class is as follows: 

```python
from pysweep import SweepObject

SweepObject(qcodes_parameter, iterable)
```
The second argument of SweepObject may also be a list or generator (or any class which implements "\_\_next\_\_"). 

A list of multiple sweep objects will be interpreted as a nested sweep. In other words, 

```python
my_measurement = Measurement(
    [setup_function], 
    [cleanup_function], 
    [measurement_function],
    [sweep_object1, sweep_object2], 
)
```
is approximately the same as 
```python
setup_function()
for i in sweep_object1:
    for j in sweep_object2:
        measurement_function()
cleanup_function()
```
An equivalent way of writing this is 
```python
my_measurement = Measurement(
    [setup_function], 
    [cleanup_function], 
    pysweep.sweep_product(sweep_object1, sweep_object2),
    [sweep_object1, sweep_object2], 
)
```
A way to perform a co-sweep (where two parameters are being swept at the same time) is as follows: 
```python
my_measurement = Measurement(
    [setup_function], 
    [cleanup_function], 
    pysweep.sweep_zip(sweep_object1, sweep_object2),
    [sweep_object1, sweep_object2], 
)
```

### Performing actions before, during and after the sweep

It can be necessary to perform certain actions before, during or after a sweep. For instance, at each iteration in the sweep we might want to send a hardware trigger. Note that it is not always possible to solve this in the measurement functions. Consider for example the scenario where we want to perform some action at the start or end of a sweep; there is no way for a measurement function to know if we are starting or ending a sweep. 

To solve this we implement "before_each", "after_each", "before_index", "after_index" methods. 

For example:
```python
SweepObject(parameter, values).before_each(action)
```
is approximately the same as 
```python
for v in values:
    action()
    parameter.set(v)
```
While 
```python
SweepObject(parameter, values).after_each(action)
```
is approximately the same as 
```python
for v in values:
    parameter.set(v)
    action()
```
Before_index and after_index work as follows: 
```python
SweepObject(parameter, values).after_index(index, action)
```
is approximately the same as 
```python
for count, v in enumerate(values):
    parameter.set(v)
    if count == index:
        action()
```

In principle we can use negative indices as well and these will work the same as negative indices in lists and arrays. For example, after_index(-1, action) will perform an action after setting the last value. However, this only works if the "values" parameter has a defined length. Negative indices will raise a ValueError in the case that "values" does not have a "\_\_len\_\_" attribute, as is the case for generators. 

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
 "gate_voltage": {
     "unit": "v", 
     "value": 2.3
  }
}
```
and at the second iteration it returns: 
```python
{
 "gate_voltage": {
     "unit": "v", 
     "value": 4.5
 }
}
```
The internal dictionary will contain
```python
{
 "gate_voltage": {
     "unit": "v",
     "value": [2.3, 4.5]
 }
}
```

We see that we can define multiple measurement functions. The measurement class will combine the resulting dictionaries.  

### Measurment functions reading hardware buffered values

Let's consider a scenario where the sweep object is sending triggers to a measurement instrument and at each trigger this instrument stores the measured value in an internal buffer. For certain type of measurements this can dramatically increase the measurement speed (as is the case with for example the SR830 lockin amplifier). We read out the buffer when either the buffer is full or when the measurement is done. How do we program this will pysweep? 

The measurement function will be called at each iteration of the sweep object but unless the instrument buffer is full or we are at the end of a sweep we cannot return any measurement value. When we do read the buffer al the previously unread values will be returned at once. To accomodate this, the measurement functions will for example return at each iteration

```python
{
 "gate_voltage": {
     "unit": "v", 
     "value": "delayed_<serial number>"
 }
}
```
where serial number is a number generated by the python module [uuid](https://docs.python.org/2/library/uuid.html). When the buffered values become available these values are returned as follows: 

```python
{
 "gate_voltage": {
     "unit": "v", 
     "value": {
         "delayed_<serial number1>": 2.3, 
         "delayed_<serial number2>": 4.5,
         ....
     }
 }
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
  .at_end(force_buffer_read), 
 [measurement]
)

def send_trigger(station, namespace):
    station.instrument.trigger()
    namespace.count_triggers += 1

def force_buffer_read(station, namespace):
    namespace.force_buffer_read = True

def measurement(station, namespace):
    if not namespace.force_buffer_read and namespace.count_triggers < station.instrument.buffer_size:
        id = "delayed_{}".format(str(uuid.uuid1()))
        namespace.ids.append(id)
        
        return {
            "gate_voltage" {
                "unit": "v"
                "value": id
            }
        }
    else:
        data = station.instrument.read_buffer()
        d = {
            "gate_voltage": {
                "unit": "v", 
                "value": {k: v for k, v in zip(namespace.ids, data)}
            }
        }
        namespace.ids = []
        namespace.count_triggers = 0
```

### Measurements without sweeping parameters

Sometimes we do not sweep parameters in software and instead leave all sweeping in hardware. For this reason, the sweep_object parameter in the measurement class is an optional parameter. However, the Measurement class still needs to know what the dependent and independent parameters are in this case. In this case the measurement function will need to return both in the following format: 

```python
{
    "independent": {
        "gate1": {
            "unit": "v", 
            "value": [1, 2, 3, 4, 5, 1, 2, 3, ...]
        }
        "gate2": {
            "unit": "v" , 
            "value": [1, 1, 1, 1, 1, 2, 2, 2, ...]
        }
    }
    "dependent": {
        "source-drain": { 
            "unit": "A", 
            "value": [0.11, 0.10, 0.09, ...]
        }
    }
}
```

# API 

## pysweep module

The pysweep module shall have the following class and function definitions: 

* Measurement: class
    * Description: Responsible for measurements 

* SweepObject: class
    * Description: Responsible for setting the independent variables in a measurement
    
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
Measurement(setup, cleanup, sweep_object=None, measurements=[measurement1, measurement2, ...])
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
    * Description: This object is responsible for setting the independent variables during a measurement. If no parameters are swept during a measurement (e.g. all sweeping is done by hardware), this parameter can be None. For a complete description, see the API of this class described elsewhere in this document. 

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
    * Description: A sweep object is an iterable, which means we can loop over a sweep object. 
    * Returns: Dict, Everytime \_\_next\_\_ is called, the sweep object shall return a dictionary in which the keys represent the independent parameter names and the values the new values of these parameters. 

* at_start
    * Description: Give a function to be executed at the start of a sweep
    * Inputs: 
        * function, callable
        * args, list, optional, arguments to be given to the function
        * kwargs, dict, optional, keyword arguments to be given to the function
    * Returns: SweepObject

* at_each
    * Description: Give a function to be executed at each iteration of the sweep
    * Inputs: 
        * function, callable
        * args, list, optional, arguments to be given to the function
        * kwargs, dict, optional, keyword arguments to be given to the function
    * Returns: SweepObject
    
* at_end
    * Description: Give a function to be executed at the end of the sweep
    * Inputs: 
        * function, callable
        * args, list, optional, arguments to be given to the function
        * kwargs, dict, optional, keyword arguments to be given to the function
    * Returns: SweepObject

## BasePysweepExporter

TBD

## SpyViewExporter

TBD

