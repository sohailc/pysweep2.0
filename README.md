# PySweep 2.0 interface and design decisions
## Introduction
PySweep is a framework intended to be used on top of qcodes [QCoDeS](https://github.com/QCoDeS/Qcodes) for defining measurements flexibly. At the most general level, a measurement has dependent and independant variables that we need to define. We need to specify: 
1) The values of the indepedent variables and how to address an instrument to set the specified values 
2) How to retrieve the dependent variables from instruments 
3) How to setup the instruments before the experiment 
4) How to clean up after the experiment 

For the first two points above, we propose to encode these in a dictionary structure as follows: 

```python 
 measurement_table = {
  "independent_variables": {
    "gate1": {
      "unit": "V",
      "set_function": some.instrument.set, 
      "values": iterable_values
     }
     "gate2": {
        "unit": "V",
        "set_function": other.instrument.set, 
        "values": generator_values
     }
  },
  "dependent_variables": {
    "source_drain": {
    "unit": "A", 
    "get_function": yet_another.instrument.get
    }
  }
}
```

In the above example we have defined two independent variables. Our measurement loop therefore will be a nested loop where the first independent variable will be located in the inner most loop and will be the one which is sweeping most frequently.  

The measurement table will also ensure the proper formatting of the resulting measurement file. We note that the "values" field of indepenent variables can be iterators or generators. This will allow us to introduce considerable flexibility. 

## Measurement setup and cleanup 

The measurement 
